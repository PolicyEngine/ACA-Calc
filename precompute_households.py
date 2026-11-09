"""
Precompute the Overview's example households: what each pays for its benchmark
plan in 2026 and 2027 under current law, and in 2027 under H.R. 1834, which
would revive the enhanced credits of 2021-2025.

Each household's income is the same in both years, so the changes are the
law's and the premiums', not the household's. Writes
src/data/households/examples.json, which the Overview reads. Rerun after every
policyengine-us pin.
"""

import json
from importlib.metadata import version
from pathlib import Path

from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_enhanced_ptc_reform

OUTPUT = Path(__file__).parent / "src" / "data" / "households" / "examples.json"
YEAR = 2027
PRIOR_YEAR = 2026

# Two households below current law's 400% FPL limit and two above it.
EXAMPLES = [
    {
        "key": "texas_single",
        "name": "Single adult",
        "description": "Age 40, Harris County, Texas",
        "household": dict(age_head=40, age_spouse=None, dependent_ages=[], state="TX", county="Harris County"),
        "income": 40_000,
    },
    {
        "key": "florida_family",
        "name": "Family of four",
        "description": "Parents aged 40, children aged 10 and 8, Hillsborough County, Florida",
        "household": dict(age_head=40, age_spouse=40, dependent_ages=[10, 8], state="FL", county="Hillsborough County"),
        "income": 75_000,
    },
    {
        "key": "pennsylvania_single",
        "name": "Single adult",
        "description": "Age 45, Lebanon County, Pennsylvania",
        "household": dict(age_head=45, age_spouse=None, dependent_ages=[], state="PA", county="Lebanon County"),
        "income": 104_000,
    },
    {
        "key": "california_couple",
        "name": "Couple in their 60s",
        "description": "Ages 64 and 62, San Benito County, California",
        "household": dict(age_head=64, age_spouse=62, dependent_ages=[], state="CA", county="San Benito County"),
        "income": 90_000,
    },
]


def scenario(example, year, reform=None):
    """The household's benchmark premium and credit in coverage year `year`,
    with all its income as the head's earnings."""
    situation = build_household_situation(**example["household"], year=year)
    situation["people"]["you"]["employment_income"] = {year: example["income"]}
    sim = Simulation(situation=situation, reform=reform)
    slcsp = float(sim.calculate("slcsp", year)[0])
    ptc = float(sim.calculate("aca_ptc", year)[0])
    # The credit measures income against the prior year's guideline.
    fpl = float(sim.calculate("tax_unit_fpg", year - 1)[0])
    return {
        "fpl_percent": round(100 * example["income"] / fpl),
        "slcsp": slcsp,
        "ptc": ptc,
        "net_premium": max(0.0, slcsp - ptc),
        # Members buying a marketplace plan, and members on Medicaid or CHIP.
        "marketplace_members": int(sim.calculate("pays_aca_premium", year).sum()),
        "medicaid_or_chip_members": int(
            ((sim.calculate("medicaid", year) > 0) | (sim.calculate("chip", year) > 0)).sum()
        ),
    }


def main():
    print("Precomputing the Overview's example households...")
    examples = []
    for example in EXAMPLES:
        scenarios = {
            "current_2026": scenario(example, PRIOR_YEAR),
            "current_2027": scenario(example, YEAR),
            "hr1834_2027": scenario(example, YEAR, create_enhanced_ptc_reform()),
        }
        examples.append({key: example[key] for key in ("key", "name", "description", "income")} | {
            "people": 1 + bool(example["household"]["age_spouse"]) + len(example["household"]["dependent_ages"]),
            "scenarios": scenarios,
        })
        print(f"  {example['key']}: " + ", ".join(
            f"{name} {values['fpl_percent']}% FPL, benchmark ${values['slcsp'] / 12:,.0f}/mo, "
            f"credit ${values['ptc'] / 12:,.0f}/mo, net ${values['net_premium'] / 12:,.0f}/mo"
            for name, values in scenarios.items()
        ))

    data = {"model_version": version("policyengine-us"), "year": YEAR, "prior_year": PRIOR_YEAR, "examples": examples}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
