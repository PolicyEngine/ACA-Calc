"""FastAPI backend for ACA Premium Tax Credit calculations.

This module provides a REST API endpoint for calculating how ACA policy
changes affect household premium tax credits across income levels.
"""

import os

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import (
    create_enhanced_ptc_reform,
    create_700fpl_reform,
)

from .models import CalculateRequest, CalculateResponse

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


def main():
    """Run the FastAPI server with uvicorn."""
    import uvicorn

    port = int(os.environ.get("PORT", 5001))
    print(f"Starting ACA Calculator API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
