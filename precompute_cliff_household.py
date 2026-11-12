"""
Precompute the Overview's example household: a single adult (45) in Lebanon
County, PA, earning 650% of the poverty guideline 2027 credits use.

Above 400% FPL current law gives no credit, so this household pays the whole
benchmark premium in 2026 and in 2027, the increase included. The file has
- 2026 and 2027 under current law
- 2027 under H.R. 1834, which would revive the enhanced credits of 2021-2025
at the household's income, and across incomes for the charts.

The income is the same in both years, so the changes are the law's and the
premiums', not the household's. Writes src/data/households/cliff_demo.json,
which the Overview page reads. Rerun after every policyengine-us pin.
"""

import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_enhanced_ptc_reform

OUTPUT = Path(__file__).parent / "src" / "data" / "households" / "cliff_demo.json"
HOUSEHOLD = dict(age_head=45, age_spouse=None, dependent_ages=[], state="PA", county="Lebanon County")
FPL_PERCENT = 650
YEAR = 2027
PRIOR_YEAR = 2026


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
    current = {year: sweep(year) for year in (PRIOR_YEAR, YEAR)}
    hr1834 = sweep(YEAR, create_enhanced_ptc_reform())

    income = current[YEAR]["employment_income"]
    assert np.array_equal(income, current[PRIOR_YEAR]["employment_income"])
    index = int(np.argmin(np.abs(income - FPL_PERCENT / 100 * current[YEAR]["fpl"])))
    example_income = float(income[index])

    years = {str(year): {**point(current[year], index), "law": "Current law"} for year in current}
    proposals = {"hr1834": {**point(hr1834, index), "name": "H.R. 1834"}}

    data = {
        "household_key": "cliff_demo",
        "household_info": {
            "name": "Pennsylvania Single Adult",
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
        "prior_year": PRIOR_YEAR,
        "example_income": example_income,
        "years": years,
        "proposals": proposals,
        # Income sweeps for the charts, named as the calculator API names them.
        "income": income.tolist(),
        "medicaid": current[YEAR]["medicaid"].tolist(),
        "chip": current[YEAR]["chip"].tolist(),
        "ptc_baseline": current[YEAR]["aca_ptc"].tolist(),
        "ptc_ira": hr1834["aca_ptc"].tolist(),
        "ptc_prior_year": current[PRIOR_YEAR]["aca_ptc"].tolist(),
        "slcsp_by_income": current[YEAR]["slcsp"].tolist(),
        "slcsp_by_income_prior_year": current[PRIOR_YEAR]["slcsp"].tolist(),
        "fpl": current[YEAR]["fpl"],
        "fpl_prior_year": current[PRIOR_YEAR]["fpl"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved {OUTPUT}")

    print(f"\nIncome ${example_income:,.0f}")
    print(f"{'':<24} {'FPL':>6} {'SLCSP/mo':>10} {'PTC/mo':>9} {'Net/mo':>9}")
    rows = [(f"{y} {v['law']}", v) for y, v in years.items()]
    rows += [(f"{YEAR} {v['name']}", v) for v in proposals.values()]
    for label, v in rows:
        net = max(0, v["slcsp"] - v["ptc"]) / 12
        print(f"{label:<24} {v['fpl_percent']:>5}% {v['slcsp'] / 12:>10,.0f} {v['ptc'] / 12:>9,.0f} {net:>9,.0f}")


if __name__ == "__main__":
    main()
