"""
Precompute household data for the scrollytelling interactive.

Run this script to generate JSON files for each preset household.
This avoids running expensive PolicyEngine simulations when users load the app.

Usage:
    python precompute_households.py
"""

import json
import numpy as np
import gc
from pathlib import Path
from policyengine_us import Simulation
from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_enhanced_ptc_reform, create_700fpl_reform

# Preset households (same as in app.py)
PRESET_HOUSEHOLDS = {
    "florida_family": {
        "name": "Florida Family of 4",
        "description": "Two parents (age 40) with two children (ages 10 and 8) in Florida",
        "age_head": 40,
        "age_spouse": 40,
        "dependent_ages": [10, 8],
        "state": "FL",
        "county": "Hillsborough County",
        "is_expansion_state": False,
        "key_insight": "Florida didn't expand Medicaid, creating a coverage gap for parents between 32% and 100% FPL.",
    },
    "california_couple": {
        "name": "California Couple",
        "description": "An older couple (ages 64 and 62) in San Benito County, California",
        "age_head": 64,
        "age_spouse": 62,
        "dependent_ages": [],
        "state": "CA",
        "county": "San Benito County",
        "is_expansion_state": True,
        "key_insight": "This older couple faces high premiums due to age-based rating, making subsidies especially valuable.",
    },
    "texas_single": {
        "name": "Single Adult in Texas",
        "description": "A single 35-year-old in Harris County, Texas",
        "age_head": 35,
        "age_spouse": None,
        "dependent_ages": [],
        "state": "TX",
        "county": "Harris County",
        "is_expansion_state": False,
        "key_insight": "Texas didn't expand Medicaid. Single adults below 100% FPL fall into the coverage gap with no affordable options.",
    },
    "ny_family": {
        "name": "Young Family in New York",
        "description": "Two parents (ages 30 and 28) with a toddler (age 2) in New York City",
        "age_head": 30,
        "age_spouse": 28,
        "dependent_ages": [2],
        "state": "NY",
        "county": "New York County",
        "is_expansion_state": True,
        "key_insight": "New York expanded Medicaid, so this family has coverage options at lower incomes, but faces the 400% FPL cliff.",
    },
}


def calculate_household_data(household_key: str, household: dict) -> dict:
    """Calculate all chart data for a household."""
    print(f"  Computing {household_key}...")

    # Build household situation
    base_situation = build_household_situation(
        age_head=household["age_head"],
        age_spouse=household["age_spouse"],
        dependent_ages=household["dependent_ages"],
        state=household["state"],
        county=household["county"],
        year=2026,
        with_axes=True,
    )

    # Create reforms
    reform_ira = create_enhanced_ptc_reform()
    reform_700fpl = create_700fpl_reform()

    # Run simulations
    print(f"    Running baseline simulation...")
    sim_baseline = Simulation(situation=base_situation)

    print(f"    Running IRA reform simulation...")
    sim_ira = Simulation(situation=base_situation, reform=reform_ira)

    sim_700fpl = None
    if reform_700fpl:
        print(f"    Running 700% FPL reform simulation...")
        sim_700fpl = Simulation(situation=base_situation, reform=reform_700fpl)

    # Get income range
    income_range = sim_baseline.calculate("employment_income", map_to="household", period=2026)

    # Calculate all values
    data = {
        "household_key": household_key,
        "household_info": household,
        "income": income_range.tolist(),
        "medicaid": sim_baseline.calculate("medicaid_cost", map_to="household", period=2026).tolist(),
        "chip": sim_baseline.calculate("per_capita_chip", map_to="household", period=2026).tolist(),
        "ptc_baseline": sim_baseline.calculate("aca_ptc", map_to="household", period=2026).tolist(),
        "ptc_ira": sim_ira.calculate("aca_ptc", map_to="household", period=2026).tolist(),
        "ptc_700fpl": sim_700fpl.calculate("aca_ptc", map_to="household", period=2026).tolist() if sim_700fpl else [],
        "fpl": float(sim_baseline.calculate("tax_unit_fpg", period=2026)[len(income_range)//2]),
        "slcsp": float(np.max(sim_baseline.calculate("slcsp", map_to="household", period=2026))),
    }

    # Calculate net income for impact chart
    print(f"    Running net income simulations...")
    base_situation["tax_units"]["your tax unit"]["tax_unit_itemizes"] = {2026: False}

    sim_baseline_net = Simulation(situation=base_situation)
    sim_ira_net = Simulation(situation=base_situation, reform=reform_ira)
    sim_700fpl_net = Simulation(situation=base_situation, reform=reform_700fpl) if reform_700fpl else None

    data["net_income_baseline"] = sim_baseline_net.calculate(
        "household_net_income_including_health_benefits", map_to="household", period=2026
    ).tolist()
    data["net_income_ira"] = sim_ira_net.calculate(
        "household_net_income_including_health_benefits", map_to="household", period=2026
    ).tolist()
    data["net_income_700fpl"] = sim_700fpl_net.calculate(
        "household_net_income_including_health_benefits", map_to="household", period=2026
    ).tolist() if sim_700fpl_net else []

    gc.collect()
    return data


def main():
    """Precompute and save all household data."""
    output_dir = Path(__file__).parent / "data" / "households"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Precomputing household data for ACA scrollytelling interactive...")
    print(f"Output directory: {output_dir}")
    print()

    all_data = {}

    for household_key, household in PRESET_HOUSEHOLDS.items():
        print(f"Processing: {household['name']}")
        data = calculate_household_data(household_key, household)
        all_data[household_key] = data

        # Save individual file
        output_file = output_dir / f"{household_key}.json"
        with open(output_file, "w") as f:
            json.dump(data, f)
        print(f"  Saved to {output_file}")
        print()

    # Also save combined file for single-load option
    combined_file = output_dir / "all_households.json"
    with open(combined_file, "w") as f:
        json.dump(all_data, f)
    print(f"Saved combined data to {combined_file}")

    print()
    print("Done! Precomputed data ready for the scrollytelling app.")


if __name__ == "__main__":
    main()
