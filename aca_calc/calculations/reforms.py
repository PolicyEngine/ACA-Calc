"""PolicyEngine reform definitions for ACA scenarios."""

from policyengine_core.reforms import Reform

# The enhanced applicable-percentage schedule of the American Rescue Plan Act
# (26 U.S.C. 36B(b)(3)(A)(iii), in effect for 2021-2025 after the Inflation
# Reduction Act's extension): 0% of income up to 150% of the poverty line,
# rising linearly to 2% at 200%, 4% at 250%, 6% at 300% and 8.5% at 400%.
# policyengine-us stores the schedule as three lists
# (gov.aca.required_contribution_percentage.threshold, .initial and .final, in
# FPL multiples and fractions of income); its formula holds the last bracket's
# final rate, 8.5%, for every income above 400%. These are its own 2021 values.
ENHANCED_THRESHOLDS = [0, 1.5, 2.0, 2.5, 3.0, 4.0]
ENHANCED_INITIAL = [0, 0, 0.02, 0.04, 0.06]
ENHANCED_FINAL = [0, 0.02, 0.04, 0.06, 0.085]

ENHANCED_PERIOD = "2026-01-01.2100-12-31"


def create_enhanced_ptc_reform():
    """Create reform extending enhanced PTCs (IRA extension) from 2026 on.

    Restores the ARPA/IRA applicable-percentage schedule and removes the 400%
    FPL eligibility limit, so households above 400% FPL pay at most 8.5% of
    income for the benchmark plan.

    The three schedule lists are replaced together: the threshold list has one
    more entry than the rate lists, and the 2026 law's lists have a 133% FPL
    threshold the enhanced schedule doesn't.

    Returns:
        Reform: PolicyEngine reform object
    """
    return Reform.from_dict(
        {
            "gov.aca.required_contribution_percentage.threshold": {ENHANCED_PERIOD: ENHANCED_THRESHOLDS},
            "gov.aca.required_contribution_percentage.initial": {ENHANCED_PERIOD: ENHANCED_INITIAL},
            "gov.aca.required_contribution_percentage.final": {ENHANCED_PERIOD: ENHANCED_FINAL},
            "gov.aca.ptc_income_eligibility[2].amount": {ENHANCED_PERIOD: True},
        },
        country_id="us",
    )


def _contrib_reform(module: str, name: str):
    """A structural ACA reform from policyengine-us, or an error saying which
    is missing: a missing reform must not show as zero credits."""
    try:
        reforms = __import__(f"policyengine_us.reforms.aca.{module}", fromlist=[name])
        return getattr(reforms, name)
    except (ImportError, AttributeError) as e:
        raise ImportError(
            f"policyengine-us has no {name} reform (policyengine_us.reforms.aca.{module}): {e}"
        ) from e


def create_700fpl_reform():
    """Create 700% FPL extension reform (Bipartisan Health Insurance Affordability Act).

    This implements the proposed bill's schedule:
    - 200-250% FPL: 2% to 4%
    - 250-300% FPL: 4% to 6%
    - 300-400% FPL: 6% to 8.5%
    - 400-600% FPL: 8.5% to 8.5%
    - 600-700% FPL: 8.5% to 9.25%
    - Eligibility cuts off at 700% FPL

    Returns:
        Reform: PolicyEngine reform object
    """
    return _contrib_reform("aca_ptc_700_fpl_cliff", "aca_ptc_700_fpl_cliff")


def create_additional_bracket_reform():
    """Create linear bracket extension reform for ACA PTC.

    This reform extends premium subsidies beyond the standard 400% FPL cliff
    using a linear formula. Above the transition threshold (typically 300% FPL),
    the contribution percentage increases linearly based on the increment rate
    (typically 4 percentage points per 100% FPL).

    The reform creates a more gradual phase-out of subsidies, reducing the
    cliff effect where households just above 400% FPL lose all subsidies.

    Returns:
        Reform: PolicyEngine reform object
    """
    return _contrib_reform("aca_ptc_additional_bracket", "aca_ptc_additional_bracket")


def create_simplified_bracket_reform():
    """Create simplified linear phase-out reform for ACA PTC.

    This reform creates a single linear phase-out starting at 100% FPL,
    where the contribution percentage increases by 4 percentage points
    per 100% FPL increment. This results in a simpler, more aggressive
    phase-out compared to the additional bracket reform.

    The reform eliminates the standard ACA bracket structure entirely,
    replacing it with one continuous linear progression from 100% FPL
    onwards.

    Returns:
        Reform: PolicyEngine reform object
    """
    return _contrib_reform("aca_ptc_simplified_bracket", "aca_ptc_simplified_bracket")
