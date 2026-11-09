"""FastAPI backend for ACA Premium Tax Credit calculations.

This module provides a REST API endpoint for calculating how ACA policy
changes affect household premium tax credits across income levels.
"""

import asyncio
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version

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
    create_additional_bracket_reform,
    create_simplified_bracket_reform,
)

# The model version is part of every cache key, so a new pin never serves
# answers the previous version computed.
MODEL_VERSION = version("policyengine-us")

# Each scenario: the request flag that turns it on, the response field for its
# credits, and the reform that models it.
SCENARIOS = [
    ("show_ira", "ptc_ira", create_enhanced_ptc_reform),
    ("show_700fpl", "ptc_700fpl", create_700fpl_reform),
    ("show_additional_bracket", "ptc_additional_bracket", create_additional_bracket_reform),
    ("show_simplified_bracket", "ptc_simplified_bracket", create_simplified_bracket_reform),
]

# Local cache fallback for development (in-memory, lost on restart)
_local_calculation_cache = TTLCache(maxsize=1000, ttl=86400)
_local_explanation_cache = TTLCache(maxsize=500, ttl=604800)

# Persistent cache (injected by Modal at runtime)
_persistent_calc_cache = None
_persistent_explain_cache = None

# Cache TTLs in seconds
CALC_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days for calculations
EXPLAIN_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days for AI explanations


def set_persistent_cache(calc_cache, explain_cache):
    """Inject persistent Modal Dict caches at runtime."""
    global _persistent_calc_cache, _persistent_explain_cache
    _persistent_calc_cache = calc_cache
    _persistent_explain_cache = explain_cache


def get_from_cache(key: str, cache_type: str = "calc"):
    """Get value from cache, checking TTL. Returns None if not found or expired."""
    # Import models lazily to avoid circular imports
    from .models import CalculateResponse, ExplainResponse

    # Try persistent cache first (Modal Dict)
    persistent_cache = _persistent_calc_cache if cache_type == "calc" else _persistent_explain_cache
    ttl = CALC_CACHE_TTL if cache_type == "calc" else EXPLAIN_CACHE_TTL

    if persistent_cache is not None:
        try:
            entry = persistent_cache.get(key)
            if entry is not None:
                # Check TTL
                if time.time() - entry.get("timestamp", 0) < ttl:
                    data = entry.get("data")
                    # Reconstruct Pydantic model from dict
                    if isinstance(data, dict):
                        if cache_type == "calc":
                            return CalculateResponse(**data)
                        else:
                            return ExplainResponse(**data)
                    return data
                # Expired - remove it
                try:
                    del persistent_cache[key]
                except Exception:
                    pass
        except Exception:
            pass

    # Fall back to local cache
    local_cache = _local_calculation_cache if cache_type == "calc" else _local_explanation_cache
    return local_cache.get(key)


def set_in_cache(key: str, data, cache_type: str = "calc"):
    """Store value in cache with timestamp for TTL."""
    # Store in persistent cache if available
    persistent_cache = _persistent_calc_cache if cache_type == "calc" else _persistent_explain_cache

    if persistent_cache is not None:
        try:
            # Serialize Pydantic models to dict for JSON storage
            serialized = data.model_dump() if hasattr(data, 'model_dump') else data
            persistent_cache[key] = {
                "data": serialized,
                "timestamp": time.time()
            }
        except Exception:
            pass

    # Also store in local cache as fallback (can store Pydantic models directly)
    local_cache = _local_calculation_cache if cache_type == "calc" else _local_explanation_cache
    local_cache[key] = data


# Legacy references for backward compatibility
calculation_cache = _local_calculation_cache
explanation_cache = _local_explanation_cache

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


@app.middleware("http")
async def report_commit(request, call_next):
    """Name the commit this deploy came from on every response.

    After a deploy, Modal can keep sending requests to the previous version's
    warm containers for a while, so the deploy's smoke test uses this header
    to tell them apart.
    """
    response = await call_next(request)
    response.headers["X-ACA-API-Commit"] = os.environ.get("ACA_API_COMMIT", "")
    return response


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
        "show_additional_bracket": data.show_additional_bracket,
        "show_simplified_bracket": data.show_simplified_bracket,
        "show_prior_year": data.show_prior_year,
        "year": data.year,
        "model_version": MODEL_VERSION,
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def household_situation(data: CalculateRequest) -> dict:
    """The household, with an income axis, for the request's coverage year."""
    return build_household_situation(
        age_head=data.age_head,
        age_spouse=data.age_spouse,
        dependent_ages=list(data.dependent_ages),
        state=data.state,
        county=data.county,
        zip_code=data.zip_code,
        year=data.year,
        with_axes=True,
    )


def run_baseline(data: CalculateRequest, situation: dict) -> dict:
    """Current law for the coverage year across the income axis."""
    year = data.year
    sim = Simulation(situation=situation)
    fpl = sim.calculate("tax_unit_fpg", period=year - 1)
    slcsp = sim.calculate("slcsp", map_to="household", period=year)
    return {
        "income": sim.calculate("employment_income", map_to="household", period=year),
        "ptc_baseline": sim.calculate("aca_ptc", map_to="household", period=year),
        "medicaid": sim.calculate("medicaid", map_to="household", period=year),
        "chip": sim.calculate("chip", map_to="household", period=year),
        # The benchmark covers the members eligible for the credit at each
        # income, so it is zero where none is; the scalar is its maximum.
        "slcsp_by_income": slcsp,
        "slcsp": float(np.max(slcsp)),
        # The credit measures income against the prior year's guideline
        # (aca_magi_fraction), so the page's FPL lines use that one too.
        "fpl": float(fpl[len(fpl) // 2]),
    }


def run_prior_year(data: CalculateRequest) -> dict:
    """Current law a year before the coverage year, for the same household and
    incomes (the income axis doesn't change with the year), or nothing if the
    request doesn't ask for it."""
    if not data.show_prior_year:
        return {}
    prior = data.model_copy(update={"year": data.year - 1})
    sim = Simulation(situation=household_situation(prior))
    fpl = sim.calculate("tax_unit_fpg", period=prior.year - 1)
    return {
        "ptc_prior_year": convert_to_native(
            sim.calculate("aca_ptc", map_to="household", period=prior.year)
        ),
        "slcsp_by_income_prior_year": convert_to_native(
            sim.calculate("slcsp", map_to="household", period=prior.year)
        ),
        "fpl_prior_year": float(fpl[len(fpl) // 2]),
    }


def run_scenario(data: CalculateRequest, situation: dict, flag: str, create_reform, zeros):
    """A scenario's credits across the income axis, or zeros if it is off."""
    if not getattr(data, flag):
        return zeros
    sim = Simulation(situation=situation, reform=create_reform())
    return sim.calculate("aca_ptc", map_to="household", period=data.year)


def build_response(
    data: CalculateRequest, baseline: dict, scenarios: dict, prior_year: dict
) -> CalculateResponse:
    return CalculateResponse(
        income=convert_to_native(baseline["income"]),
        ptc_baseline=convert_to_native(baseline["ptc_baseline"]),
        **{field: convert_to_native(values) for field, values in scenarios.items()},
        year=data.year,
        fpl=baseline["fpl"],
        fpl_year=data.year - 1,
        slcsp=baseline["slcsp"],
        slcsp_by_income=convert_to_native(baseline["slcsp_by_income"]),
        medicaid=convert_to_native(baseline["medicaid"]),
        chip=convert_to_native(baseline["chip"]),
        model_version=MODEL_VERSION,
        **prior_year,
    )


@app.post("/api/calculate", response_model=CalculateResponse)
async def calculate_ptc(data: CalculateRequest):
    """Calculate premium tax credits across income range.

    Returns arrays of PTC values under baseline, IRA extension, and 700% FPL
    scenarios for the specified household.
    """
    # Check cache first (persistent or local), unless the request skips it
    cache_key = get_cache_key(data)
    cached = None if data.skip_cache else get_from_cache(cache_key, "calc")
    if cached is not None:
        return cached

    try:
        situation = household_situation(data)
        prior_year = simulation_executor.submit(run_prior_year, data)
        baseline = run_baseline(data, situation)

        # Run the selected scenarios in parallel
        zeros = np.zeros_like(baseline["ptc_baseline"])
        futures = {
            field: simulation_executor.submit(run_scenario, data, situation, flag, create, zeros)
            for flag, field, create in SCENARIOS
        }
        scenarios = {field: future.result() for field, future in futures.items()}
        response = build_response(data, baseline, scenarios, prior_year.result())

        # Cache the result (persistent + local)
        if not data.skip_cache:
            set_in_cache(cache_key, response, "calc")
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
    # Check cache first (persistent or local) - if cached, return immediately,
    # unless the request skips it
    cache_key = get_cache_key(data)
    cached = None if data.skip_cache else get_from_cache(cache_key, "calc")
    if cached is not None:
        async def cached_response():
            yield f"data: {json.dumps({'step': 'cached', 'progress': 100, 'message': 'Using cached results'})}\n\n"
            result = cached.model_dump() if hasattr(cached, 'model_dump') else cached
            yield f"data: {json.dumps({'step': 'complete', 'result': result})}\n\n"
        return StreamingResponse(cached_response(), media_type="text/event-stream")

    async def generate():
        try:
            # Step 1: Build household situation
            yield f"data: {json.dumps({'step': 'setup', 'progress': 10, 'message': 'Setting up household...'})}\n\n"
            await asyncio.sleep(0)  # Allow event to be sent

            situation = household_situation(data)
            loop = asyncio.get_event_loop()
            prior_year = loop.run_in_executor(simulation_executor, run_prior_year, data)

            # Step 2: Run the current-law simulation
            message = f"Calculating current law ({data.year})..."
            yield f"data: {json.dumps({'step': 'baseline', 'progress': 25, 'message': message})}\n\n"
            await asyncio.sleep(0)

            baseline = run_baseline(data, situation)

            # Step 3: Run the selected scenarios in parallel
            yield f"data: {json.dumps({'step': 'reforms', 'progress': 50, 'message': 'Calculating policy reforms...'})}\n\n"
            await asyncio.sleep(0)

            zeros = np.zeros_like(baseline["ptc_baseline"])
            results = await asyncio.gather(
                *(
                    loop.run_in_executor(
                        simulation_executor, run_scenario, data, situation, flag, create, zeros
                    )
                    for flag, _, create in SCENARIOS
                )
            )
            scenarios = {field: result for (_, field, _), result in zip(SCENARIOS, results)}

            # Step 4: Complete
            yield f"data: {json.dumps({'step': 'finalizing', 'progress': 90, 'message': 'Finalizing results...'})}\n\n"
            await asyncio.sleep(0)

            response = build_response(data, baseline, scenarios, await prior_year)

            # Cache the result (persistent + local)
            if not data.skip_cache:
                set_in_cache(cache_key, response, "calc")

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
    chip_income = data.fpl * data.chip_threshold_pct / 100 if data.chip_threshold_pct > 0 else 0

    # Medicaid details
    medicaid_children_note = f" Children qualify up to {data.medicaid_child_threshold_pct}% FPL." if has_children else ""
    expansion_note = "This is a non-expansion state." if not data.is_expansion_state else "This is an expansion state."
    chip_line = f"- CHIP for children: {data.chip_threshold_pct}% FPL (${chip_income:,.0f})" if has_children and data.chip_threshold_pct > 0 else ""

    year = data.year

    # Build reform data section based on which reforms are selected
    reform_data_lines = [f"- Current-law PTC ({year}): ${data.ptc_baseline_at_sample:,.0f}/year (${data.ptc_baseline_at_sample/12:,.0f}/month)"]

    if data.show_ira:
        reform_data_lines.append(f"- H.R. 1834 PTC: ${data.ptc_ira_at_sample:,.0f}/year (${data.ptc_ira_at_sample/12:,.0f}/month)")
    if data.show_700fpl:
        reform_data_lines.append(f"- 700% FPL Bill PTC: ${data.ptc_700fpl_at_sample:,.0f}/year (${data.ptc_700fpl_at_sample/12:,.0f}/month)")
    if data.show_additional_bracket:
        reform_data_lines.append(f"- Additional Bracket PTC: ${data.ptc_additional_bracket_at_sample:,.0f}/year (${data.ptc_additional_bracket_at_sample/12:,.0f}/month)")
    if data.show_simplified_bracket:
        reform_data_lines.append(f"- Simplified Bracket PTC: ${data.ptc_simplified_bracket_at_sample:,.0f}/year (${data.ptc_simplified_bracket_at_sample/12:,.0f}/month)")
    if data.show_prior_year:
        reform_data_lines.insert(0, f"- Current-law PTC ({year - 1}): ${data.ptc_prior_year_at_sample:,.0f}/year (${data.ptc_prior_year_at_sample/12:,.0f}/month)")

    reform_data_text = "\n".join(reform_data_lines)

    # Build reform descriptions for the prompt
    reform_descriptions = []
    if data.show_ira:
        reform_descriptions.append("""
H.R. 1834 (show_ira=True):
- Would extend the enhanced premium tax credits of the American Rescue Plan Act and the Inflation Reduction Act, which expired after 2025, for 2026 through 2028
- Required contributions run from 0% of income up to 150% FPL to 8.5% at 400% FPL and above
- Removes the income eligibility limit at 400% FPL
- Passed the House on January 8, 2026; it has not been enacted""")

    if data.show_700fpl:
        reform_descriptions.append("""
700% FPL BILL (show_700fpl=True):
- Bipartisan Health Insurance Affordability Act, introduced by Reps. Dunn and Schneider on December 9, 2025; it has not been enacted
- Extends subsidies up to 700% FPL (vs the current 400% FPL limit)
- Contribution rates: 2-4% at 200-250% FPL, 4-6% at 250-300%, 6-8.5% at 300-400%, 8.5% at 400-600%, 8.5-9.25% at 600-700%
- Eligibility ends at 700% FPL""")

    if data.show_additional_bracket:
        reform_descriptions.append("""
ADDITIONAL BRACKET (show_additional_bracket=True):
- CRFB proposal: "Extend Subsidies Below 300% of Poverty, Extend Phase Up Above"
- Adds a new bracket above 400% FPL with a linear phase-out
- Contribution percentage increases by ~4 percentage points per 100% FPL above transition threshold
- Creates a more gradual cliff than current law
- CRFB estimates it would cost about $280 billion through 2035, against $350 billion for the full IRA extension""")

    if data.show_simplified_bracket:
        reform_descriptions.append("""
SIMPLIFIED BRACKET (show_simplified_bracket=True):
- CRFB proposal: sets subsidies "about halfway between base and enhanced rate"
- Single linear phase-out starting at 100% FPL
- Contribution percentage increases by 4 percentage points per 100% FPL from the start
- Simplest structure, with the fastest phase-out of the options
- CRFB estimates it would cost about $175 billion through 2035""")

    reform_descriptions_text = "\n".join(reform_descriptions) if reform_descriptions else "No reforms selected."

    # Build dynamic sections based on selected reforms
    section_num = 1
    sections_spec = []
    sections_json = []

    # Section 1: Always intro
    prior_year_note = (
        f" Compare it with the {year - 1} benchmark of ${data.slcsp_prior_year:,.0f}/year, and"
        f" say how the household's current-law credit at ${data.sample_income:,.0f} changes"
        f" between {year - 1} and {year}."
        if data.show_prior_year
        else ""
    )
    sections_spec.append(f'{section_num}. id: "intro", chartState: "all_programs" - Introduce this household and their location. State the SLCSP cost of ${data.slcsp:,.0f}/year.{prior_year_note}')
    sections_json.append('{{"id": "intro", "title": "...", "content": "...", "chartState": "all_programs"}}')
    section_num += 1

    # Section 2: Medicaid
    sections_spec.append(f'{section_num}. id: "medicaid", chartState: "medicaid_focus" - Explain Medicaid eligibility in {state_name}. Adults qualify up to {data.medicaid_adult_threshold_pct}% FPL (${medicaid_adult_income:,.0f}).{medicaid_children_note} {expansion_note}')
    sections_json.append('{{"id": "medicaid", "title": "...", "content": "...", "chartState": "medicaid_focus"}}')
    section_num += 1

    # Section 3: CHIP or Cliff
    if has_children:
        sections_spec.append(f'{section_num}. id: "chip", chartState: "chip_focus" - Explain CHIP coverage for children up to {data.chip_threshold_pct}% FPL (${chip_income:,.0f}).')
        sections_json.append('{{"id": "chip", "title": "...", "content": "...", "chartState": "chip_focus"}}')
    else:
        sections_spec.append(f'{section_num}. id: "cliff", chartState: "cliff_focus" - Explain the 400% FPL cliff at ${data.fpl_400_income:,.0f} where current-law subsidies end. Above this income, there are no premium tax credits under current law ({year}).')
        sections_json.append('{{"id": "cliff", "title": "...", "content": "...", "chartState": "cliff_focus"}}')
    section_num += 1

    # Add a section for each selected reform
    if data.show_ira:
        diff = data.ptc_ira_at_sample - data.ptc_baseline_at_sample
        sections_spec.append(f'{section_num}. id: "ira", chartState: "ira_impact" - Explain H.R. 1834, which would extend the enhanced credits. At ${data.sample_income:,.0f} income, it provides ${data.ptc_ira_at_sample:,.0f}/year vs current law ${data.ptc_baseline_at_sample:,.0f}/year (difference: ${diff:,.0f}/year). Explain the 8.5% cap and removal of the 400% FPL limit.')
        sections_json.append('{{"id": "ira", "title": "...", "content": "...", "chartState": "ira_impact"}}')
        section_num += 1

    if data.show_700fpl:
        diff = data.ptc_700fpl_at_sample - data.ptc_baseline_at_sample
        sections_spec.append(f'{section_num}. id: "fpl700", chartState: "fpl700_focus" - Explain the 700% FPL Bill (Bipartisan Health Insurance Affordability Act). At ${data.sample_income:,.0f} income, it provides ${data.ptc_700fpl_at_sample:,.0f}/year vs current law ${data.ptc_baseline_at_sample:,.0f}/year (difference: ${diff:,.0f}/year). Explain the graduated brackets up to 700% FPL.')
        sections_json.append('{{"id": "fpl700", "title": "...", "content": "...", "chartState": "fpl700_focus"}}')
        section_num += 1

    if data.show_additional_bracket:
        diff = data.ptc_additional_bracket_at_sample - data.ptc_baseline_at_sample
        sections_spec.append(f'{section_num}. id: "additional", chartState: "additional_focus" - Explain the Additional Bracket reform (CRFB proposal). At ${data.sample_income:,.0f} income, it provides ${data.ptc_additional_bracket_at_sample:,.0f}/year vs current law ${data.ptc_baseline_at_sample:,.0f}/year (difference: ${diff:,.0f}/year). This proposal extends subsidies below 300% FPL while adding a linear phase-up above; CRFB estimates it would cost about $280B, against $350B for the full IRA extension.')
        sections_json.append('{{"id": "additional", "title": "...", "content": "...", "chartState": "additional_focus"}}')
        section_num += 1

    if data.show_simplified_bracket:
        diff = data.ptc_simplified_bracket_at_sample - data.ptc_baseline_at_sample
        sections_spec.append(f'{section_num}. id: "simplified", chartState: "simplified_focus" - Explain the Simplified Bracket reform (CRFB proposal). At ${data.sample_income:,.0f} income, it provides ${data.ptc_simplified_bracket_at_sample:,.0f}/year vs current law ${data.ptc_baseline_at_sample:,.0f}/year (difference: ${diff:,.0f}/year). This proposal uses a single linear phase-out from 100% FPL, setting subsidies about halfway between current-law and enhanced rates; CRFB estimates it would cost about $175B.')
        sections_json.append('{{"id": "simplified", "title": "...", "content": "...", "chartState": "simplified_focus"}}')
        section_num += 1

    # Final comparison section (always included)
    selected_reforms = []
    if data.show_ira:
        selected_reforms.append("H.R. 1834")
    if data.show_700fpl:
        selected_reforms.append("700% FPL Bill")
    if data.show_additional_bracket:
        selected_reforms.append("Additional Bracket")
    if data.show_simplified_bracket:
        selected_reforms.append("Simplified Bracket")

    if len(selected_reforms) > 1:
        reforms_list = ", ".join(selected_reforms)
        sections_spec.append(f'{section_num}. id: "comparison", chartState: "both_reforms" - Compare all selected reforms: current law vs {reforms_list}. Use the exact PTC values provided for ${data.sample_income:,.0f} income. Summarize which provides the most/least subsidy for this household.')
        sections_json.append('{{"id": "comparison", "title": "...", "content": "...", "chartState": "both_reforms"}}')

    prior_year_benchmark = (
        f"\n- Annual benchmark plan (SLCSP) in {year - 1}: ${data.slcsp_prior_year:,.0f}"
        f" (${data.slcsp_prior_year/12:,.0f}/month)"
        if data.show_prior_year
        else ""
    )
    sections_spec_text = "\n\n".join(sections_spec)
    sections_json_text = ",\n    ".join(sections_json)
    total_sections = len(sections_json)

    prompt = f"""You are creating a factual, neutral scrollytelling narrative explaining ACA premium tax credits for a specific household.

IMPORTANT GUIDELINES:
- Be strictly factual and neutral. Do NOT express opinions about whether policies are good, bad, beneficial, or harmful.
- Do NOT use value-laden words like "unfortunately", "thankfully", "crucial", "vital", "struggle", etc.
- Simply describe what the policies are and how they affect this household's numbers.
- Use exact dollar amounts and percentages provided - do not round or approximate.
- Every reform below is a proposal, not law. Say so, and describe {year} current law as the law in effect.
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
- Coverage year: {year}
- Federal Poverty Level (FPL) for this household: ${data.fpl:,.0f} (the {year - 1} poverty guideline, which {year} premium tax credits use)
- 400% FPL (current-law subsidy limit): ${data.fpl_400_income:,.0f}
- 700% FPL: ${data.fpl_700_income:,.0f}
- Annual benchmark plan (SLCSP): ${data.slcsp:,.0f} (${data.slcsp/12:,.0f}/month){prior_year_benchmark}

SELECTED REFORMS AND THEIR DETAILS:
{reform_descriptions_text}

AT SAMPLE INCOME OF ${data.sample_income:,.0f} ({data.sample_income/data.fpl*100:.0f}% FPL):
{reform_data_text}

Generate exactly {total_sections} scrollytelling sections in JSON format. Each section should have:
- id: unique identifier
- title: descriptive section title (5-10 words)
- content: 2-3 short paragraphs using **bold** for key numbers. Use exact values provided above.
- chartState: MUST be one of these exact strings: "all_programs", "medicaid_focus", "chip_focus", "cliff_focus", "ira_impact", "fpl700_focus", "additional_focus", "simplified_focus", "both_reforms"

REQUIRED SECTIONS (use these EXACT chartState values and ids):
{sections_spec_text}

Return ONLY valid JSON:
{{
  "sections": [
    {sections_json_text}
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
        # Include reform flags so different selections get different explanations
        "show_ira": data.show_ira,
        "show_700fpl": data.show_700fpl,
        "show_additional_bracket": data.show_additional_bracket,
        "show_simplified_bracket": data.show_simplified_bracket,
        "show_prior_year": data.show_prior_year,
        "slcsp_prior_year": round(data.slcsp_prior_year, 0),
        "year": data.year,
        "model_version": MODEL_VERSION,
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


@app.post("/api/explain", response_model=ExplainResponse)
async def explain_with_ai(data: ExplainRequest):
    """Generate AI-powered scrollytelling narrative for a household."""

    # Check cache first (persistent or local)
    cache_key = get_explain_cache_key(data)
    cached = get_from_cache(cache_key, "explain")
    if cached is not None:
        return cached

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
            model="claude-sonnet-5-5",
            max_tokens=16000,
            # The locked SDK predates the output_config keyword argument.
            extra_body={"output_config": {"effort": "low"}},
            messages=[{"role": "user", "content": prompt}],
        )

        if message.stop_reason == "refusal":
            raise ValueError("AI refused to generate an explanation")

        # Thinking blocks can precede or separate the JSON text blocks.
        response_text = "".join(
            block.text for block in message.content if block.type == "text"
        )
        if not response_text.strip():
            raise ValueError("AI response did not contain any text")

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

        # Cache the result (persistent + local)
        set_in_cache(cache_key, response, "explain")
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
