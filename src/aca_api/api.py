"""FastAPI backend for ACA Premium Tax Credit calculations.

This module provides a REST API endpoint for calculating how ACA policy
changes affect household premium tax credits across income levels.
"""

import asyncio
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor

import anthropic
import numpy as np
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from policyengine_us import Simulation

# Thread pool for parallel simulations
simulation_executor = ThreadPoolExecutor(max_workers=3)

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import (
    create_enhanced_ptc_reform,
    create_700fpl_reform,
)

# Cache for calculation results - stores up to 1000 results for 24 hours
calculation_cache = TTLCache(maxsize=1000, ttl=86400)

# Cache for AI explanations - stores up to 500 results for 7 days
explanation_cache = TTLCache(maxsize=500, ttl=604800)

from .models import (
    CalculateRequest,
    CalculateResponse,
    ExplainRequest,
    ExplainResponse,
    ScrollySection,
)

app = FastAPI(
    title="ACA Premium Tax Credit Calculator API",
    description="Calculate how ACA policy changes affect household health insurance costs",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def convert_to_native(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return [convert_to_native(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native(item) for item in obj]
    return obj


def get_cache_key(data: CalculateRequest) -> str:
    """Generate a cache key from request parameters."""
    key_data = {
        "age_head": data.age_head,
        "age_spouse": data.age_spouse,
        "dependent_ages": tuple(data.dependent_ages) if data.dependent_ages else (),
        "state": data.state,
        "county": data.county,
        "zip_code": data.zip_code,
        "show_ira": data.show_ira,
        "show_700fpl": data.show_700fpl,
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


@app.post("/api/calculate", response_model=CalculateResponse)
async def calculate_ptc(data: CalculateRequest):
    """Calculate premium tax credits across income range.

    Returns arrays of PTC values under baseline, IRA extension, and 700% FPL
    scenarios for the specified household.
    """
    # Check cache first
    cache_key = get_cache_key(data)
    if cache_key in calculation_cache:
        return calculation_cache[cache_key]

    try:
        # Build household situation with income axis
        situation = build_household_situation(
            age_head=data.age_head,
            age_spouse=data.age_spouse,
            dependent_ages=list(data.dependent_ages),
            state=data.state,
            county=data.county,
            zip_code=data.zip_code,
            year=2026,
            with_axes=True,
        )

        # Run baseline simulation
        sim_baseline = Simulation(situation=situation)
        income = sim_baseline.calculate(
            "employment_income", map_to="household", period=2026
        )
        ptc_baseline = sim_baseline.calculate(
            "aca_ptc", map_to="household", period=2026
        )
        medicaid = sim_baseline.calculate(
            "medicaid", map_to="household", period=2026
        )
        chip = sim_baseline.calculate(
            "chip", map_to="household", period=2026
        )
        slcsp_array = sim_baseline.calculate(
            "slcsp", map_to="household", period=2026
        )
        fpl_array = sim_baseline.calculate("tax_unit_fpg", period=2026)

        # Get scalar values
        slcsp = float(np.max(slcsp_array))
        fpl = float(fpl_array[len(fpl_array) // 2])

        # Run reform simulations in parallel
        def run_ira_simulation():
            if not data.show_ira:
                return np.zeros_like(ptc_baseline)
            reform_ira = create_enhanced_ptc_reform()
            sim_ira = Simulation(situation=situation, reform=reform_ira)
            return sim_ira.calculate("aca_ptc", map_to="household", period=2026)

        def run_700fpl_simulation():
            if not data.show_700fpl:
                return np.zeros_like(ptc_baseline)
            reform_700fpl = create_700fpl_reform()
            if not reform_700fpl:
                return np.zeros_like(ptc_baseline)
            sim_700fpl = Simulation(situation=situation, reform=reform_700fpl)
            return sim_700fpl.calculate("aca_ptc", map_to="household", period=2026)

        # Submit both simulations to run in parallel
        ira_future = simulation_executor.submit(run_ira_simulation)
        fpl700_future = simulation_executor.submit(run_700fpl_simulation)

        # Wait for both to complete
        ptc_ira = ira_future.result()
        ptc_700fpl = fpl700_future.result()

        response = CalculateResponse(
            income=convert_to_native(income),
            ptc_baseline=convert_to_native(ptc_baseline),
            ptc_ira=convert_to_native(ptc_ira),
            ptc_700fpl=convert_to_native(ptc_700fpl),
            fpl=fpl,
            slcsp=slcsp,
            medicaid=convert_to_native(medicaid),
            chip=convert_to_native(chip),
        )

        # Cache the result
        calculation_cache[cache_key] = response
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {e}")


@app.post("/api/calculate-stream")
async def calculate_ptc_stream(data: CalculateRequest):
    """Calculate premium tax credits with streaming progress updates.

    Returns Server-Sent Events with progress updates as each simulation completes.
    """
    # Check cache first - if cached, return immediately
    cache_key = get_cache_key(data)
    if cache_key in calculation_cache:
        async def cached_response():
            yield f"data: {json.dumps({'step': 'cached', 'progress': 100, 'message': 'Using cached results'})}\n\n"
            result = calculation_cache[cache_key]
            yield f"data: {json.dumps({'step': 'complete', 'result': result.model_dump()})}\n\n"
        return StreamingResponse(cached_response(), media_type="text/event-stream")

    async def generate():
        try:
            # Step 1: Build household situation
            yield f"data: {json.dumps({'step': 'setup', 'progress': 10, 'message': 'Setting up household...'})}\n\n"
            await asyncio.sleep(0)  # Allow event to be sent

            situation = build_household_situation(
                age_head=data.age_head,
                age_spouse=data.age_spouse,
                dependent_ages=list(data.dependent_ages),
                state=data.state,
                county=data.county,
                zip_code=data.zip_code,
                year=2026,
                with_axes=True,
            )

            # Step 2: Run baseline simulation
            yield f"data: {json.dumps({'step': 'baseline', 'progress': 25, 'message': 'Calculating baseline (2026)...'})}\n\n"
            await asyncio.sleep(0)

            sim_baseline = Simulation(situation=situation)
            income = sim_baseline.calculate(
                "employment_income", map_to="household", period=2026
            )
            ptc_baseline = sim_baseline.calculate(
                "aca_ptc", map_to="household", period=2026
            )
            medicaid = sim_baseline.calculate(
                "medicaid", map_to="household", period=2026
            )
            chip = sim_baseline.calculate(
                "chip", map_to="household", period=2026
            )
            slcsp_array = sim_baseline.calculate(
                "slcsp", map_to="household", period=2026
            )
            fpl_array = sim_baseline.calculate("tax_unit_fpg", period=2026)

            slcsp = float(np.max(slcsp_array))
            fpl = float(fpl_array[len(fpl_array) // 2])

            # Step 3: Run reform simulations in parallel
            yield f"data: {json.dumps({'step': 'reforms', 'progress': 50, 'message': 'Calculating policy reforms...'})}\n\n"
            await asyncio.sleep(0)

            def run_ira_simulation():
                if not data.show_ira:
                    return np.zeros_like(ptc_baseline)
                reform_ira = create_enhanced_ptc_reform()
                sim_ira = Simulation(situation=situation, reform=reform_ira)
                return sim_ira.calculate("aca_ptc", map_to="household", period=2026)

            def run_700fpl_simulation():
                if not data.show_700fpl:
                    return np.zeros_like(ptc_baseline)
                reform_700fpl = create_700fpl_reform()
                if not reform_700fpl:
                    return np.zeros_like(ptc_baseline)
                sim_700fpl = Simulation(situation=situation, reform=reform_700fpl)
                return sim_700fpl.calculate("aca_ptc", map_to="household", period=2026)

            # Run both reform simulations in parallel
            loop = asyncio.get_event_loop()
            ira_future = loop.run_in_executor(simulation_executor, run_ira_simulation)
            fpl700_future = loop.run_in_executor(simulation_executor, run_700fpl_simulation)

            ptc_ira, ptc_700fpl = await asyncio.gather(ira_future, fpl700_future)

            # Step 4: Complete
            yield f"data: {json.dumps({'step': 'finalizing', 'progress': 90, 'message': 'Finalizing results...'})}\n\n"
            await asyncio.sleep(0)

            response = CalculateResponse(
                income=convert_to_native(income),
                ptc_baseline=convert_to_native(ptc_baseline),
                ptc_ira=convert_to_native(ptc_ira),
                ptc_700fpl=convert_to_native(ptc_700fpl),
                fpl=fpl,
                slcsp=slcsp,
                medicaid=convert_to_native(medicaid),
                chip=convert_to_native(chip),
            )

            # Cache the result
            calculation_cache[cache_key] = response

            yield f"data: {json.dumps({'step': 'complete', 'progress': 100, 'result': response.model_dump()})}\n\n"

        except ValueError as e:
            yield f"data: {json.dumps({'step': 'error', 'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'error': f'Calculation error: {e}'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# State names for narrative
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def build_explain_prompt(data: ExplainRequest) -> str:
    """Build the prompt for Claude to generate scrolly sections."""

    # Build household description
    household_parts = []
    household_parts.append(f"a {data.age_head}-year-old")
    if data.age_spouse:
        household_parts.append(f"and their {data.age_spouse}-year-old spouse")
    if data.dependent_ages:
        if len(data.dependent_ages) == 1:
            household_parts.append(f"with a {data.dependent_ages[0]}-year-old child")
        else:
            ages_str = ", ".join(str(a) for a in data.dependent_ages[:-1])
            ages_str += f" and {data.dependent_ages[-1]}"
            household_parts.append(f"with children ages {ages_str}")

    household_desc = " ".join(household_parts)
    state_name = STATE_NAMES.get(data.state, data.state)
    location = f"{data.county}, {state_name}"

    # Household size
    household_size = 1 + (1 if data.age_spouse else 0) + len(data.dependent_ages)
    has_children = len(data.dependent_ages) > 0

    # Calculate dollar thresholds from percentages
    medicaid_adult_income = data.fpl * data.medicaid_adult_threshold_pct / 100
    medicaid_child_income = data.fpl * data.medicaid_child_threshold_pct / 100
    chip_income = data.fpl * data.chip_threshold_pct / 100 if data.chip_threshold_pct > 0 else 0

    # Determine section 3 based on whether household has children
    if has_children:
        section3_id = "chip"
        section3_chart = "chip_focus"
        section3_instruction = f"Explain CHIP coverage for children up to {data.chip_threshold_pct}% FPL (${chip_income:,.0f})."
    else:
        section3_id = "cliff"
        section3_chart = "cliff_focus"
        section3_instruction = f"Explain the 400% FPL cliff at ${data.fpl_400_income:,.0f} where baseline subsidies end. Above this income, there are no premium tax credits under current law."

    # Medicaid details
    medicaid_children_note = f" Children qualify up to {data.medicaid_child_threshold_pct}% FPL." if has_children else ""
    expansion_note = "This is a non-expansion state." if not data.is_expansion_state else "This is an expansion state."
    chip_line = f"- CHIP for children: {data.chip_threshold_pct}% FPL (${chip_income:,.0f})" if has_children and data.chip_threshold_pct > 0 else ""

    prompt = f"""You are creating a factual, neutral scrollytelling narrative explaining ACA premium tax credits for a specific household.

IMPORTANT GUIDELINES:
- Be strictly factual and neutral. Do NOT express opinions about whether policies are good, bad, beneficial, or harmful.
- Do NOT use value-laden words like "unfortunately", "thankfully", "crucial", "vital", "struggle", etc.
- Simply describe what the policies are and how they affect this household's numbers.
- Use exact dollar amounts and percentages provided - do not round or approximate.
{"- CRITICAL: This household has NO children. Do NOT mention CHIP at all." if not has_children else ""}

HOUSEHOLD DETAILS:
- Description: {household_desc}
- Location: {location}
- Household size: {household_size}
- Has children: {"Yes" if has_children else "NO - DO NOT MENTION CHIP"}

PROGRAM ELIGIBILITY THRESHOLDS FOR {state_name.upper()}:
- Medicaid for adults: {data.medicaid_adult_threshold_pct}% FPL (${medicaid_adult_income:,.0f} for this household)
{chip_line}
- Medicaid expansion state: {"Yes" if data.is_expansion_state else "No"}

KEY FINANCIAL DATA:
- Federal Poverty Level (FPL) for this household: ${data.fpl:,.0f}
- 400% FPL (baseline subsidy cliff): ${data.fpl_400_income:,.0f}
- 700% FPL (proposed cliff under 700% FPL bill): ${data.fpl_700_income:,.0f}
- Annual benchmark plan (SLCSP): ${data.slcsp:,.0f} (${data.slcsp/12:,.0f}/month)

AT SAMPLE INCOME OF ${data.sample_income:,.0f} ({data.sample_income/data.fpl*100:.0f}% FPL):
- Baseline PTC (2026 if IRA expires): ${data.ptc_baseline_at_sample:,.0f}/year (${data.ptc_baseline_at_sample/12:,.0f}/month)
- IRA Extension PTC: ${data.ptc_ira_at_sample:,.0f}/year (${data.ptc_ira_at_sample/12:,.0f}/month)
- 700% FPL Bill PTC: ${data.ptc_700fpl_at_sample:,.0f}/year (${data.ptc_700fpl_at_sample/12:,.0f}/month)

Generate exactly 5 scrollytelling sections in JSON format. Each section should have:
- id: unique identifier
- title: descriptive section title (5-10 words)
- content: 2-3 short paragraphs using **bold** for key numbers. Use exact values provided above.
- chartState: MUST be one of these exact strings: "all_programs", "medicaid_focus", "chip_focus", "cliff_focus", "ira_impact", "both_reforms"

REQUIRED SECTIONS (use these EXACT chartState values - do not change them):
1. id: "intro", chartState: "all_programs" - Introduce this household and their location. State the SLCSP cost.

2. id: "medicaid", chartState: "medicaid_focus" - Explain Medicaid eligibility in {state_name}. Adults qualify up to {data.medicaid_adult_threshold_pct}% FPL (${medicaid_adult_income:,.0f}).{medicaid_children_note} {expansion_note}

3. id: "{section3_id}", chartState: "{section3_chart}" - {section3_instruction}

4. id: "ira_impact", chartState: "ira_impact" - Describe the IRA extension. At ${data.sample_income:,.0f} income, IRA provides ${data.ptc_ira_at_sample:,.0f}/year vs baseline ${data.ptc_baseline_at_sample:,.0f}/year.

5. id: "comparison", chartState: "both_reforms" - Compare baseline, IRA extension, and 700% FPL bill. Use the exact numbers provided.

Return ONLY valid JSON:
{{
  "sections": [
    {{"id": "intro", "title": "...", "content": "...", "chartState": "all_programs"}},
    {{"id": "medicaid", "title": "...", "content": "...", "chartState": "medicaid_focus"}},
    {{"id": "{section3_id}", "title": "...", "content": "...", "chartState": "{section3_chart}"}},
    {{"id": "ira_impact", "title": "...", "content": "...", "chartState": "ira_impact"}},
    {{"id": "comparison", "title": "...", "content": "...", "chartState": "both_reforms"}}
  ],
  "household_description": "{household_desc} in {location}"
}}"""

    return prompt


def get_explain_cache_key(data: ExplainRequest) -> str:
    """Generate a cache key from explain request parameters."""
    key_data = {
        "age_head": data.age_head,
        "age_spouse": data.age_spouse,
        "dependent_ages": tuple(data.dependent_ages) if data.dependent_ages else (),
        "state": data.state,
        "county": data.county,
        "is_expansion_state": data.is_expansion_state,
        "fpl": round(data.fpl, 0),
        "slcsp": round(data.slcsp, 0),
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


@app.post("/api/explain", response_model=ExplainResponse)
async def explain_with_ai(data: ExplainRequest):
    """Generate AI-powered scrollytelling narrative for a household."""

    # Check cache first
    cache_key = get_explain_cache_key(data)
    if cache_key in explanation_cache:
        return explanation_cache[cache_key]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured"
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = build_explain_prompt(data)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the response
        response_text = message.content[0].text

        # Extract JSON from response (handle potential markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())

        sections = [
            ScrollySection(**section)
            for section in result["sections"]
        ]

        response = ExplainResponse(
            sections=sections,
            household_description=result["household_description"]
        )

        # Cache the result
        explanation_cache[cache_key] = response
        return response

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse AI response: {e}"
        )
    except anthropic.APIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Anthropic API error: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating explanation: {e}"
        )


def main():
    """Run the FastAPI server with uvicorn."""
    import uvicorn

    port = int(os.environ.get("PORT", 5001))
    print(f"Starting ACA Calculator API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
