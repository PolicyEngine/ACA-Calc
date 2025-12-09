"""
ACA Premium Tax Credit Calculator
==================================
Explore how extending enhanced premium tax credits would affect your household.

This app calculates ACA premium tax credits under two scenarios:
1. Current law: Enhanced PTCs expire after 2025
2. Extended: Enhanced PTCs extended to 2026

Uses PolicyEngine US for accurate tax-benefit microsimulation.
"""

import streamlit as st

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
        page_title="Enhanced ACA Subsidies Calculator",
        layout="wide",
        initial_sidebar_state="expanded",
    )

except Exception as e:
    st.error(f"Startup Error: {str(e)}")
    st.error("Please report this error with the details above.")
    import traceback

    st.code(traceback.format_exc())
    st.stop()


# Load PolicyEngine logo
def get_logo_base64():
    """Load PolicyEngine logo and convert to base64"""
    try:
        with open("blue.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


# Load counties from PolicyEngine data
@st.cache_data
def load_counties():
    try:
        with open("counties.json", "r") as f:
            return json.load(f)
    except:
        return None


# PolicyEngine brand colors
COLORS = {
    "primary": "#2C6496",  # Blue for extension/reform
    "secondary": "#39C6C0",
    "green": "#28A745",
    "gray": "#BDBDBD",  # Medium light gray for baseline (matches policyengine-app)
    "blue_gradient": ["#D1E5F0", "#92C5DE", "#2166AC", "#053061"],
}


def get_logo_base64():
    """Get base64 encoded PolicyEngine logo"""
    try:
        with open("blue.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


def add_logo_to_layout():
    """Add PolicyEngine logo to chart layout (matches policyengine-app positioning)"""
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


def main():
    # Header with PolicyEngine branding
    st.markdown(
        f"""
        <style>
        .stApp {{
            font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
        }}
        h1 {{
            color: {COLORS["primary"]};
            font-weight: 600;
        }}
        .subtitle {{
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }}
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.title("How would extending enhanced subsidies affect you?")

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
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DE",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
            "DC",
        ]

        state = st.selectbox(
            "Which state do you live in?", states, index=0
        )  # Default to AL

        # County selection - auto-select first alphabetically
        county = None
        if counties and state in counties:
            sorted_counties = sorted(counties[state])
            county = st.selectbox(
                "Which county?",
                sorted_counties,
                index=0,
                help="County used for marketplace calculations",
            )

        # ZIP code input - required for LA County
        zip_code = None
        if state == "CA" and county == "Los Angeles County":
            zip_code = st.text_input(
                "What is your ZIP code?",
                max_chars=5,
                help="Los Angeles County has multiple rating areas. ZIP code is required for accurate premium calculations.",
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
        # Show instructional text when first loading
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

        # Generate charts only if not already in session state (avoid recalculation)
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

                # Store arrays and charts in session state for later use
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

        # Show tabs using cached charts
        if hasattr(st.session_state, "fig_delta") and st.session_state.fig_delta is not None:
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "Gain from extension",
                "Baseline vs. extension",
                "Net income",
                "Marginal tax rates",
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
                # Auto-generate net income chart if not cached
                if not hasattr(st.session_state, "fig_net_income") or st.session_state.fig_net_income is None:
                    with st.spinner("Calculating net income (this may take a few seconds)..."):
                        x_axis_max = st.session_state.get("x_axis_max", 200000)
                        (
                            fig_net_income,
                            fig_mtr,
                            net_income_range,
                            net_income_baseline,
                            net_income_reform,
                        ) = create_net_income_and_mtr_charts(
                            params["age_head"],
                            params["age_spouse"],
                            tuple(params["dependent_ages"]),
                            params["state"],
                            params.get("county"),
                            params.get("zip_code"),
                            x_axis_max,
                            show_ira=params.get("show_ira", True),
                            show_700fpl=params.get("show_700fpl", False),
                        )

                        # Store in session state
                        if fig_net_income is not None:
                            st.session_state.fig_net_income = fig_net_income
                            st.session_state.fig_mtr = fig_mtr

                # Display cached chart
                if hasattr(st.session_state, "fig_net_income") and st.session_state.fig_net_income is not None:
                    st.plotly_chart(
                        st.session_state.fig_net_income,
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key="net_income_chart",
                    )

            with tab4:
                # Check if chart needs to be generated
                if not hasattr(st.session_state, "fig_mtr") or st.session_state.fig_mtr is None:
                    with st.spinner("Calculating marginal tax rates (this may take a few seconds)..."):
                        x_axis_max = st.session_state.get("x_axis_max", 200000)
                        (
                            fig_net_income,
                            fig_mtr,
                            net_income_range,
                            net_income_baseline,
                            net_income_reform,
                        ) = create_net_income_and_mtr_charts(
                            params["age_head"],
                            params["age_spouse"],
                            tuple(params["dependent_ages"]),
                            params["state"],
                            params.get("county"),
                            params.get("zip_code"),
                            x_axis_max,
                            show_ira=params.get("show_ira", True),
                            show_700fpl=params.get("show_700fpl", False),
                        )

                        # Store in session state
                        if fig_mtr is not None:
                            st.session_state.fig_net_income = fig_net_income
                            st.session_state.fig_mtr = fig_mtr

                # Display chart
                if hasattr(st.session_state, "fig_mtr") and st.session_state.fig_mtr is not None:
                    st.plotly_chart(
                        st.session_state.fig_mtr,
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key="mtr_chart",
                    )

            with tab5:
                st.markdown("Enter your annual household income to see your specific impact.")

                user_income = st.number_input(
                    "Annual household income:",
                    min_value=0,
                    value=0,
                    step=1000,
                    help="Modified Adjusted Gross Income (MAGI) as defined in 26 USC § 36B(d)(2). Includes: wages, self-employment income, capital gains, interest, dividends, pensions, Social Security, unemployment, rental income, and other income sources. Also includes tax-exempt interest and tax-exempt Social Security.",
                    format="%d",
                )

                # Interpolate values at user's income (only if income > 0)
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
                    slcsp_2026 = st.session_state.slcsp_2026
                    fpl = st.session_state.fpl

                    # Calculate FPL percentage
                    household_size = (
                        1
                        + (1 if params["age_spouse"] else 0)
                        + len(params["dependent_ages"])
                    )
                    fpl_pct = (user_income / fpl * 100) if fpl > 0 else 0

                    # Display metrics with custom CSS to prevent truncation
                    st.markdown(
                        """
                    <style>
                    [data-testid="stMetricValue"] {
                        font-size: 1.4rem !important;
                        white-space: nowrap !important;
                        overflow: visible !important;
                        line-height: 1.3 !important;
                    }
                    [data-testid="stMetricLabel"] {
                        font-size: 0.95rem !important;
                        line-height: 1.2 !important;
                    }
                    </style>
                    """,
                        unsafe_allow_html=True,
                    )

                    col_baseline, col_with_ira, col_diff = st.columns(3)

                    with col_baseline:
                        st.metric(
                            "Current law",
                            f"${ptc_2026_baseline:,.0f} per year",
                            help="Your credits under current law (enhanced PTCs expire)",
                        )

                    with col_with_ira:
                        st.metric(
                            "Enhanced PTCs extended",
                            f"${ptc_2026_with_ira:,.0f} per year",
                            help="Your credits if enhanced subsidies were extended",
                        )

                    with col_diff:
                        if difference > 0:
                            st.metric(
                                "You gain",
                                f"${difference:,.0f} per year",
                                f"+${difference/12:,.0f} per month",
                                delta_color="normal",
                            )
                        else:
                            st.metric("No change", "$0")

                    # Details
                    with st.expander("See calculation details"):
                        st.write(
                            f"""
                        ### Your household
                        - **Size:** {household_size} people
                        - **Income:** ${user_income:,} ({fpl_pct:.0f}% of FPL)
                        - **2026 Federal Poverty Guideline:** ${fpl:,.0f}
                        - **Location:** {params['county'] + ', ' if params['county'] else ''}{params['state']}
                        - **Second Lowest Cost Silver Plan:** ${slcsp_2026:,.0f} per year (${slcsp_2026/12:,.0f} per month)

                        ### How premium tax credits work

                        **Formula:** PTC = Benchmark Plan Cost - Your Required Contribution

                        **Your Required Contribution** is a percentage of your income:
                        - Lower percentages with IRA extension (2026): 0-8.5% based on income
                        - Higher percentages without IRA (2026): 2-9.5% based on income
                        - No credits at all above 400% FPL without IRA extension

                        If the benchmark plan costs less than your required contribution, you get no credit.
                        """
                        )

            # Move "About this calculator" below the tabs
            with st.expander("About this calculator"):
                try:
                    from importlib.metadata import version
                    pe_version = version("policyengine-us")
                except Exception:
                    pe_version = "development"

                st.markdown(
                    f"""
                The Inflation Reduction Act enhanced ACA subsidies through 2025. This calculator shows how extending these enhancements to 2026 would affect your household's premium tax credits.

                This calculator uses [PolicyEngine's open-source tax-benefit microsimulation model](https://github.com/PolicyEngine/policyengine-us) (version {pe_version}).

                **2026 premium projections:** This calculator projects Second Lowest Cost Silver Plan (SLCSP) premiums for 2026 by applying a 4.19% increase to actual 2025 benchmark premiums from KFF, based on 2024-25 growth patterns. Actual premiums may rise faster, and we will update the calculator when CMS releases official data in October 2025.

                📖 [Learn more about enhanced premium tax credits](https://policyengine.org/us/research/enhanced-premium-tax-credits-extension)

                **Reform scenarios:**

                *IRA Extension:*
                - No income cap - households above 400% FPL can still receive credits
                - Lower premium contribution percentages (0-8.5% of income)
                - More generous subsidies at all income levels

                *700% FPL Extension ([Bipartisan Health Insurance Affordability Act](https://punchbowl.news/wp-content/uploads/Bipartisan-Health-Insurance-Affordability-Act-Section-by-Section-copy.pdf)):*
                - Eligibility extends to 700% FPL (vs no limit under IRA extension)
                - Contribution percentages: 2-9.25% of income
                - Different phase-out schedule than IRA extension

                **Current law (baseline - enhanced PTCs expire):**
                - Hard cap at 400% FPL - no credits above this level (the "subsidy cliff")
                - Higher contribution percentages (2.1-9.96% of income, per IRS Revenue Procedure 2025-25)
                - Less generous subsidies, especially for middle incomes

                **Key assumptions:**
                - Households have no employer-sponsored insurance (ESI), making them eligible for Medicaid, CHIP, and premium tax credits
                - Net income and MTR calculations assume standard deduction (set as input to avoid expensive itemization branching)

                **Technical note on MTR chart:** The IRS requires MAGI/FPL ratios to be truncated to whole percentages per [Form 8962 instructions](https://www.irs.gov/pub/irs-pdf/i8962.pdf#page=8). This creates ~$10 jumps in PTCs approximately every $100-200 income. The MTR chart applies a $1,000 moving average to smooth over these artifacts while preserving major cliffs (like PTC eligibility thresholds).
                """
                )


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
    """Create income curve charts showing PTC across income range

    Args:
        zip_code: 5-digit ZIP code string (required for LA County)
        income: Optional income to mark on chart. If None, no marker shown.
        show_ira: Whether to show IRA extension reform
        show_700fpl: Whether to show 700% FPL extension reform

    Returns tuple of (comparison_fig, delta_fig, benefit_info, income_range, ptc_baseline_range, ptc_reform_range, ptc_700fpl_range, slcsp, fpl, x_axis_max)
        Arrays are returned for interpolation

    Note: Caching removed to prevent signature mismatch issues on Streamlit Cloud
    """

    # Create base household structure for income sweep
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

    # Color for 700% FPL reform
    PURPLE = "#9467BD"

    try:
        # Create reforms for chart calculation
        reform_ira = create_enhanced_ptc_reform()
        reform_700fpl = create_700fpl_reform()

        # Calculate baseline
        sim_baseline = Simulation(situation=base_household)

        income_range = sim_baseline.calculate(
            "employment_income", map_to="household", period=2026
        )
        ptc_range_baseline = sim_baseline.calculate(
            "aca_ptc", map_to="household", period=2026
        )

        # Calculate IRA reform if selected
        ptc_range_reform = None
        if show_ira:
            sim_ira = Simulation(situation=base_household, reform=reform_ira)
            ptc_range_reform = sim_ira.calculate(
                "aca_ptc", map_to="household", period=2026
            )

        # Calculate 700% FPL reform if selected
        ptc_range_700fpl = None
        if show_700fpl and reform_700fpl is not None:
            sim_700fpl = Simulation(situation=base_household, reform=reform_700fpl)
            ptc_range_700fpl = sim_700fpl.calculate(
                "aca_ptc", map_to="household", period=2026
            )

        # Calculate Medicaid and CHIP values
        medicaid_range = sim_baseline.calculate(
            "medicaid_cost", map_to="household", period=2026
        )
        chip_range = sim_baseline.calculate(
            "per_capita_chip", map_to="household", period=2026
        )

        # Find where PTC goes to zero for dynamic x-axis range
        max_income_with_ptc = 200000  # Default fallback
        # Check all active reform PTCs
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

        # Add 10% padding to the range
        x_axis_max = min(1000000, max_income_with_ptc * 1.1)

        # Calculate delta (use IRA if available, otherwise 700% FPL)
        if ptc_range_reform is not None:
            delta_range = ptc_range_reform - ptc_range_baseline
        elif ptc_range_700fpl is not None:
            delta_range = ptc_range_700fpl - ptc_range_baseline
        else:
            delta_range = np.zeros_like(ptc_range_baseline)

        # Create hover text based on program eligibility
        import numpy as np

        hover_text = []
        for i in range(len(income_range)):
            inc = income_range[i]
            ptc_base = ptc_range_baseline[i]
            ptc_ira = ptc_range_reform[i] if ptc_range_reform is not None else 0
            ptc_700 = ptc_range_700fpl[i] if ptc_range_700fpl is not None else 0
            medicaid = medicaid_range[i]
            chip = chip_range[i]

            text = f"<b>Income: ${inc:,.0f}</b><br><br>"

            # Show all applicable benefits (not mutually exclusive)
            if medicaid > 0:
                text += f"<b>Medicaid:</b> ${medicaid:,.0f}/year<br>"
            if chip > 0:
                text += f"<b>CHIP:</b> ${chip:,.0f}/year<br>"

            # Always show PTC information if present
            if ptc_base > 0 or ptc_ira > 0 or ptc_700 > 0:
                text += f"<b>PTC (baseline):</b> ${ptc_base:,.0f}/year<br>"
                if show_ira and ptc_range_reform is not None:
                    text += f"<b>PTC (IRA extension):</b> ${ptc_ira:,.0f}/year<br>"
                if show_700fpl and ptc_range_700fpl is not None:
                    text += f"<b>PTC (700% FPL):</b> ${ptc_700:,.0f}/year<br>"

            hover_text.append(text)

        # Create the plot
        fig = go.Figure()

        # Build list of arrays to find max for hover trace
        arrays_for_max = [medicaid_range, chip_range, ptc_range_baseline]
        if ptc_range_reform is not None:
            arrays_for_max.append(ptc_range_reform)
        if ptc_range_700fpl is not None:
            arrays_for_max.append(ptc_range_700fpl)

        # Add invisible hover trace with unified information
        fig.add_trace(
            go.Scatter(
                x=income_range,
                y=np.maximum.reduce(arrays_for_max),
                mode="lines",
                line=dict(width=0),
                hovertext=hover_text,
                hoverinfo="text",
                showlegend=False,
                name="",
            )
        )

        # Add Medicaid line (always show in legend, hidden by default)
        fig.add_trace(
            go.Scatter(
                x=income_range,
                y=medicaid_range,
                mode="lines",
                name="Medicaid",
                line=dict(color=COLORS["green"], width=3),
                hoverinfo="skip",
                visible="legendonly",
            )
        )

        # Add CHIP line only if any household member is eligible
        if np.any(chip_range > 0):
            fig.add_trace(
                go.Scatter(
                    x=income_range,
                    y=chip_range,
                    mode="lines",
                    name="Children's Health Insurance Program (CHIP)",
                    line=dict(color=COLORS["secondary"], width=3),
                    hoverinfo="skip",
                    visible="legendonly",
                )
            )

        # Add baseline line (current law) - show first in legend
        fig.add_trace(
            go.Scatter(
                x=income_range,
                y=ptc_range_baseline,
                mode="lines",
                name="PTC (baseline)",
                line=dict(color=COLORS["gray"], width=3),
                hoverinfo="skip",
            )
        )

        # Add IRA extension line if selected
        if show_ira and ptc_range_reform is not None:
            fig.add_trace(
                go.Scatter(
                    x=income_range,
                    y=ptc_range_reform,
                    mode="lines",
                    name="PTC (IRA extension)",
                    line=dict(color=COLORS["primary"], width=3),
                    hoverinfo="skip",
                )
            )

        # Add 700% FPL extension line if selected
        if show_700fpl and ptc_range_700fpl is not None:
            fig.add_trace(
                go.Scatter(
                    x=income_range,
                    y=ptc_range_700fpl,
                    mode="lines",
                    name="PTC (700% FPL extension)",
                    line=dict(color=PURPLE, width=3),
                    hoverinfo="skip",
                )
            )

        # Add user's position markers (only if income is provided)
        if income is not None and income > 10000:
            # Interpolate PTC values at user's income
            ptc_baseline_user = np.interp(
                income, income_range, ptc_range_baseline
            )

            # Add baseline marker
            fig.add_annotation(
                x=income,
                y=ptc_baseline_user,
                text=f"Baseline: ${ptc_baseline_user:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=COLORS["gray"],
                ax=60,
                ay=40,
                bgcolor="white",
                bordercolor=COLORS["gray"],
                borderwidth=2,
            )

            if show_ira and ptc_range_reform is not None:
                ptc_ira_user = np.interp(income, income_range, ptc_range_reform)
                fig.add_annotation(
                    x=income,
                    y=ptc_ira_user,
                    text=f"IRA: ${ptc_ira_user:,.0f}",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor=COLORS["primary"],
                    ax=60,
                    ay=-40,
                    bgcolor="white",
                    bordercolor=COLORS["primary"],
                    borderwidth=2,
                )

            if show_700fpl and ptc_range_700fpl is not None:
                ptc_700_user = np.interp(income, income_range, ptc_range_700fpl)
                fig.add_annotation(
                    x=income,
                    y=ptc_700_user,
                    text=f"700% FPL: ${ptc_700_user:,.0f}",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor=PURPLE,
                    ax=-60,
                    ay=-40,
                    bgcolor="white",
                    bordercolor=PURPLE,
                    borderwidth=2,
                )

        # Update layout for comparison chart
        fig.update_layout(
            title={
                "text": "Healthcare assistance by household income (2026)",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Annual healthcare assistance value",
            height=400,
            xaxis=dict(
                tickformat="$,.0f", range=[0, x_axis_max], automargin=True
            ),
            yaxis=dict(
                tickformat="$,.0f", rangemode="tozero", automargin=True
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Roboto, sans-serif"),
            legend=dict(
                orientation="h", yanchor="bottom", y=0.98, xanchor="right", x=1
            ),
            margin=dict(l=80, r=40, t=60, b=80),
            **add_logo_to_layout(),
        )

        # Create delta chart
        fig_delta = go.Figure()

        # Create hover text for delta chart
        delta_hover_text = []
        for i in range(len(income_range)):
            inc = income_range[i]
            delta = delta_range[i]
            ptc_base = ptc_range_baseline[i]
            ptc_ira = ptc_range_reform[i] if ptc_range_reform is not None else 0
            ptc_700 = ptc_range_700fpl[i] if ptc_range_700fpl is not None else 0
            medicaid = medicaid_range[i]
            chip = chip_range[i]

            text = f"<b>Income: ${inc:,.0f}</b><br><br>"

            # Show all applicable benefits
            if medicaid > 0:
                text += f"<b>Medicaid:</b> ${medicaid:,.0f}/year<br>"
            if chip > 0:
                text += f"<b>CHIP:</b> ${chip:,.0f}/year<br>"

            # Show PTC amounts
            text += f"<b>PTC (baseline):</b> ${ptc_base:,.0f}/year<br>"
            if show_ira and ptc_range_reform is not None:
                text += f"<b>PTC (IRA extension):</b> ${ptc_ira:,.0f}/year<br>"
            if show_700fpl and ptc_range_700fpl is not None:
                text += f"<b>PTC (700% FPL):</b> ${ptc_700:,.0f}/year<br>"

            delta_hover_text.append(text)

        # Add delta lines for each selected reform
        if show_ira and ptc_range_reform is not None:
            delta_ira = ptc_range_reform - ptc_range_baseline
            fig_delta.add_trace(
                go.Scatter(
                    x=income_range,
                    y=delta_ira,
                    mode="lines",
                    name="IRA extension gain",
                    line=dict(color=COLORS["primary"], width=3),
                    fill="tozeroy",
                    fillcolor="rgba(44, 100, 150, 0.2)",
                    hovertext=delta_hover_text,
                    hoverinfo="text",
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
                    hovertext=delta_hover_text,
                    hoverinfo="text",
                )
            )

        fig_delta.update_layout(
            title={
                "text": "PTC gain from extending enhanced subsidies (2026)",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Annual PTC gain (extended - current law)",
            height=400,
            xaxis=dict(
                tickformat="$,.0f", range=[0, x_axis_max], automargin=True
            ),
            yaxis=dict(
                tickformat="$,.0f", rangemode="tozero", automargin=True
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Roboto, sans-serif"),
            showlegend=False,
            margin=dict(l=80, r=40, t=60, b=80),
            **add_logo_to_layout(),
        )

        # Calculate benefit range information
        benefit_indices = np.where(delta_range > 0)[0]
        if len(benefit_indices) > 0:
            min_benefit_income = income_range[benefit_indices[0]]
            max_benefit_income = income_range[benefit_indices[-1]]
            max_benefit = np.max(delta_range[benefit_indices])
            peak_benefit_index = benefit_indices[np.argmax(delta_range[benefit_indices])]
            peak_benefit_income = income_range[peak_benefit_index]

            benefit_info = {
                "min_income": float(min_benefit_income),
                "max_income": float(max_benefit_income),
                "max_benefit": float(max_benefit),
                "peak_income": float(peak_benefit_income),
            }

            # Add annotations to delta chart for min/max/peak
            # Min income annotation
            fig_delta.add_annotation(
                x=min_benefit_income,
                y=delta_range[benefit_indices[0]],
                text=f"Benefit starts<br>${min_benefit_income:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=COLORS["primary"],
                ax=-50,
                ay=-50,
                bgcolor=COLORS["primary"],
                bordercolor=COLORS["primary"],
                borderwidth=0,
                borderpad=8,
                font=dict(size=11, color="white"),
            )

            # Peak benefit annotation
            fig_delta.add_annotation(
                x=peak_benefit_income,
                y=max_benefit,
                text=f"Max benefit: ${max_benefit:,.0f}<br>at ${peak_benefit_income:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=COLORS["primary"],
                ax=0,
                ay=50,
                bgcolor=COLORS["primary"],
                bordercolor=COLORS["primary"],
                borderwidth=0,
                borderpad=8,
                font=dict(size=12, color="white"),
            )

            # Max income annotation
            fig_delta.add_annotation(
                x=max_benefit_income,
                y=delta_range[benefit_indices[-1]],
                text=f"Benefit ends<br>${max_benefit_income:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=COLORS["primary"],
                ax=50,
                ay=-50,
                bgcolor=COLORS["primary"],
                bordercolor=COLORS["primary"],
                borderwidth=0,
                borderpad=8,
                font=dict(size=11, color="white"),
            )
        else:
            benefit_info = None

        # Get SLCSP and FPL for display
        # SLCSP and FPL don't vary with income, but get from middle of array to avoid edge cases
        slcsp_array = sim_baseline.calculate("slcsp", map_to="household", period=2026)
        fpl_array = sim_baseline.calculate("tax_unit_fpg", period=2026)

        # Use max value for SLCSP (should be constant, but this handles any edge cases)
        slcsp = float(np.max(slcsp_array))
        fpl = float(fpl_array[len(fpl_array) // 2])  # Use middle value

        return (
            fig,
            fig_delta,
            benefit_info,
            income_range,
            ptc_range_baseline,
            ptc_range_reform,
            ptc_range_700fpl,
            slcsp,
            fpl,
            x_axis_max,
        )

    except Exception as e:
        # If chart generation fails, return None for everything
        st.error(f"Error generating charts: {str(e)}")
        import traceback

        st.error(traceback.format_exc())
        return None, None, None, None, None, None, None, 0, 0, 200000


def create_net_income_and_mtr_charts(
    age_head,
    age_spouse,
    dependent_ages,
    state,
    county=None,
    zip_code=None,
    x_axis_max=200000,
    show_ira=True,
    show_700fpl=False,
):
    """Create net income and MTR charts including health benefits

    Args:
        x_axis_max: Maximum income for x-axis (from PTC charts)
        show_ira: Whether to show IRA extension reform
        show_700fpl: Whether to show 700% FPL extension reform

    Returns tuple of (net_income_fig, mtr_fig, income_range, net_income_baseline, net_income_reform)
    """

    # Color for 700% FPL reform
    PURPLE = "#9467BD"

    # Create base household structure for income sweep
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

    # Set tax_unit_itemizes=False to avoid expensive itemization branching
    # This is an input variable, not a reform, so it doesn't slow down baseline
    base_household["tax_units"]["your tax unit"]["tax_unit_itemizes"] = {2026: False}

    try:
        # Create reforms
        reform_ira = create_enhanced_ptc_reform()
        reform_700fpl = create_700fpl_reform()

        # Run simulations (itemization already set to False via input)
        sim_baseline = Simulation(situation=base_household)

        sim_ira = None
        if show_ira:
            sim_ira = Simulation(situation=base_household, reform=reform_ira)

        sim_700fpl = None
        if show_700fpl and reform_700fpl is not None:
            sim_700fpl = Simulation(situation=base_household, reform=reform_700fpl)

        income_range = sim_baseline.calculate(
            "employment_income", map_to="household", period=2026
        )

        # Calculate net income including health benefits
        net_income_baseline = sim_baseline.calculate(
            "household_net_income_including_health_benefits", map_to="household", period=2026
        )

        net_income_ira = None
        if sim_ira is not None:
            net_income_ira = sim_ira.calculate(
                "household_net_income_including_health_benefits", map_to="household", period=2026
            )

        net_income_700fpl = None
        if sim_700fpl is not None:
            net_income_700fpl = sim_700fpl.calculate(
                "household_net_income_including_health_benefits", map_to="household", period=2026
            )

        # Apply 10-step ($1k) moving average to smooth IRS truncation artifacts
        window = 10
        def moving_average(arr, window_size):
            """Apply simple moving average smoothing."""
            result = np.copy(arr)
            for i in range(len(arr)):
                start = max(0, i - window_size // 2)
                end = min(len(arr), i + window_size // 2 + 1)
                result[i] = np.mean(arr[start:end])
            return result

        def calc_mtr(net_income_arr):
            """Calculate MTR from net income array."""
            mtr_raw = np.zeros_like(income_range)
            for i in range(len(income_range) - 1):
                d_income = income_range[i+1] - income_range[i]
                d_net = net_income_arr[i+1] - net_income_arr[i]
                mtr_raw[i] = 1 - d_net / d_income
            mtr_raw[-1] = mtr_raw[-2] if len(income_range) > 1 else 0
            mtr_viz = moving_average(mtr_raw, window)
            return np.clip(mtr_viz, -1.0, 1.5)

        mtr_baseline_viz = calc_mtr(net_income_baseline)
        mtr_ira_viz = calc_mtr(net_income_ira) if net_income_ira is not None else None
        mtr_700fpl_viz = calc_mtr(net_income_700fpl) if net_income_700fpl is not None else None

        # Create hover text for net income chart
        net_income_hover = []
        for i in range(len(income_range)):
            text = f"<b>Income: ${income_range[i]:,.0f}</b><br><br>"
            text += f"<b>Net income (baseline):</b> ${net_income_baseline[i]:,.0f}<br>"
            if net_income_ira is not None:
                text += f"<b>Net income (IRA extension):</b> ${net_income_ira[i]:,.0f}<br>"
            if net_income_700fpl is not None:
                text += f"<b>Net income (700% FPL):</b> ${net_income_700fpl[i]:,.0f}<br>"
            net_income_hover.append(text)

        # Create MTR hover text
        mtr_hover = []
        for i in range(len(income_range)):
            text = f"<b>Income: ${income_range[i]:,.0f}</b><br><br>"
            text += f"<b>MTR (baseline):</b> {mtr_baseline_viz[i]*100:.1f}%<br>"
            if mtr_ira_viz is not None:
                text += f"<b>MTR (IRA extension):</b> {mtr_ira_viz[i]*100:.1f}%<br>"
            if mtr_700fpl_viz is not None:
                text += f"<b>MTR (700% FPL):</b> {mtr_700fpl_viz[i]*100:.1f}%<br>"
            mtr_hover.append(text)

        # Create net income chart
        fig_net_income = go.Figure()

        fig_net_income.add_trace(
            go.Scatter(
                x=income_range,
                y=net_income_baseline,
                mode="lines",
                name="Baseline",
                line=dict(color=COLORS["gray"], width=3),
                hovertext=net_income_hover,
                hoverinfo="text",
            )
        )

        if net_income_ira is not None:
            fig_net_income.add_trace(
                go.Scatter(
                    x=income_range,
                    y=net_income_ira,
                    mode="lines",
                    name="IRA extension",
                    line=dict(color=COLORS["primary"], width=3),
                    hovertext=net_income_hover,
                    hoverinfo="text",
                )
            )

        if net_income_700fpl is not None:
            fig_net_income.add_trace(
                go.Scatter(
                    x=income_range,
                    y=net_income_700fpl,
                    mode="lines",
                    name="700% FPL extension",
                    line=dict(color=PURPLE, width=3),
                    hovertext=net_income_hover,
                    hoverinfo="text",
                )
            )

        # Set y-axis range to 1.2x the max value within visible x range
        # Find indices within x_axis_max
        visible_indices = income_range <= x_axis_max
        net_income_arrays = [net_income_baseline[visible_indices]]
        if net_income_ira is not None:
            net_income_arrays.append(net_income_ira[visible_indices])
        if net_income_700fpl is not None:
            net_income_arrays.append(net_income_700fpl[visible_indices])
        net_income_max = max(np.max(arr) for arr in net_income_arrays)
        net_income_y_max = net_income_max * 1.2

        fig_net_income.update_layout(
            title={
                "text": "Net income (2026)",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Net income",
            height=400,
            xaxis=dict(
                tickformat="$,.0f", range=[0, x_axis_max], automargin=True
            ),
            yaxis=dict(
                tickformat="$,.0f", range=[0, net_income_y_max], automargin=True
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Roboto, sans-serif"),
            legend=dict(
                orientation="h", yanchor="bottom", y=0.98, xanchor="right", x=1
            ),
            margin=dict(l=80, r=40, t=60, b=80),
            **add_logo_to_layout(),
        )

        # Create MTR chart
        fig_mtr = go.Figure()

        fig_mtr.add_trace(
            go.Scatter(
                x=income_range,
                y=mtr_baseline_viz,
                mode="lines",
                name="Baseline",
                line=dict(color=COLORS["gray"], width=3),
                hovertext=mtr_hover,
                hoverinfo="text",
            )
        )

        if mtr_ira_viz is not None:
            fig_mtr.add_trace(
                go.Scatter(
                    x=income_range,
                    y=mtr_ira_viz,
                    mode="lines",
                    name="IRA extension",
                    line=dict(color=COLORS["primary"], width=3),
                    hovertext=mtr_hover,
                    hoverinfo="text",
                )
            )

        if mtr_700fpl_viz is not None:
            fig_mtr.add_trace(
                go.Scatter(
                    x=income_range,
                    y=mtr_700fpl_viz,
                    mode="lines",
                    name="700% FPL extension",
                    line=dict(color=PURPLE, width=3),
                    hovertext=mtr_hover,
                    hoverinfo="text",
                )
            )

        fig_mtr.update_layout(
            title={
                "text": "Marginal tax rate (2026)",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Marginal tax rate",
            height=400,
            xaxis=dict(
                tickformat="$,.0f", range=[0, x_axis_max], automargin=True
            ),
            yaxis=dict(
                tickformat=".0%", range=[-0.1, 1.0], automargin=True, zeroline=True, zerolinecolor="black", zerolinewidth=2
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Roboto, sans-serif"),
            legend=dict(
                orientation="h", yanchor="bottom", y=0.98, xanchor="right", x=1
            ),
            margin=dict(l=80, r=40, t=60, b=80),
            **add_logo_to_layout(),
        )

        # Clean up memory before returning
        gc.collect()

        return (
            fig_net_income,
            fig_mtr,
            income_range,
            net_income_baseline,
            net_income_ira,
        )

    except Exception as e:
        st.error(f"Error generating net income/MTR charts: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, None, None, None, None


if __name__ == "__main__":
    main()
