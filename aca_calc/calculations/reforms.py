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

# H.R. 1834 extends the enhanced schedule for 2026 through 2028; the January
# 2026 draft variants below use the same years.
ENHANCED_PERIOD = "2026-01-01.2028-12-31"


def _enhanced_schedule() -> dict:
    """The enhanced schedule as policyengine-us parameter overrides.

    The three lists are replaced together: the threshold list has one more
    entry than the rate lists, and current law's lists have a 133% FPL
    threshold the enhanced schedule doesn't.
    """
    return {
        "gov.aca.required_contribution_percentage.threshold": {ENHANCED_PERIOD: ENHANCED_THRESHOLDS},
        "gov.aca.required_contribution_percentage.initial": {ENHANCED_PERIOD: ENHANCED_INITIAL},
        "gov.aca.required_contribution_percentage.final": {ENHANCED_PERIOD: ENHANCED_FINAL},
    }


# gov.aca.ptc_income_eligibility's third bracket starts at 400% FPL; from 2026
# it makes incomes there ineligible.
NO_INCOME_CAP = {"gov.aca.ptc_income_eligibility[2].amount": {ENHANCED_PERIOD: True}}


def create_enhanced_ptc_reform():
    """H.R. 1834: extend the enhanced premium tax credits for 2026-2028.

    Restores the ARPA/IRA applicable-percentage schedule and removes the 400%
    FPL eligibility limit, so households above 400% FPL pay at most 8.5% of
    income for the benchmark plan. H.R. 1834 passed the House on January 8,
    2026; it has not been enacted.

    Returns:
        Reform: PolicyEngine reform object
    """
    return Reform.from_dict({**_enhanced_schedule(), **NO_INCOME_CAP}, country_id="us")


def create_700fpl_cap_reform():
    """The enhanced schedule with eligibility ending at 700% FPL.

    A January 2026 draft of the CARE Act, which was never introduced, paired
    the enhanced schedule with a 700% FPL income cap. Between 400% and 700%
    FPL households pay 8.5% of income; above 700% there is no credit.

    Returns:
        Reform: PolicyEngine reform object
    """
    return Reform.from_dict(
        {
            **_enhanced_schedule(),
            # Move the ineligible bracket's start from 400% to 700% FPL.
            "gov.aca.ptc_income_eligibility[2].threshold": {ENHANCED_PERIOD: 7},
        },
        country_id="us",
    )


MINIMUM_PREMIUM_MODULE = "aca_ptc_minimum_premium"


def minimum_premium_available() -> bool:
    """Whether the installed policyengine-us has the minimum premium reform
    (gov.contrib.aca.minimum_premium, policyengine-us #10681)."""
    try:
        _contrib_reform(MINIMUM_PREMIUM_MODULE, MINIMUM_PREMIUM_MODULE)
    except ImportError:
        return False
    return True


def create_minimum_premium_reform():
    """The enhanced schedule with a $5 monthly minimum premium.

    The January 2026 CARE Act draft required every tax unit to pay at least $5
    a month toward its premiums: the credit can't cover the last $5 a month.
    policyengine-us models it as the contributed reform
    gov.contrib.aca.minimum_premium, $5 by default.

    Returns:
        Reform: PolicyEngine reform object

    Raises:
        ImportError: if the installed policyengine-us has no such reform.
    """
    _contrib_reform(MINIMUM_PREMIUM_MODULE, MINIMUM_PREMIUM_MODULE)
    return Reform.from_dict(
        {
            **_enhanced_schedule(),
            **NO_INCOME_CAP,
            "gov.contrib.aca.minimum_premium.in_effect": {ENHANCED_PERIOD: True},
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

    Introduced by Reps. Dunn (R-FL) and Schneider (D-IL) on December 9, 2025;
    not enacted.

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
