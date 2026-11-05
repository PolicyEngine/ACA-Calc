"""The IRA-extension scenario builds on the installed policyengine-us and applies
the enhanced (ARPA/IRA) schedule.

policyengine-us #7067 replaced the bracket scale gov.aca.required_contribution_percentage
with three lists (threshold, initial, final). The reform set the old scale's
brackets, so every request with the scenario on failed with "Could not find the
parameter gov.aca.required_contribution_percentage[0].amount".
"""

import numpy as np
import pytest
from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import (
    ENHANCED_FINAL,
    ENHANCED_INITIAL,
    ENHANCED_THRESHOLDS,
    create_enhanced_ptc_reform,
)

YEAR = 2026


def enhanced_rate(fraction: float) -> float:
    """The enhanced applicable percentage at a multiple of the poverty line,
    worked out by hand from the ARPA schedule: linear within each band, 8.5%
    above 400%."""
    if fraction >= ENHANCED_THRESHOLDS[-1]:
        return ENHANCED_FINAL[-1]
    for k in range(len(ENHANCED_INITIAL)):
        lo, hi = ENHANCED_THRESHOLDS[k], ENHANCED_THRESHOLDS[k + 1]
        if fraction < hi:
            share = (fraction - lo) / (hi - lo)
            return ENHANCED_INITIAL[k] + share * (ENHANCED_FINAL[k] - ENHANCED_INITIAL[k])
    raise AssertionError("unreachable")


def simulation(multiple: float, age: int = 60, reform=None) -> Simulation:
    """A single adult in Travis County, Texas, earning `multiple` times the
    poverty line the credit uses (the prior year's)."""
    situation = build_household_situation(age, None, [], "TX", county="Travis County", year=YEAR)
    fpg = Simulation(situation=situation).calculate("tax_unit_fpg", YEAR - 1)[0]
    situation["people"]["you"]["employment_income"] = {YEAR: float(multiple * fpg)}
    return Simulation(situation=situation, reform=reform)


def test_the_reform_builds():
    assert create_enhanced_ptc_reform() is not None


@pytest.mark.parametrize("multiple", [1.2, 1.75, 2.25, 2.75, 3.5, 4.5, 6.0])
def test_the_reform_applies_the_enhanced_schedule(multiple):
    sim = simulation(multiple, reform=create_enhanced_ptc_reform())
    fraction = float(sim.calculate("aca_magi_fraction", YEAR)[0])
    rate = float(sim.calculate("aca_required_contribution_percentage", YEAR)[0])
    assert rate == pytest.approx(enhanced_rate(fraction), abs=1e-6)


@pytest.mark.parametrize("multiple", [4.5, 6.0])
def test_the_reform_removes_the_400_percent_cliff(multiple):
    baseline = simulation(multiple)
    reformed = simulation(multiple, reform=create_enhanced_ptc_reform())
    assert not baseline.calculate("is_aca_ptc_eligible", YEAR).any()
    assert reformed.calculate("is_aca_ptc_eligible", YEAR).all()
    # A 60-year-old's benchmark premium is above 8.5% of income at these
    # incomes, so a credit remains, where current law gives none
    assert float(np.sum(baseline.calculate("aca_ptc", YEAR, map_to="household"))) == 0
    assert float(np.sum(reformed.calculate("aca_ptc", YEAR, map_to="household"))) > 0


def test_the_reform_raises_credits_below_400_percent():
    baseline = simulation(3.0)
    reformed = simulation(3.0, reform=create_enhanced_ptc_reform())
    assert float(np.sum(reformed.calculate("aca_ptc", YEAR, map_to="household"))) > float(
        np.sum(baseline.calculate("aca_ptc", YEAR, map_to="household"))
    )
