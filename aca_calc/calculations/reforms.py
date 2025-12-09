"""PolicyEngine reform definitions for ACA scenarios."""

from policyengine_core.reforms import Reform


def create_enhanced_ptc_reform():
    """Create reform extending enhanced PTCs (IRA extension) through 2026.

    This extends the current IRA-enhanced subsidies indefinitely with:
    - 8.5% cap at 400%+ FPL
    - No income eligibility limit above 400% FPL

    Returns:
        Reform: PolicyEngine reform object
    """
    return Reform.from_dict(
        {
            "gov.aca.required_contribution_percentage[0].amount": {
                "2026-01-01.2100-12-31": 0
            },
            "gov.aca.required_contribution_percentage[1].amount": {
                "2026-01-01.2100-12-31": 0
            },
            "gov.aca.required_contribution_percentage[2].amount": {
                "2026-01-01.2100-12-31": 0
            },
            "gov.aca.required_contribution_percentage[3].amount": {
                "2026-01-01.2100-12-31": 0.02
            },
            "gov.aca.required_contribution_percentage[4].amount": {
                "2026-01-01.2100-12-31": 0.04
            },
            "gov.aca.required_contribution_percentage[5].amount": {
                "2026-01-01.2100-12-31": 0.06
            },
            "gov.aca.required_contribution_percentage[6].amount": {
                "2026-01-01.2100-12-31": 0.085
            },
            "gov.aca.ptc_income_eligibility[2].amount": {
                "2026-01-01.2100-12-31": True
            },
        },
        country_id="us",
    )


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
    # Import the structural reform from policyengine-us
    try:
        from policyengine_us.reforms.aca.aca_ptc_700_fpl_cliff import aca_ptc_700_fpl_cliff
        return aca_ptc_700_fpl_cliff
    except ImportError:
        # Fallback if the reform isn't available in the installed version
        return None
