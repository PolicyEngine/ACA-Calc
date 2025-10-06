"""Chart creation functions for ACA calculator."""

import numpy as np
import plotly.graph_objects as go
from policyengine_us import Simulation

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_enhanced_ptc_reform


# PolicyEngine brand colors
COLORS = {
    "primary": "#2C6496",
    "secondary": "#39C6C0",
    "green": "#28A745",
    "gray": "#BDBDBD",
    "blue_gradient": ["#D1E5F0", "#92C5DE", "#2166AC", "#053061"],
}


def add_logo_to_layout():
    """Add PolicyEngine logo to chart layout."""
    import base64

    try:
        with open("blue.png", "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
            return {
                "images": [
                    {
                        "source": f"data:image/png;base64,{logo_base64}",
                        "xref": "paper",
                        "yref": "paper",
                        "x": 1.01,
                        "y": -0.18,
                        "sizex": 0.10,
                        "sizey": 0.10,
                        "xanchor": "right",
                        "yanchor": "bottom",
                    }
                ]
            }
    except:
        return {}


def create_ptc_charts(
    age_head,
    age_spouse,
    dependent_ages,
    state,
    county=None,
    zip_code=None,
    income=None,
):
    """Create PTC comparison and difference charts.

    Args:
        age_head: Age of head of household
        age_spouse: Age of spouse (None if not married)
        dependent_ages: List/tuple of dependent ages
        state: Two-letter state code
        county: County name
        zip_code: 5-digit ZIP code
        income: Optional income to mark on chart

    Returns:
        tuple: (comparison_fig, delta_fig, benefit_info, income_range,
                ptc_baseline_range, ptc_reform_range, slcsp, fpl, x_axis_max)
    """
    # Convert tuple to list for household builder
    dependent_ages = list(dependent_ages) if dependent_ages else []

    # Build household with axes
    base_household = build_household_situation(
        age_head=age_head,
        age_spouse=age_spouse,
        dependent_ages=dependent_ages,
        state=state,
        county=county,
        zip_code=zip_code,
        year=2026,
        with_axes=True,
    )

    try:
        reform = create_enhanced_ptc_reform()

        # Run simulations
        sim_baseline = Simulation(situation=base_household)
        sim_reform = Simulation(situation=base_household, reform=reform)

        income_range = sim_baseline.calculate(
            "employment_income", map_to="household", period=2026
        )
        ptc_range_baseline = sim_baseline.calculate(
            "aca_ptc", map_to="household", period=2026
        )
        ptc_range_reform = sim_reform.calculate(
            "aca_ptc", map_to="household", period=2026
        )

        # Calculate Medicaid and CHIP
        medicaid_range = sim_baseline.calculate(
            "medicaid_cost", map_to="household", period=2026
        )
        chip_range = sim_baseline.calculate(
            "per_capita_chip", map_to="household", period=2026
        )

        # Find x-axis range
        max_income_with_ptc = 200000
        for i in range(len(ptc_range_reform) - 1, -1, -1):
            if ptc_range_reform[i] > 0:
                max_income_with_ptc = income_range[i]
                break
        x_axis_max = min(1000000, max_income_with_ptc * 1.1)

        delta_range = ptc_range_reform - ptc_range_baseline

        # TODO: Implement full chart creation
        # For now, return None to keep refactoring incremental
        return None, None, None, income_range, ptc_range_baseline, ptc_range_reform, 0, 0, x_axis_max

    except Exception as e:
        raise Exception(f"Chart creation error: {str(e)}") from e
