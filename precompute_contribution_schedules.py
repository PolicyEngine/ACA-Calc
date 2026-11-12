"""
Precompute the Overview's contribution schedule chart: the share of income a
household pays for the benchmark plan, by income as a percent of the poverty
guideline, under current law (2026 and 2027) and the enhanced schedule
(2021-2025, which H.R. 1834 would revive).

Computed by policyengine-us across an income axis for a single adult in
Travis County, TX: Texas didn't expand Medicaid, so every income from 100% FPL
up is in the credit's range. Writes src/data/contribution_schedules.json.
Rerun after every policyengine-us pin.
"""

import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_enhanced_ptc_reform

OUTPUT = Path(__file__).parent / "src" / "data" / "contribution_schedules.json"
# Percent of the poverty guideline, in steps of 1%.
FPL_PERCENTS = np.arange(0, 801)


def schedule(year, reform=None):
    """Applicable percentage (percent of income) at each FPL percent, None where
    the credit isn't available."""
    situation = build_household_situation(40, None, [], "TX", county="Travis County", year=year)
    fpg = float(Simulation(situation=situation).calculate("tax_unit_fpg", year - 1)[0])
    # A tenth of a percent above each step, so the truncated FPL fraction lands on it.
    situation["axes"] = [[{
        "name": "employment_income",
        "count": len(FPL_PERCENTS),
        "min": 0.001 * fpg,
        "max": (FPL_PERCENTS[-1] / 100 + 0.001) * fpg,
        "period": year,
    }]]
    sim = Simulation(situation=situation, reform=reform)
    rate = sim.calculate("aca_required_contribution_percentage", year)
    eligible = sim.calculate("is_aca_ptc_eligible", year)
    fraction = sim.calculate("aca_magi_fraction", year)
    assert np.allclose(fraction, FPL_PERCENTS / 100), "the axis missed the FPL steps"
    return [round(100 * float(r), 2) if e else None for r, e in zip(rate, eligible)]


def main():
    print("Precomputing contribution schedules...")
    data = {
        "model_version": version("policyengine-us"),
        "fpl_percent": FPL_PERCENTS.tolist(),
        "schedules": {
            "current_2026": schedule(2026),
            "current_2027": schedule(2027),
            # The enhanced schedule doesn't change by year.
            "enhanced": schedule(2027, create_enhanced_ptc_reform()),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data), encoding="utf-8")
    print(f"Saved {OUTPUT}")
    for name, values in data["schedules"].items():
        at = {pct: values[pct] for pct in (100, 150, 200, 300, 400, 450, 650, 750)}
        print(f"  {name:<13} {at}")


if __name__ == "__main__":
    main()
