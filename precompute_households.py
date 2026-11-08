"""
Precompute household data for the scrollytelling interactive.

Run this script to generate JSON files for each preset household.
This avoids running expensive PolicyEngine simulations when users load the app.

Usage:
    python precompute_households.py

Writes src/data/households/, which the Explore Households page reads. Rerun
after every policyengine-us pin.
"""

import gc
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from policyengine_us import Simulation
from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_enhanced_ptc_reform, create_700fpl_reform

# The coverage year the Explore Households page shows.
YEAR = 2027

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
    "texas_couple": {
        "name": "Young Texas Couple",
        "description": "A married couple (ages 28 and 27) in Harris County, Texas",
        "age_head": 28,
        "age_spouse": 27,
        "dependent_ages": [],
        "state": "TX",
        "county": "Harris County",
        "is_expansion_state": False,
        "key_insight": "Texas didn't expand Medicaid. Adults below 100% FPL fall into the coverage gap with no affordable options.",
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
    """Calculate all chart data for a household, for coverage year YEAR."""
    print(f"  Computing {household_key}...")

    situation = build_household_situation(
        age_head=household["age_head"],
        age_spouse=household["age_spouse"],
        dependent_ages=household["dependent_ages"],
        state=household["state"],
        county=household["county"],
        year=YEAR,
        with_axes=True,
    )

    def sweep(reform=None):
        sim = Simulation(situation=situation, reform=reform)
        return sim, sim.calculate("aca_ptc", map_to="household", period=YEAR)

    print("    Running current law...")
    sim_baseline, ptc_baseline = sweep()
    print("    Running H.R. 1834...")
    _, ptc_ira = sweep(create_enhanced_ptc_reform())
    print("    Running the 700% FPL bill...")
    _, ptc_700fpl = sweep(create_700fpl_reform())

    income_range = sim_baseline.calculate("employment_income", map_to="household", period=YEAR)
    # The credit measures income against the prior year's guideline.
    fpl = sim_baseline.calculate("tax_unit_fpg", period=YEAR - 1)
    data = {
        "household_key": household_key,
        "household_info": household,
        "year": YEAR,
        "model_version": version("policyengine-us"),
        "income": income_range.tolist(),
        "medicaid": sim_baseline.calculate("medicaid", map_to="household", period=YEAR).tolist(),
        "chip": sim_baseline.calculate("chip", map_to="household", period=YEAR).tolist(),
        "ptc_baseline": ptc_baseline.tolist(),
        "ptc_ira": ptc_ira.tolist(),
        "ptc_700fpl": ptc_700fpl.tolist(),
        "fpl": float(fpl[len(fpl) // 2]),
        # Medicaid measures income against the coverage year's guideline.
        "fpl_current": float(sim_baseline.calculate("tax_unit_fpg", period=YEAR)[len(fpl) // 2]),
        "slcsp": float(np.max(sim_baseline.calculate("slcsp", map_to="household", period=YEAR))),
    }

    gc.collect()
    return data


def main():
    """Precompute and save all household data."""
    output_dir = Path(__file__).parent / "src" / "data" / "households"
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
