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
    from policyengine_us import Simulation
    import plotly.graph_objects as go
    import base64

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

            The analysis compares two scenarios:
            - **Current law**: Enhanced premium tax credits expire after 2025
            - **Extended**: Enhanced PTCs continue through 2026
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
                )

                # Store arrays and charts in session state for later use
                if income_range is not None:
                    st.session_state.income_range = income_range
                    st.session_state.ptc_baseline_range = ptc_baseline_range
                    st.session_state.ptc_reform_range = ptc_reform_range
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
                )

            with tab2:
                st.plotly_chart(
                    st.session_state.fig_comparison,
                    use_container_width=True,
                    config={"displayModeBar": False},
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
                # Auto-generate MTR chart if not cached (uses same calculation as net income)
                if not hasattr(st.session_state, "fig_mtr") or st.session_state.fig_mtr is None:
                    # Check if we already have net income data (they're calculated together)
                    if hasattr(st.session_state, "fig_net_income") and st.session_state.fig_net_income is not None:
                        # MTR already calculated with net income
                        pass
                    else:
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
                            )

                            # Store in session state
                            if fig_mtr is not None:
                                st.session_state.fig_net_income = fig_net_income
                                st.session_state.fig_mtr = fig_mtr

                # Display cached chart
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
                from importlib.metadata import version

                pe_version = version("policyengine-us")

                st.markdown(
                    f"""
                The Inflation Reduction Act enhanced ACA subsidies through 2025. This calculator shows how extending these enhancements to 2026 would affect your household's premium tax credits.

                This calculator uses [PolicyEngine's open-source tax-benefit microsimulation model](https://github.com/PolicyEngine/policyengine-us) (version {pe_version}).

                **2026 premium projections:** This calculator projects Second Lowest Cost Silver Plan (SLCSP) premiums for 2026 by applying a 4.19% increase to actual 2025 benchmark premiums from KFF, based on 2024-25 growth patterns. Actual premiums may rise faster, and we will update the calculator when CMS releases official data in October 2025.

                📖 [Learn more about enhanced premium tax credits](https://policyengine.org/us/research/enhanced-premium-tax-credits-extension)

                **Enhanced PTCs extended:**
                - No income cap - households above 400% FPL can still receive credits
                - Lower premium contribution percentages (0-8.5% of income)
                - More generous subsidies at all income levels

                **Current law (enhanced PTCs expire):**
                - Hard cap at 400% FPL - no credits above this level (the "subsidy cliff")
                - Higher contribution percentages (2.1-9.96% of income, per IRS Revenue Procedure 2025-25)
                - Less generous subsidies, especially for middle incomes
                """
                )


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
    """Calculate PTC for baseline or IRA enhanced scenario using 2026 comparison

    Matches notebook pattern exactly - uses copy.deepcopy pattern with income injection

    Args:
        county_name: County name from dropdown (e.g. "Travis County")
                    Will be converted to PolicyEngine format (TRAVIS_COUNTY_TX)
        zip_code: 5-digit ZIP code string (required for LA County)

    Returns:
        tuple: (ptc, slcsp, fpl, fpl_pct) - PTC amount, SLCSP premium, FPL dollar amount, and income as % of FPL (for display only)
    """
    import copy

    try:
        # Build base household situation (matches notebook structure exactly)
        situation = {
            "people": {"you": {"age": {2026: age_head}}},
            "families": {"your family": {"members": ["you"]}},
            "spm_units": {"your household": {"members": ["you"]}},
            "tax_units": {"your tax unit": {"members": ["you"]}},
            "households": {
                "your household": {
                    "members": ["you"],
                    "state_name": {2026: state},
                }
            },
        }

        # Add county if provided - convert to PolicyEngine format
        if county_name:
            # Convert "Travis County" -> "TRAVIS_COUNTY_TX"
            county_pe_format = (
                county_name.upper().replace(" ", "_") + "_" + state
            )
            situation["households"]["your household"]["county"] = {
                2026: county_pe_format
            }

        # Add ZIP code if provided (required for LA County)
        if zip_code:
            situation["households"]["your household"]["zip_code"] = {
                2026: zip_code
            }

        # Add spouse if married
        if age_spouse:
            situation["people"]["your partner"] = {"age": {2026: age_spouse}}
            situation["families"]["your family"]["members"].append(
                "your partner"
            )
            situation["spm_units"]["your household"]["members"].append(
                "your partner"
            )
            situation["tax_units"]["your tax unit"]["members"].append(
                "your partner"
            )
            situation["households"]["your household"]["members"].append(
                "your partner"
            )
            situation["marital_units"] = {
                "your marital unit": {"members": ["you", "your partner"]}
            }

        # Add dependents with consistent naming (matches notebook)
        for i, dep_age in enumerate(dependent_ages):
            if i == 0:
                child_id = "your first dependent"
            elif i == 1:
                child_id = "your second dependent"
            else:
                child_id = f"dependent_{i+1}"

            situation["people"][child_id] = {"age": {2026: dep_age}}
            situation["families"]["your family"]["members"].append(child_id)
            situation["spm_units"]["your household"]["members"].append(
                child_id
            )
            situation["tax_units"]["your tax unit"]["members"].append(child_id)
            situation["households"]["your household"]["members"].append(
                child_id
            )

            # Add child's marital unit
            if "marital_units" not in situation:
                situation["marital_units"] = {}
            situation["marital_units"][f"{child_id}'s marital unit"] = {
                "members": [child_id]
            }

        # Deep copy and inject income (matches notebook pattern)
        sit = copy.deepcopy(situation)

        # Split income between adults if married, otherwise single person gets all
        # Note: Cannot set aca_magi directly - must use employment_income for reforms to work
        if age_spouse:
            sit["people"]["you"]["employment_income"] = {2026: income / 2}
            sit["people"]["your partner"]["employment_income"] = {
                2026: income / 2
            }
        else:
            sit["people"]["you"]["employment_income"] = {2026: income}

        # Create reform if requested (exact same as notebook)
        reform = None
        if use_reform:
            from policyengine_core.reforms import Reform

            reform = Reform.from_dict(
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

        # Run simulation
        sim = Simulation(situation=sit, reform=reform)

        ptc = sim.calculate("aca_ptc", map_to="household", period=2026)[0]
        slcsp = sim.calculate("slcsp", map_to="household", period=2026)[0]
        # Get FPL info for display only (all calculations done by PolicyEngine)
        fpl = sim.calculate("tax_unit_fpg", period=2026)[0]
        aca_magi_fraction = sim.calculate("aca_magi_fraction", period=2026)[0]
        fpl_pct = aca_magi_fraction * 100

        return float(max(0, ptc)), float(slcsp), float(fpl), float(fpl_pct)

    except Exception as e:
        st.error(f"Calculation error: {str(e)}")
        import traceback

        st.error(traceback.format_exc())
        return 0, 0, 0, 0


def create_chart(
    age_head,
    age_spouse,
    dependent_ages,
    state,
    county=None,
    zip_code=None,
    income=None,
):
    """Create income curve charts showing PTC across income range

    Args:
        zip_code: 5-digit ZIP code string (required for LA County)
        income: Optional income to mark on chart. If None, no marker shown.

    Returns tuple of (comparison_fig, delta_fig, benefit_info, income_range, ptc_baseline_range, ptc_reform_range, slcsp, fpl, x_axis_max)
        Arrays are returned for interpolation

    Note: Caching removed to prevent signature mismatch issues on Streamlit Cloud
    """

    # Create base household structure for income sweep
    base_household = {
        "people": {"you": {"age": {2026: age_head}}},
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {"members": ["you"], "state_name": {2026: state}}
        },
        "axes": [
            [
                {
                    "name": "employment_income",
                    "count": 10_001,  # 10_001 points for exact $100 increments (0 to 1M)
                    "min": 0,
                    "max": 1000000,
                    "period": 2026,  # Specify period to get exact values without uprating
                }
            ]
        ],
    }

    # Add county if provided
    if county:
        county_pe_format = county.upper().replace(" ", "_") + "_" + state
        base_household["households"]["your household"]["county"] = {
            2026: county_pe_format
        }

    # Add ZIP code if provided (required for LA County)
    if zip_code:
        base_household["households"]["your household"]["zip_code"] = {
            2026: zip_code
        }

    # Add spouse if married
    if age_spouse:
        base_household["people"]["your partner"] = {"age": {2026: age_spouse}}
        base_household["families"]["your family"]["members"].append(
            "your partner"
        )
        base_household["spm_units"]["your household"]["members"].append(
            "your partner"
        )
        base_household["tax_units"]["your tax unit"]["members"].append(
            "your partner"
        )
        base_household["households"]["your household"]["members"].append(
            "your partner"
        )
        base_household["marital_units"] = {
            "your marital unit": {"members": ["you", "your partner"]}
        }

    # Add dependents
    for i, dep_age in enumerate(dependent_ages):
        if i == 0:
            child_id = "your first dependent"
        elif i == 1:
            child_id = "your second dependent"
        else:
            child_id = f"dependent_{i+1}"

        base_household["people"][child_id] = {"age": {2026: dep_age}}
        base_household["families"]["your family"]["members"].append(child_id)
        base_household["spm_units"]["your household"]["members"].append(
            child_id
        )
        base_household["tax_units"]["your tax unit"]["members"].append(
            child_id
        )
        base_household["households"]["your household"]["members"].append(
            child_id
        )

        # Add child's marital unit
        if "marital_units" not in base_household:
            base_household["marital_units"] = {}
        base_household["marital_units"][f"{child_id}'s marital unit"] = {
            "members": [child_id]
        }

    try:
        # Create reform for chart calculation
        from policyengine_core.reforms import Reform

        reform = Reform.from_dict(
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

        # Calculate both curves - baseline and reform for 2026
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

        # Calculate Medicaid and CHIP values
        medicaid_range = sim_baseline.calculate(
            "medicaid_cost", map_to="household", period=2026
        )
        chip_range = sim_baseline.calculate(
            "per_capita_chip", map_to="household", period=2026
        )

        # Find where PTC goes to zero for dynamic x-axis range
        # Use reform PTC since it always extends to higher incomes than baseline
        # (baseline has 400% FPL cliff, reform removes it)
        max_income_with_ptc = 200000  # Default fallback
        for i in range(len(ptc_range_reform) - 1, -1, -1):
            if ptc_range_reform[i] > 0:
                max_income_with_ptc = income_range[i]
                break

        # Add 10% padding to the range
        x_axis_max = min(1000000, max_income_with_ptc * 1.1)

        # Calculate delta
        delta_range = ptc_range_reform - ptc_range_baseline

        # Create hover text based on program eligibility
        import numpy as np

        hover_text = []
        for i in range(len(income_range)):
            inc = income_range[i]
            ptc_base = ptc_range_baseline[i]
            ptc_ref = ptc_range_reform[i]
            delta = delta_range[i]
            medicaid = medicaid_range[i]
            chip = chip_range[i]

            text = f"<b>Income: ${inc:,.0f}</b><br><br>"

            # Show all applicable benefits (not mutually exclusive)
            if medicaid > 0:
                text += f"<b>Medicaid:</b> ${medicaid:,.0f}/year<br>"
            if chip > 0:
                text += f"<b>CHIP:</b> ${chip:,.0f}/year<br>"

            # Always show PTC information if present
            if ptc_base > 0 or ptc_ref > 0:
                text += f"<b>PTC (current law):</b> ${ptc_base:,.0f}/year<br>"
                text += f"<b>PTC (extended):</b> ${ptc_ref:,.0f}/year<br>"
                if delta > 0:
                    text += f"<b>PTC difference:</b> +${delta:,.0f}/year"
                elif delta < 0:
                    text += f"<b>PTC difference:</b> -${abs(delta):,.0f}/year"
                else:
                    text += f"<b>PTC difference:</b> $0"

            hover_text.append(text)

        # Create the plot
        fig = go.Figure()

        # Add invisible hover trace with unified information
        fig.add_trace(
            go.Scatter(
                x=income_range,
                y=np.maximum.reduce(
                    [
                        medicaid_range,
                        chip_range,
                        ptc_range_baseline,
                        ptc_range_reform,
                    ]
                ),
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
                name="PTC (current law)",
                line=dict(color=COLORS["gray"], width=3),
                hoverinfo="skip",
            )
        )

        # Add reform line (enhanced PTCs extended)
        fig.add_trace(
            go.Scatter(
                x=income_range,
                y=ptc_range_reform,
                mode="lines",
                name="PTC (enhanced PTCs extended)",
                line=dict(color=COLORS["primary"], width=3),
                hoverinfo="skip",
            )
        )

        # Add user's position markers (only if income is provided)
        if income is not None and income > 10000:
            # Interpolate PTC values at user's income
            ptc_baseline_user = np.interp(
                income, income_range, ptc_range_baseline
            )
            ptc_reform_user = np.interp(income, income_range, ptc_range_reform)

            fig.add_trace(
                go.Scatter(
                    x=[income, income],
                    y=[ptc_baseline_user, ptc_reform_user],
                    mode="markers",
                    name="Your Household",
                    marker=dict(
                        color=[COLORS["gray"], COLORS["primary"]],
                        size=12,
                        symbol="diamond",
                        line=dict(width=2, color="white"),
                    ),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            fig.add_annotation(
                x=income,
                y=ptc_baseline_user,
                text=f"Current law: ${ptc_baseline_user:,.0f}",
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

            fig.add_annotation(
                x=income,
                y=ptc_reform_user,
                text=f"Extended: ${ptc_reform_user:,.0f}",
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
            ptc_ref = ptc_range_reform[i]
            medicaid = medicaid_range[i]
            chip = chip_range[i]

            text = f"<b>Income: ${inc:,.0f}</b><br><br>"

            # Show all applicable benefits
            if medicaid > 0:
                text += f"<b>Medicaid:</b> ${medicaid:,.0f}/year<br>"
            if chip > 0:
                text += f"<b>CHIP:</b> ${chip:,.0f}/year<br>"

            # Show PTC amounts and gain from extension
            if ptc_base > 0 or ptc_ref > 0:
                text += f"<b>PTC (current law):</b> ${ptc_base:,.0f}/year<br>"
                text += f"<b>PTC (extended):</b> ${ptc_ref:,.0f}/year<br>"
                if delta > 0:
                    text += f"<b>Gain from extension:</b> ${delta:,.0f}/year"
                else:
                    text += f"<b>No change</b>"

            delta_hover_text.append(text)

        # Add delta line
        fig_delta.add_trace(
            go.Scatter(
                x=income_range,
                y=delta_range,
                mode="lines",
                name="PTC gain from extension",
                line=dict(color=COLORS["primary"], width=3),
                fill="tozeroy",
                fillcolor=f"rgba(44, 100, 150, 0.2)",
                hovertext=delta_hover_text,
                hoverinfo="text",
            )
        )

        # Add user's position marker (only if income is provided)
        if income is not None and income > 10000:
            # Interpolate values at user's income
            ptc_baseline_user = np.interp(
                income, income_range, ptc_range_baseline
            )
            ptc_reform_user = np.interp(income, income_range, ptc_range_reform)
            user_difference = ptc_reform_user - ptc_baseline_user

            fig_delta.add_trace(
                go.Scatter(
                    x=[income],
                    y=[user_difference],
                    mode="markers",
                    name="Your household",
                    marker=dict(
                        color=COLORS["primary"],
                        size=12,
                        symbol="diamond",
                        line=dict(width=2, color="white"),
                    ),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            fig_delta.add_annotation(
                x=income,
                y=user_difference,
                text=f"You: ${user_difference:,.0f}",
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
            slcsp,
            fpl,
            x_axis_max,
        )

    except Exception as e:
        # If chart generation fails, return None for everything
        st.error(f"Error generating charts: {str(e)}")
        import traceback

        st.error(traceback.format_exc())
        return None, None, None, None, None, None, 0, 0, 200000


def create_net_income_and_mtr_charts(
    age_head,
    age_spouse,
    dependent_ages,
    state,
    county=None,
    zip_code=None,
    x_axis_max=200000,
):
    """Create net income and MTR charts including health benefits

    Args:
        x_axis_max: Maximum income for x-axis (from PTC charts)

    Returns tuple of (net_income_fig, mtr_fig, income_range, net_income_baseline, net_income_reform)
    """

    # Create base household structure (same as create_chart)
    base_household = {
        "people": {"you": {"age": {2026: age_head}}},
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {"members": ["you"], "state_name": {2026: state}}
        },
        "axes": [
            [
                {
                    "name": "employment_income",
                    "count": 10_001,
                    "min": 0,
                    "max": 1000000,
                    "period": 2026,
                }
            ]
        ],
    }

    # Add county if provided
    if county:
        county_pe_format = county.upper().replace(" ", "_") + "_" + state
        base_household["households"]["your household"]["county"] = {
            2026: county_pe_format
        }

    # Add ZIP code if provided
    if zip_code:
        base_household["households"]["your household"]["zip_code"] = {
            2026: zip_code
        }

    # Add spouse if married
    if age_spouse:
        base_household["people"]["your partner"] = {"age": {2026: age_spouse}}
        base_household["families"]["your family"]["members"].append("your partner")
        base_household["spm_units"]["your household"]["members"].append("your partner")
        base_household["tax_units"]["your tax unit"]["members"].append("your partner")
        base_household["households"]["your household"]["members"].append("your partner")
        base_household["marital_units"] = {
            "your marital unit": {"members": ["you", "your partner"]}
        }

    # Add dependents
    for i, dep_age in enumerate(dependent_ages):
        if i == 0:
            child_id = "your first dependent"
        elif i == 1:
            child_id = "your second dependent"
        else:
            child_id = f"dependent_{i+1}"

        base_household["people"][child_id] = {"age": {2026: dep_age}}
        base_household["families"]["your family"]["members"].append(child_id)
        base_household["spm_units"]["your household"]["members"].append(child_id)
        base_household["tax_units"]["your tax unit"]["members"].append(child_id)
        base_household["households"]["your household"]["members"].append(child_id)

        if "marital_units" not in base_household:
            base_household["marital_units"] = {}
        base_household["marital_units"][f"{child_id}'s marital unit"] = {
            "members": [child_id]
        }

    try:
        from policyengine_core.reforms import Reform

        # Create reform for extended PTCs
        reform = Reform.from_dict(
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

        # Run simulations
        sim_baseline = Simulation(situation=base_household)
        sim_reform = Simulation(situation=base_household, reform=reform)

        income_range = sim_baseline.calculate(
            "employment_income", map_to="household", period=2026
        )

        # Calculate net income including health benefits
        # Use PolicyEngine's built-in variable that includes PTCs, Medicaid, CHIP
        net_income_baseline = sim_baseline.calculate(
            "household_net_income_including_health_benefits", map_to="household", period=2026
        )
        net_income_reform = sim_reform.calculate(
            "household_net_income_including_health_benefits", map_to="household", period=2026
        )

        # Calculate MTR using numerical differentiation with smoothing
        # MTR = 1 - d(net_income)/d(employment_income)
        # Use wider window (10 points = $1000) for smoother MTR
        # Income range has uniform $100 spacing
        window = 10
        d_income_central = income_range[window] - income_range[0]  # $1000 for edges
        d_income_window = 2 * d_income_central  # $2000 for central differences

        mtr_baseline = np.zeros_like(income_range)
        mtr_reform = np.zeros_like(income_range)

        # Central differences for interior points
        for i in range(window, len(income_range) - window):
            d_net_baseline = net_income_baseline[i+window] - net_income_baseline[i-window]
            d_net_reform = net_income_reform[i+window] - net_income_reform[i-window]

            mtr_baseline[i] = 1 - d_net_baseline / d_income_window
            mtr_reform[i] = 1 - d_net_reform / d_income_window

        # Handle edges with forward differences
        for i in range(window):
            d_net_baseline = net_income_baseline[i+window] - net_income_baseline[i]
            d_net_reform = net_income_reform[i+window] - net_income_reform[i]
            mtr_baseline[i] = 1 - d_net_baseline / d_income_central
            mtr_reform[i] = 1 - d_net_reform / d_income_central

        # Handle trailing edges with backward differences
        for i in range(len(income_range) - window, len(income_range)):
            d_net_baseline = net_income_baseline[i] - net_income_baseline[i-window]
            d_net_reform = net_income_reform[i] - net_income_reform[i-window]
            mtr_baseline[i] = 1 - d_net_baseline / d_income_central
            mtr_reform[i] = 1 - d_net_reform / d_income_central

        # Bound MTR at +/- 100%
        mtr_baseline = np.clip(mtr_baseline, -1.0, 1.0)
        mtr_reform = np.clip(mtr_reform, -1.0, 1.0)

        # Convert to percentage
        mtr_baseline_pct = mtr_baseline * 100
        mtr_reform_pct = mtr_reform * 100

        # Create hover text for net income chart
        net_income_hover = []
        for i in range(len(income_range)):
            text = f"<b>Income: ${income_range[i]:,.0f}</b><br><br>"
            text += f"<b>Net income (current law):</b> ${net_income_baseline[i]:,.0f}<br>"
            text += f"<b>Net income (extended):</b> ${net_income_reform[i]:,.0f}<br>"
            diff = net_income_reform[i] - net_income_baseline[i]
            if diff > 0:
                text += f"<b>Gain from extension:</b> ${diff:,.0f}"
            else:
                text += "<b>No difference</b>"
            net_income_hover.append(text)

        # Create MTR hover text
        mtr_hover = []
        for i in range(len(income_range)):
            text = f"<b>Income: ${income_range[i]:,.0f}</b><br><br>"
            text += f"<b>MTR (current law):</b> {mtr_baseline_pct[i]:.1f}%<br>"
            text += f"<b>MTR (extended):</b> {mtr_reform_pct[i]:.1f}%<br>"
            diff = mtr_reform_pct[i] - mtr_baseline_pct[i]
            if abs(diff) > 0.1:
                text += f"<b>Difference:</b> {diff:+.1f} pp"
            else:
                text += "<b>No difference</b>"
            mtr_hover.append(text)

        # Create net income chart
        fig_net_income = go.Figure()

        fig_net_income.add_trace(
            go.Scatter(
                x=income_range,
                y=net_income_baseline,
                mode="lines",
                name="Current law",
                line=dict(color=COLORS["gray"], width=3),
                hovertext=net_income_hover,
                hoverinfo="text",
            )
        )

        fig_net_income.add_trace(
            go.Scatter(
                x=income_range,
                y=net_income_reform,
                mode="lines",
                name="Enhanced PTCs extended",
                line=dict(color=COLORS["primary"], width=3),
                hoverinfo="skip",
            )
        )

        fig_net_income.update_layout(
            title={
                "text": "Net income including health benefits (2026)",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Net income (including health benefits)",
            height=400,
            xaxis=dict(
                tickformat="$,.0f", range=[0, x_axis_max], automargin=True
            ),
            yaxis=dict(
                tickformat="$,.0f", automargin=True
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
                y=mtr_baseline_pct,
                mode="lines",
                name="Current law",
                line=dict(color=COLORS["gray"], width=3),
                hovertext=mtr_hover,
                hoverinfo="text",
            )
        )

        fig_mtr.add_trace(
            go.Scatter(
                x=income_range,
                y=mtr_reform_pct,
                mode="lines",
                name="Enhanced PTCs extended",
                line=dict(color=COLORS["primary"], width=3),
                hoverinfo="skip",
            )
        )

        fig_mtr.update_layout(
            title={
                "text": "Marginal tax rate including health benefits (2026)",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Marginal tax rate",
            height=400,
            xaxis=dict(
                tickformat="$,.0f", range=[0, x_axis_max], automargin=True
            ),
            yaxis=dict(
                tickformat=".0f", ticksuffix="%", automargin=True
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

        return (
            fig_net_income,
            fig_mtr,
            income_range,
            net_income_baseline,
            net_income_reform,
        )

    except Exception as e:
        st.error(f"Error generating net income/MTR charts: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, None, None, None, None


if __name__ == "__main__":
    main()
