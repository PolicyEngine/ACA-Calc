"""
Precompute the Overview's example household: a single adult (45) in Lebanon
County, PA, earning 650% of the poverty guideline 2027 credits use.

Above 400% FPL the enhanced credits of 2021-2025 left a credit and current law
since 2026 leaves none, so this household shows the cliff:
- 2025: the enhanced credits in effect
- 2026 and 2027: current law
- 2027 under H.R. 1834 and the 700% FPL bill

The income is the same in every year, so the changes are the law's and the
premiums', not the household's. Writes src/data/households/cliff_demo.json,
which the Overview page reads. Rerun after every policyengine-us pin.
"""

import gc
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_700fpl_reform, create_enhanced_ptc_reform

OUTPUT = Path(__file__).parent / "src" / "data" / "households" / "cliff_demo.json"
HOUSEHOLD = dict(age_head=45, age_spouse=None, dependent_ages=[], state="PA", county="Lebanon County")
FPL_PERCENT = 650
# The charts show this year.
YEAR = 2027


def sweep(year, reform=None):
    """The household across the income axis for coverage year `year`."""
    situation = build_household_situation(**HOUSEHOLD, year=year, with_axes=True)
    sim = Simulation(situation=situation, reform=reform)
    fpl = sim.calculate("tax_unit_fpg", period=year - 1)
    result = {
        name: sim.calculate(name, map_to="household", period=year)
        for name in ("employment_income", "aca_ptc", "slcsp", "medicaid", "chip")
    }
    # The credit measures income against the prior year's guideline.
    result["fpl"] = float(fpl[len(fpl) // 2])
    return result


def point(result, index):
    """Annual values at one point on the axis."""
    return {
        "fpl": result["fpl"],
        "fpl_percent": round(100 * float(result["employment_income"][index]) / result["fpl"]),
        "slcsp": float(result["slcsp"][index]),
        "ptc": float(result["aca_ptc"][index]),
    }


def main():
    print("Precomputing the Overview's example household...")
    current = {year: sweep(year) for year in (2025, 2026, YEAR)}
    hr1834 = sweep(YEAR, create_enhanced_ptc_reform())
    bill700 = sweep(YEAR, create_700fpl_reform())

    income = current[YEAR]["employment_income"]
    index = int(np.argmin(np.abs(income - FPL_PERCENT / 100 * current[YEAR]["fpl"])))
    example_income = float(income[index])

    years = {
        # policyengine-us applies the enhanced schedule through 2025 as law.
        "2025": {**point(current[2025], index), "law": "Enhanced credits (ARPA, extended by the IRA)"},
        "2026": {**point(current[2026], index), "law": "Current law"},
        str(YEAR): {**point(current[YEAR], index), "law": "Current law"},
    }
    proposals = {
        "hr1834": {**point(hr1834, index), "name": "H.R. 1834"},
        "bill700": {**point(bill700, index), "name": "700% FPL bill"},
    }

    data = {
        "household_key": "cliff_demo",
        "household_info": {
            "name": "Pennsylvania Single Adult",
            "shortName": "PA Demo",
            "description": f"Single adult (45) in Lebanon County, PA at {FPL_PERCENT}% FPL",
            "location": "Lebanon County, PA",
            "age": HOUSEHOLD["age_head"],
            "state": HOUSEHOLD["state"],
            "county": HOUSEHOLD["county"],
            "fpl_percent": FPL_PERCENT,
            "isExpansion": True,
        },
        "model_version": version("policyengine-us"),
        "year": YEAR,
        "example_income": example_income,
        "years": years,
        "proposals": proposals,
        # Income sweeps for the charts, for YEAR
        "income": income.tolist(),
        "medicaid": current[YEAR]["medicaid"].tolist(),
        "chip": current[YEAR]["chip"].tolist(),
        "ptc_baseline": current[YEAR]["aca_ptc"].tolist(),
        "ptc_ira": hr1834["aca_ptc"].tolist(),
        "ptc_700fpl": bill700["aca_ptc"].tolist(),
        "slcsp": current[YEAR]["slcsp"].tolist(),
        "fpl": current[YEAR]["fpl"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved {OUTPUT}")

    print(f"\nIncome ${example_income:,.0f}")
    print(f"{'':<34} {'FPL':>6} {'SLCSP/mo':>10} {'PTC/mo':>9} {'Net/mo':>9}")
    rows = [(f"{y} {v['law']}", v) for y, v in years.items()]
    rows += [(f"{YEAR} {v['name']}", v) for v in proposals.values()]
    for label, v in rows:
        net = max(0, v["slcsp"] - v["ptc"]) / 12
        print(f"{label:<34} {v['fpl_percent']:>5}% {v['slcsp'] / 12:>10,.0f} {v['ptc'] / 12:>9,.0f} {net:>9,.0f}")
    gc.collect()


if __name__ == "__main__":
    main()
