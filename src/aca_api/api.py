"""FastAPI backend for ACA Premium Tax Credit calculations.

This module provides a REST API endpoint for calculating how ACA policy
changes affect household premium tax credits across income levels.
"""

import json
import os

import anthropic
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import (
    create_enhanced_ptc_reform,
    create_700fpl_reform,
)

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


@app.post("/api/calculate", response_model=CalculateResponse)
async def calculate_ptc(data: CalculateRequest):
    """Calculate premium tax credits across income range.

    Returns arrays of PTC values under baseline, IRA extension, and 700% FPL
    scenarios for the specified household.
    """
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

        # Run IRA extension simulation
        ptc_ira = np.zeros_like(ptc_baseline)
        if data.show_ira:
            reform_ira = create_enhanced_ptc_reform()
            sim_ira = Simulation(situation=situation, reform=reform_ira)
            ptc_ira = sim_ira.calculate(
                "aca_ptc", map_to="household", period=2026
            )

        # Run 700% FPL simulation
        ptc_700fpl = np.zeros_like(ptc_baseline)
        if data.show_700fpl:
            reform_700fpl = create_700fpl_reform()
            if reform_700fpl:
                sim_700fpl = Simulation(situation=situation, reform=reform_700fpl)
                ptc_700fpl = sim_700fpl.calculate(
                    "aca_ptc", map_to="household", period=2026
                )

        return CalculateResponse(
            income=convert_to_native(income),
            ptc_baseline=convert_to_native(ptc_baseline),
            ptc_ira=convert_to_native(ptc_ira),
            ptc_700fpl=convert_to_native(ptc_700fpl),
            fpl=fpl,
            slcsp=slcsp,
            medicaid=convert_to_native(medicaid),
            chip=convert_to_native(chip),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {e}")


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

    prompt = f"""You are creating a personalized scrollytelling narrative explaining ACA premium tax credits for a specific household.

HOUSEHOLD DETAILS:
- Description: {household_desc}
- Location: {location}
- Household size: {household_size}
- Medicaid expansion state: {"Yes" if data.is_expansion_state else "No"}
- Has children: {"Yes" if has_children else "No"}

KEY FINANCIAL DATA:
- Federal Poverty Level (FPL) for this household: ${data.fpl:,.0f}
- 400% FPL (baseline cliff): ${data.fpl_400_income:,.0f}
- 700% FPL (proposed cliff): ${data.fpl_700_income:,.0f}
- Annual benchmark plan (SLCSP): ${data.slcsp:,.0f} (${data.slcsp/12:,.0f}/month)

AT SAMPLE INCOME OF ${data.sample_income:,.0f}:
- Baseline PTC (2026 if IRA expires): ${data.ptc_baseline_at_sample:,.0f}/year
- IRA Extension PTC: ${data.ptc_ira_at_sample:,.0f}/year
- 700% FPL Bill PTC: ${data.ptc_700fpl_at_sample:,.0f}/year

Generate exactly 5 scrollytelling sections in JSON format. Each section should have:
- id: unique identifier (e.g., "intro", "medicaid", "cliff", "ira_impact", "comparison")
- title: engaging section title (5-10 words)
- content: 2-3 paragraphs of markdown text using **bold** for emphasis. Be specific with dollar amounts and percentages. Make it personal to this household.
- chartState: one of "all_programs", "medicaid_focus", "chip_focus", "cliff_focus", "ira_impact", "both_reforms"

SECTION REQUIREMENTS:
1. **Introduction** (chartState: "all_programs"): Introduce this specific household and their location. Mention the SLCSP cost and what programs might help them.

2. **Medicaid** (chartState: "medicaid_focus"): Explain Medicaid {"availability since " + state_name + " expanded Medicaid" if data.is_expansion_state else "limitations since " + state_name + " has NOT expanded Medicaid"}. {"Mention the coverage gap if applicable." if not data.is_expansion_state else ""}

3. {"**CHIP Coverage** (chartState: 'chip_focus'): Explain how CHIP helps cover the children in this household." if has_children else "**The 400% FPL Cliff** (chartState: 'cliff_focus'): Explain what happens at $" + f"{data.fpl_400_income:,.0f}" + " when baseline subsidies end."}

4. **IRA Extension Impact** (chartState: "ira_impact"): Explain the blue shaded area showing additional subsidies. Use specific dollar amounts from the sample income data. Calculate monthly savings.

5. **Policy Comparison** (chartState: "both_reforms"): Compare all three scenarios. Mention specific income thresholds and what each policy means for this household.

Return ONLY valid JSON in this exact format:
{{
  "sections": [
    {{"id": "...", "title": "...", "content": "...", "chartState": "..."}},
    ...
  ],
  "household_description": "Short 10-word description like 'Single 35-year-old in Harris County, Texas'"
}}"""

    return prompt


@app.post("/api/explain", response_model=ExplainResponse)
async def explain_with_ai(data: ExplainRequest):
    """Generate AI-powered scrollytelling narrative for a household."""

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

        return ExplainResponse(
            sections=sections,
            household_description=result["household_description"]
        )

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
