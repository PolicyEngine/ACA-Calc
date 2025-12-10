"""
ACA Premium Tax Credit Calculator Page
======================================
Full calculator for exploring ACA premium tax credits.
"""

import streamlit as st
import sys
import os

# Add parent directory to path to import from aca_calc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pandas as pd
    import numpy as np
    import json
    import gc
    from policyengine_us import Simulation
    import plotly.graph_objects as go
    import base64

    # Import calculation functions from package
    from aca_calc.calculations.ptc import calculate_ptc
    from aca_calc.calculations.household import build_household_situation
    from aca_calc.calculations.reforms import create_enhanced_ptc_reform, create_700fpl_reform

    # Try to import reform capability
    try:
        from policyengine_core.reforms import Reform
        REFORM_AVAILABLE = True
    except ImportError:
        REFORM_AVAILABLE = False

    st.set_page_config(
        page_title="ACA Calculator",
        page_icon="🧮",
        layout="wide",
        initial_sidebar_state="expanded",
    )

except Exception as e:
    st.error(f"Startup Error: {str(e)}")
    st.error("Please report this error with the details above.")
    import traceback
    st.code(traceback.format_exc())
    st.stop()


# PolicyEngine brand colors (app-v2 style)
COLORS = {
    "primary": "#319795",  # Teal
    "secondary": "#2C6496",  # Blue for IRA reform
    "purple": "#9467BD",  # Purple for 700% FPL
    "gray": "#9CA3AF",  # Gray for baseline
    "green": "#22C55E",
}


def get_logo_base64():
    """Get base64 encoded PolicyEngine logo"""
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blue.png")
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


def add_logo_to_layout():
    """Add PolicyEngine logo to chart layout"""
    logo_base64 = get_logo_base64()
    if logo_base64:
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
    return {}


# Load counties
@st.cache_data
def load_counties():
    try:
        counties_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "counties.json")
        with open(counties_path, "r") as f:
            return json.load(f)
    except:
        return None


def main():
    # Header styling
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto:wght@400;500&display=swap');
        .stApp {{
            font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
        }}
        h1 {{
            color: {COLORS["primary"]};
            font-weight: 600;
            font-family: 'Inter', sans-serif;
        }}
        .subtitle {{
            color: #5A5A5A;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }}
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.title("🧮 ACA Premium Tax Credit Calculator")
    st.markdown("Explore how extending enhanced premium tax credits would affect your household.")

    # Link back to interactive story
    st.markdown("← [Back to Interactive Guide](/)")

    counties = load_counties()

    # Sidebar for household configuration
    with st.sidebar:
        st.header("Reform scenarios")
        st.markdown("Select which reform(s) to compare against baseline:")

        show_ira = st.checkbox(
            "IRA Extension",
            value=True,
            help="Extends current enhanced subsidies indefinitely with 8.5% cap and no income limit above 400% FPL"
        )

        show_700fpl = st.checkbox(
            "700% FPL Extension (Bipartisan Bill)",
            value=False,
            help="Bipartisan Health Insurance Affordability Act: extends eligibility to 700% FPL with 9.25% cap"
        )

        if not show_ira and not show_700fpl:
            st.warning("Please select at least one reform to compare.")

        st.markdown("---")

        st.header("Household configuration")

        married = st.checkbox("Are you married?", value=False)

        age_head = st.number_input(
            "How old are you?", min_value=18, max_value=100, value=35
        )

        if married:
            age_spouse = st.number_input(
                "How old is your spouse?",
                min_value=18,
                max_value=100,
                value=35,
            )
        else:
            age_spouse = None

        num_dependents = st.number_input(
            "How many children or dependents do you have?",
            min_value=0,
            max_value=10,
            value=0,
        )
        dependent_ages = []

        if num_dependents > 0:
            st.write("What are their ages?")
            for i in range(num_dependents):
                age_dep = st.number_input(
                    f"Child {i+1} age",
                    min_value=0,
                    max_value=25,
                    value=10,
                    key=f"dep_{i}",
                )
                dependent_ages.append(age_dep)

        states = [
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
        ]

        state = st.selectbox("Which state do you live in?", states, index=0)

        # County selection
        county = None
        if counties and state in counties:
            sorted_counties = sorted(counties[state])
            county = st.selectbox(
                "Which county?",
                sorted_counties,
                index=0,
                help="County used for marketplace calculations",
            )

        # ZIP code for LA County
        zip_code = None
        if state == "CA" and county == "Los Angeles County":
            zip_code = st.text_input(
                "What is your ZIP code?",
                max_chars=5,
                help="Los Angeles County has multiple rating areas.",
                placeholder="90001",
            )
            if zip_code and (len(zip_code) != 5 or not zip_code.isdigit()):
                st.error("Please enter a valid 5-digit ZIP code")
                zip_code = None

        st.markdown("---")

        calculate_button = st.button(
            "Analyze premium subsidies",
            type="primary",
            use_container_width=True,
        )

        if calculate_button:
            st.session_state.calculate = True
            new_params = {
                "age_head": age_head,
                "age_spouse": age_spouse,
                "dependent_ages": dependent_ages,
                "state": state,
                "county": county,
                "married": married,
                "zip_code": zip_code,
                "show_ira": show_ira,
                "show_700fpl": show_700fpl,
            }
            # Clear cached charts if params changed
            if hasattr(st.session_state, "params") and st.session_state.params != new_params:
                st.session_state.income_range = None
                st.session_state.fig_net_income = None
                st.session_state.fig_mtr = None
            st.session_state.params = new_params

    # Main content area
    if not hasattr(st.session_state, "calculate") or not st.session_state.calculate:
        st.markdown(
            """
            ### Get started

            Enter your household information in the sidebar, then click **"Analyze premium subsidies"** to see:

            - How premium tax credits vary across income levels for your household
            - The income range where extending enhanced subsidies would benefit you
            - Your specific impact at any income level you choose

            **Available reform scenarios:**
            - **IRA Extension**: Continues current enhanced subsidies with 8.5% cap and no income limit
            - **700% FPL Extension**: [Bipartisan Health Insurance Affordability Act](https://punchbowl.news/wp-content/uploads/Bipartisan-Health-Insurance-Affordability-Act-Section-by-Section-copy.pdf) extending eligibility to 700% FPL with 9.25% cap

            Select one or both reforms in the sidebar to compare against baseline (current law after IRA expiration).
            """
        )
    else:
        params = st.session_state.params

        # Generate charts
        if not hasattr(st.session_state, "income_range") or st.session_state.income_range is None:
            with st.spinner("Generating analysis..."):
                county_name = params["county"] if params["county"] else None
                zip_code = params.get("zip_code")

                (
                    fig_comparison,
                    fig_delta,
                    benefit_info,
                    income_range,
                    ptc_baseline_range,
                    ptc_reform_range,
                    ptc_700fpl_range,
                    slcsp_2026,
                    fpl,
                    x_axis_max,
                ) = create_chart(
                    params["age_head"],
                    params["age_spouse"],
                    tuple(params["dependent_ages"]),
                    params["state"],
                    county_name,
                    zip_code,
                    show_ira=params.get("show_ira", True),
                    show_700fpl=params.get("show_700fpl", False),
                )

                if income_range is not None:
                    st.session_state.income_range = income_range
                    st.session_state.ptc_baseline_range = ptc_baseline_range
                    st.session_state.ptc_reform_range = ptc_reform_range
                    st.session_state.ptc_700fpl_range = ptc_700fpl_range
                    st.session_state.slcsp_2026 = slcsp_2026
                    st.session_state.fpl = fpl
                    st.session_state.benefit_info = benefit_info
                    st.session_state.fig_comparison = fig_comparison
                    st.session_state.fig_delta = fig_delta
                    st.session_state.x_axis_max = x_axis_max

        # Show tabs
        if hasattr(st.session_state, "fig_delta") and st.session_state.fig_delta is not None:
            tab1, tab2, tab3 = st.tabs([
                "Gain from extension",
                "Baseline vs. extension",
                "Your impact"
            ])

            with tab1:
                st.plotly_chart(
                    st.session_state.fig_delta,
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="gain_chart",
                )

            with tab2:
                st.plotly_chart(
                    st.session_state.fig_comparison,
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="comparison_chart",
                )

            with tab3:
                st.markdown("Enter your annual household income to see your specific impact.")

                user_income = st.number_input(
                    "Annual household income:",
                    min_value=0,
                    value=0,
                    step=1000,
                    help="Modified Adjusted Gross Income (MAGI)",
                    format="%d",
                )

                if (
                    hasattr(st.session_state, "income_range")
                    and user_income is not None
                    and user_income > 0
                ):
                    ptc_2026_baseline = np.interp(
                        user_income,
                        st.session_state.income_range,
                        st.session_state.ptc_baseline_range,
                    )
                    ptc_2026_with_ira = np.interp(
                        user_income,
                        st.session_state.income_range,
                        st.session_state.ptc_reform_range,
                    )
                    difference = ptc_2026_with_ira - ptc_2026_baseline
                    fpl = st.session_state.fpl

                    # Calculate FPL percentage
                    household_size = (
                        1
                        + (1 if params["age_spouse"] else 0)
                        + len(params["dependent_ages"])
                    )
                    fpl_pct = (user_income / fpl * 100) if fpl > 0 else 0

                    col_baseline, col_with_ira, col_diff = st.columns(3)

                    with col_baseline:
                        st.metric(
                            "Current law",
                            f"${ptc_2026_baseline:,.0f}/year",
                        )

                    with col_with_ira:
                        st.metric(
                            "With reform",
                            f"${ptc_2026_with_ira:,.0f}/year",
                        )

                    with col_diff:
                        if difference > 0:
                            st.metric(
                                "You gain",
                                f"${difference:,.0f}/year",
                                f"+${difference/12:,.0f}/month",
                            )
                        else:
                            st.metric("No change", "$0")


def create_chart(
    age_head,
    age_spouse,
    dependent_ages,
    state,
    county=None,
    zip_code=None,
    income=None,
    show_ira=True,
    show_700fpl=False,
):
    """Create income curve charts showing PTC across income range"""

    base_household = build_household_situation(
        age_head=age_head,
        age_spouse=age_spouse,
        dependent_ages=list(dependent_ages) if dependent_ages else [],
        state=state,
        county=county,
        zip_code=zip_code,
        year=2026,
        with_axes=True,
    )

    PURPLE = "#9467BD"

    try:
        reform_ira = create_enhanced_ptc_reform()
        reform_700fpl = create_700fpl_reform()

        sim_baseline = Simulation(situation=base_household)

        income_range = sim_baseline.calculate(
            "employment_income", map_to="household", period=2026
        )
        ptc_range_baseline = sim_baseline.calculate(
            "aca_ptc", map_to="household", period=2026
        )

        ptc_range_reform = None
        if show_ira:
            sim_ira = Simulation(situation=base_household, reform=reform_ira)
            ptc_range_reform = sim_ira.calculate(
                "aca_ptc", map_to="household", period=2026
            )

        ptc_range_700fpl = None
        if show_700fpl and reform_700fpl is not None:
            sim_700fpl = Simulation(situation=base_household, reform=reform_700fpl)
            ptc_range_700fpl = sim_700fpl.calculate(
                "aca_ptc", map_to="household", period=2026
            )

        # Find x-axis range
        max_income_with_ptc = 200000
        ptc_arrays_to_check = [ptc_range_baseline]
        if ptc_range_reform is not None:
            ptc_arrays_to_check.append(ptc_range_reform)
        if ptc_range_700fpl is not None:
            ptc_arrays_to_check.append(ptc_range_700fpl)

        for ptc_arr in ptc_arrays_to_check:
            for i in range(len(ptc_arr) - 1, -1, -1):
                if ptc_arr[i] > 0:
                    max_income_with_ptc = max(max_income_with_ptc, income_range[i])
                    break

        x_axis_max = min(1000000, max_income_with_ptc * 1.1)

        # Delta
        if ptc_range_reform is not None:
            delta_range = ptc_range_reform - ptc_range_baseline
        elif ptc_range_700fpl is not None:
            delta_range = ptc_range_700fpl - ptc_range_baseline
        else:
            delta_range = np.zeros_like(ptc_range_baseline)

        # Create comparison chart
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=income_range,
                y=ptc_range_baseline,
                mode="lines",
                name="PTC (baseline)",
                line=dict(color=COLORS["gray"], width=3),
            )
        )

        if show_ira and ptc_range_reform is not None:
            fig.add_trace(
                go.Scatter(
                    x=income_range,
                    y=ptc_range_reform,
                    mode="lines",
                    name="PTC (IRA extension)",
                    line=dict(color=COLORS["secondary"], width=3),
                )
            )

        if show_700fpl and ptc_range_700fpl is not None:
            fig.add_trace(
                go.Scatter(
                    x=income_range,
                    y=ptc_range_700fpl,
                    mode="lines",
                    name="PTC (700% FPL extension)",
                    line=dict(color=PURPLE, width=3),
                )
            )

        fig.update_layout(
            title={
                "text": "Premium Tax Credits by Household Income (2026)",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Annual premium tax credit",
            height=400,
            xaxis=dict(tickformat="$,.0f", range=[0, x_axis_max]),
            yaxis=dict(tickformat="$,.0f", rangemode="tozero"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Roboto, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=0.98, xanchor="right", x=1),
            margin=dict(l=80, r=40, t=60, b=80),
            **add_logo_to_layout(),
        )

        # Create delta chart
        fig_delta = go.Figure()

        if show_ira and ptc_range_reform is not None:
            delta_ira = ptc_range_reform - ptc_range_baseline
            fig_delta.add_trace(
                go.Scatter(
                    x=income_range,
                    y=delta_ira,
                    mode="lines",
                    name="IRA extension gain",
                    line=dict(color=COLORS["secondary"], width=3),
                    fill="tozeroy",
                    fillcolor="rgba(44, 100, 150, 0.2)",
                )
            )

        if show_700fpl and ptc_range_700fpl is not None:
            delta_700 = ptc_range_700fpl - ptc_range_baseline
            fig_delta.add_trace(
                go.Scatter(
                    x=income_range,
                    y=delta_700,
                    mode="lines",
                    name="700% FPL extension gain",
                    line=dict(color=PURPLE, width=3),
                    fill="tozeroy" if not show_ira else None,
                    fillcolor="rgba(148, 103, 189, 0.2)" if not show_ira else None,
                )
            )

        fig_delta.update_layout(
            title={
                "text": "PTC Gain from Extending Enhanced Subsidies (2026)",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Annual PTC gain",
            height=400,
            xaxis=dict(tickformat="$,.0f", range=[0, x_axis_max]),
            yaxis=dict(tickformat="$,.0f", rangemode="tozero"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Roboto, sans-serif"),
            showlegend=True,
            margin=dict(l=80, r=40, t=60, b=80),
            **add_logo_to_layout(),
        )

        # Calculate benefit info
        benefit_indices = np.where(delta_range > 0)[0]
        if len(benefit_indices) > 0:
            benefit_info = {
                "min_income": float(income_range[benefit_indices[0]]),
                "max_income": float(income_range[benefit_indices[-1]]),
                "max_benefit": float(np.max(delta_range[benefit_indices])),
            }
        else:
            benefit_info = None

        # Get SLCSP and FPL
        slcsp_array = sim_baseline.calculate("slcsp", map_to="household", period=2026)
        fpl_array = sim_baseline.calculate("tax_unit_fpg", period=2026)
        slcsp = float(np.max(slcsp_array))
        fpl = float(fpl_array[len(fpl_array) // 2])

        return (
            fig,
            fig_delta,
            benefit_info,
            income_range,
            ptc_range_baseline,
            ptc_range_reform if ptc_range_reform is not None else np.zeros_like(ptc_range_baseline),
            ptc_range_700fpl,
            slcsp,
            fpl,
            x_axis_max,
        )

    except Exception as e:
        st.error(f"Error generating charts: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, None, None, None, None, None, None, 0, 0, 200000


if __name__ == "__main__":
    main()
