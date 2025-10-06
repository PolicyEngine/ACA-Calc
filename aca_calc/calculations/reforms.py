"""PolicyEngine reform definitions for ACA scenarios."""

from policyengine_core.reforms import Reform


def create_enhanced_ptc_reform():
    """Create reform extending enhanced PTCs through 2026.

    Returns:
        Reform: PolicyEngine reform object
    """
    return Reform.from_dict(
        {
            "gov.aca.ptc_phase_out_rate[0].amount": {
                "2026-01-01.2100-12-31": 0
            },
            "gov.aca.ptc_phase_out_rate[1].amount": {
                "2025-01-01.2100-12-31": 0
            },
            "gov.aca.ptc_phase_out_rate[2].amount": {
                "2026-01-01.2100-12-31": 0
            },
            "gov.aca.ptc_phase_out_rate[3].amount": {
                "2026-01-01.2100-12-31": 0.02
            },
            "gov.aca.ptc_phase_out_rate[4].amount": {
                "2026-01-01.2100-12-31": 0.04
            },
            "gov.aca.ptc_phase_out_rate[5].amount": {
                "2026-01-01.2100-12-31": 0.06
            },
            "gov.aca.ptc_phase_out_rate[6].amount": {
                "2026-01-01.2100-12-31": 0.085
            },
            "gov.aca.ptc_income_eligibility[2].amount": {
                "2026-01-01.2100-12-31": True
            },
        },
        country_id="us",
    )
