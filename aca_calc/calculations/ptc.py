"""Premium Tax Credit calculation functions."""

import copy
from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_enhanced_ptc_reform


def calculate_ptc(
    age_head,
    age_spouse,
    income,
    dependent_ages,
    state,
    county_name=None,
    zip_code=None,
    use_reform=False,
):
    """Calculate PTC for baseline or IRA enhanced scenario using 2026 comparison.

    Args:
        age_head: Age of head of household
        age_spouse: Age of spouse (None if not married)
        income: Annual household income
        dependent_ages: List of dependent ages
        state: Two-letter state code
        county_name: County name (e.g., "Travis County")
        zip_code: 5-digit ZIP code (required for LA County)
        use_reform: If True, use enhanced PTC reform

    Returns:
        tuple: (ptc, slcsp, fpl, fpl_pct)
    """
    try:
        # Build base household situation
        situation = build_household_situation(
            age_head=age_head,
            age_spouse=age_spouse,
            dependent_ages=dependent_ages,
            state=state,
            county=county_name,
            zip_code=zip_code,
            year=2026,
            with_axes=False,
        )

        # Deep copy and inject income
        sit = copy.deepcopy(situation)

        # Split income between adults if married
        if age_spouse:
            sit["people"]["you"]["employment_income"] = {2026: income / 2}
            sit["people"]["your partner"]["employment_income"] = {
                2026: income / 2
            }
        else:
            sit["people"]["you"]["employment_income"] = {2026: income}

        # Create reform if requested
        reform = create_enhanced_ptc_reform() if use_reform else None

        # Run simulation
        sim = Simulation(situation=sit, reform=reform)

        ptc = sim.calculate("aca_ptc", map_to="household", period=2026)[0]
        slcsp = sim.calculate("slcsp", map_to="household", period=2026)[0]
        fpl = sim.calculate("tax_unit_fpg", period=2026)[0]
        aca_magi_fraction = sim.calculate("aca_magi_fraction", period=2026)[0]
        fpl_pct = aca_magi_fraction * 100

        return float(max(0, ptc)), float(slcsp), float(fpl), float(fpl_pct)

    except Exception as e:
        raise Exception(f"PTC calculation error: {str(e)}") from e
