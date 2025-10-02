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
        initial_sidebar_state="expanded"
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
        with open('blue.png', 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

# Load counties from PolicyEngine data
@st.cache_data
def load_counties():
    try:
        with open('counties.json', 'r') as f:
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
        with open('blue.png', 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

def add_logo_to_layout():
    """Add PolicyEngine logo to chart layout"""
    logo_base64 = get_logo_base64()
    if logo_base64:
        return {
            "images": [{
                "source": f"data:image/png;base64,{logo_base64}",
                "xref": "paper",
                "yref": "paper",
                "x": 1,
                "y": -0.15,
                "sizex": 0.15,
                "sizey": 0.15,
                "xanchor": "right",
                "yanchor": "bottom",
            }]
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

    st.title("How Would Extending Enhanced Subsidies Affect You?")
    st.markdown(
        '<p class="subtitle">Calculate your premium tax credits under '
        "current law vs. extended enhancements</p>",
        unsafe_allow_html=True,
    )

    st.markdown("""
    The Inflation Reduction Act enhanced ACA subsidies through 2025. Use this calculator to explore how extending these enhancements to 2026 would affect your household's premium tax credits.

    📖 [Learn more about enhanced premium tax credits](https://policyengine.org/us/research/enhanced-premium-tax-credits-extension)
    """)

    with st.expander("Understanding the enhanced subsidies"):
        st.markdown("""
        **Enhanced PTCs extended:**
        - No income cap - households above 400% FPL can still receive credits
        - Lower premium contribution percentages (0-8.5% of income)
        - More generous subsidies at all income levels

        **Current law (enhanced PTCs expire):**
        - Hard cap at 400% FPL - no credits above this level (the "subsidy cliff")
        - Higher contribution percentages (2-9.5% of income)
        - Less generous subsidies, especially for middle incomes
        """)
    
    counties = load_counties()

    # Sidebar for household configuration
    with st.sidebar:
        st.header("Household Configuration")

        married = st.checkbox("Are you married?", value=False)

        age_head = st.number_input(
            "How old are you?", min_value=18, max_value=100, value=35
        )

        if married:
            age_spouse = st.number_input(
                "How old is your spouse?", min_value=18, max_value=100, value=35
            )
        else:
            age_spouse = None

        num_dependents = st.number_input(
            "How many children or dependents do you have?",
            min_value=0,
            max_value=10,
            value=0
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
                    key=f"dep_{i}"
                )
                dependent_ages.append(age_dep)

        income = st.number_input(
            "What is your annual household income?",
            min_value=0,
            value=0,
            step=1000,
            help="Modified Adjusted Gross Income (MAGI) as defined in 26 USC § 36B(d)(2). Includes: wages, self-employment income, capital gains, interest, dividends, pensions, Social Security, unemployment, rental income, and other income sources. Also includes tax-exempt interest and tax-exempt Social Security.",
            format="%d"
        )

        states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL",
                  "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA",
                  "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE",
                  "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
                  "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT",
                  "VA", "WA", "WV", "WI", "WY", "DC"]

        state = st.selectbox("Which state do you live in?", states, index=0)  # Default to AL

        # County selection - auto-select first alphabetically
        county = None
        if counties and state in counties:
            sorted_counties = sorted(counties[state])
            county = st.selectbox(
                "Which county?",
                sorted_counties,
                index=0,
                help="County used for marketplace calculations"
            )

        st.markdown("---")

        calculate_button = st.button(
            "Calculate Premium Tax Credits",
            type="primary",
            use_container_width=True
        )

        if calculate_button:
            st.session_state.calculate = True
            st.session_state.params = {
                'age_head': age_head,
                'age_spouse': age_spouse,
                'income': income,
                'dependent_ages': dependent_ages,
                'state': state,
                'county': county,
                'married': married
            }

    # Main content area
    if hasattr(st.session_state, 'calculate') and st.session_state.calculate:
        st.header("Your Results")

        params = st.session_state.params

        with st.spinner("Calculating..."):
            # Calculate household size and FPL
            household_size = 1 + (1 if params['age_spouse'] else 0) + len(params['dependent_ages'])
            fpl_pct = calculate_fpl_percentage(params['income'], household_size)

            # Calculate PTCs - compare 2026 baseline vs 2026 with IRA reform!
            # Pass county name if selected (will be converted to PolicyEngine format)
            county_name = params['county'] if params['county'] else None

            ptc_2026_with_ira, slcsp_2026 = calculate_ptc(
                params['age_head'], params['age_spouse'], params['income'],
                params['dependent_ages'], params['state'], county_name, use_reform=True
            )

            ptc_2026_baseline, _ = calculate_ptc(
                params['age_head'], params['age_spouse'], params['income'],
                params['dependent_ages'], params['state'], county_name, use_reform=False
            )

            difference = ptc_2026_with_ira - ptc_2026_baseline

            # Display SLCSP if available
            if slcsp_2026 > 0:
                st.info(f"Your base Second Lowest Cost Silver Plan is ${slcsp_2026:,.0f} per year (${slcsp_2026/12:,.0f} per month)")

            # Display metrics with custom CSS to prevent truncation
            st.markdown("""
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
            """, unsafe_allow_html=True)

            col_baseline, col_with_ira, col_diff = st.columns(3)

            with col_baseline:
                st.metric("Current law", f"${ptc_2026_baseline:,.0f} per year",
                         help="Your credits under current law (enhanced PTCs expire)")

            with col_with_ira:
                st.metric("Enhanced PTCs extended", f"${ptc_2026_with_ira:,.0f} per year",
                         help="Your credits if enhanced subsidies were extended")

            with col_diff:
                if difference > 0:
                    st.metric("You Lose", f"${difference:,.0f} per year",
                             f"-${difference/12:,.0f} per month", delta_color="inverse")
                elif difference < 0:
                    # This shouldn't happen but just in case
                    st.metric("You Gain?", f"${abs(difference):,.0f} per year",
                             f"+${abs(difference)/12:,.0f} per month", delta_color="normal")
                else:
                    st.metric("No Change", "$0")

            # Impact message
            if ptc_2026_with_ira == 0 and ptc_2026_baseline == 0:
                if fpl_pct > 400:
                    st.info("### No Premium Tax Credits Available")
                    st.write("Your income exceeds 400% FPL, which is above the credit limit in both scenarios.")
                else:
                    st.info("### No Premium Tax Credits Available")
                    st.write("Your income is below the minimum threshold for ACA premium tax credits in both scenarios. Check the chart below to see potential Medicaid or CHIP eligibility.")
            elif ptc_2026_with_ira > 0 and ptc_2026_baseline == 0:
                if fpl_pct > 400:
                    st.warning("### Credits available only with enhanced PTCs extended")
                    st.warning(f"Premium tax credits: ${ptc_2026_with_ira:,.0f} per year with enhanced PTCs extended, $0 under current law.")
                    st.warning("Your income exceeds 400% FPL. Credits are available above this limit with enhanced PTCs but not under current law.")
                else:
                    st.warning("### Credits available only with enhanced PTCs extended")
                    st.warning(f"Premium tax credits: ${ptc_2026_with_ira:,.0f} per year with enhanced PTCs extended, $0 under current law.")
                    st.warning("Higher contribution requirements under current law eliminate your credit eligibility.")
            elif difference > 0:
                st.info("### Credit reduction under current law")
                st.info(f"Premium tax credits decrease by ${difference:,.0f} per year (${difference/12:,.0f} per month) when enhanced PTCs expire.")
            else:
                st.success("### No Change in Credits")

            # Optional Chart - only generate when requested
            st.markdown("---")
            if st.button("📊 Show income comparison chart", help="Generate interactive charts showing how credits change across income levels"):
                with st.spinner("Generating charts..."):
                    fig_comparison, fig_delta = create_chart(ptc_2026_with_ira, ptc_2026_baseline, params['age_head'], params['age_spouse'],
                                     tuple(params['dependent_ages']), params['state'], params['income'], params['county'])

                    tab1, tab2 = st.tabs(["Comparison", "Difference"])

                    with tab1:
                        st.plotly_chart(fig_comparison, use_container_width=True)

                    with tab2:
                        st.plotly_chart(fig_delta, use_container_width=True)

            # Details
            with st.expander("See calculation details"):
                st.write(f"""
                ### Your Household
                - **Size:** {household_size} people
                - **Income:** ${params['income']:,} ({fpl_pct:.0f}% of FPL)
                - **2026 FPL for {household_size}:** ${get_fpl(household_size):,}
                - **Location:** {params['county'] + ', ' if params['county'] else ''}{params['state']}
                - **Second Lowest Cost Silver Plan:** ${slcsp_2026:,.0f} per year (${slcsp_2026/12:,.0f} per month)

                ### How Premium Tax Credits Work

                **Formula:** PTC = Benchmark Plan Cost - Your Required Contribution

                **Your Required Contribution** is a percentage of your income:
                - Lower percentages with IRA extension (2026): 0-8.5% based on income
                - Higher percentages without IRA (2026): 2-9.5% based on income
                - No credits at all above 400% FPL without IRA extension

                If the benchmark plan costs less than your required contribution, you get no credit.
                """)

def calculate_fpl_percentage(income, household_size):
    """Calculate income as percentage of Federal Poverty Level"""
    fpl = get_fpl(household_size)
    return (income / fpl) * 100

def get_fpl(household_size):
    """Get Federal Poverty Level for household size"""
    fpl_base = {
        1: 15570,
        2: 21130, 
        3: 26650,
        4: 32200,
        5: 37750,
        6: 43300,
        7: 48850,
        8: 54400,
    }
    
    if household_size <= 8:
        return fpl_base[household_size]
    else:
        return fpl_base[8] + (household_size - 8) * 5550

def calculate_ptc(age_head, age_spouse, income, dependent_ages, state, county_name=None, use_reform=False):
    """Calculate PTC for baseline or IRA enhanced scenario using 2026 comparison

    Matches notebook pattern exactly - uses copy.deepcopy pattern with income injection

    Args:
        county_name: County name from dropdown (e.g. "Travis County")
                    Will be converted to PolicyEngine format (TRAVIS_COUNTY_TX)
    """
    import copy
    try:
        # Build base household situation (matches notebook structure exactly)
        situation = {
            "people": {
                "you": {"age": {2026: age_head}}
            },
            "families": {"your family": {"members": ["you"]}},
            "spm_units": {"your household": {"members": ["you"]}},
            "tax_units": {"your tax unit": {"members": ["you"]}},
            "households": {
                "your household": {
                    "members": ["you"],
                    "state_name": {2026: state}
                }
            }
        }

        # Add county if provided - convert to PolicyEngine format
        if county_name:
            # Convert "Travis County" -> "TRAVIS_COUNTY_TX"
            county_pe_format = county_name.upper().replace(' ', '_') + '_' + state
            situation["households"]["your household"]["county"] = {2026: county_pe_format}

        # Add spouse if married
        if age_spouse:
            situation["people"]["your partner"] = {"age": {2026: age_spouse}}
            situation["families"]["your family"]["members"].append("your partner")
            situation["spm_units"]["your household"]["members"].append("your partner")
            situation["tax_units"]["your tax unit"]["members"].append("your partner")
            situation["households"]["your household"]["members"].append("your partner")
            situation["marital_units"] = {"your marital unit": {"members": ["you", "your partner"]}}

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
            situation["spm_units"]["your household"]["members"].append(child_id)
            situation["tax_units"]["your tax unit"]["members"].append(child_id)
            situation["households"]["your household"]["members"].append(child_id)

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
            sit["people"]["your partner"]["employment_income"] = {2026: income / 2}
        else:
            sit["people"]["you"]["employment_income"] = {2026: income}

        # Create reform if requested (exact same as notebook)
        reform = None
        if use_reform:
            from policyengine_core.reforms import Reform
            reform = Reform.from_dict({
                "gov.aca.ptc_phase_out_rate[0].amount": {"2026-01-01.2100-12-31": 0},
                "gov.aca.ptc_phase_out_rate[1].amount": {"2025-01-01.2100-12-31": 0},
                "gov.aca.ptc_phase_out_rate[2].amount": {"2026-01-01.2100-12-31": 0},
                "gov.aca.ptc_phase_out_rate[3].amount": {"2026-01-01.2100-12-31": 0.02},
                "gov.aca.ptc_phase_out_rate[4].amount": {"2026-01-01.2100-12-31": 0.04},
                "gov.aca.ptc_phase_out_rate[5].amount": {"2026-01-01.2100-12-31": 0.06},
                "gov.aca.ptc_phase_out_rate[6].amount": {"2026-01-01.2100-12-31": 0.085},
                "gov.aca.ptc_income_eligibility[2].amount": {"2026-01-01.2100-12-31": True}
            }, country_id="us")

        # Run simulation
        sim = Simulation(situation=sit, reform=reform)

        ptc = sim.calculate("aca_ptc", map_to="household", period=2026)[0]
        slcsp = sim.calculate("slcsp", map_to="household", period=2026)[0]

        return float(max(0, ptc)), float(slcsp)

    except Exception as e:
        st.error(f"Calculation error: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return 0, 0

def create_chart(ptc_with_ira, ptc_baseline, age_head, age_spouse, dependent_ages, state, income, county=None):
    """Create income curve charts showing PTC across income range with user's position marked

    Returns tuple of (comparison_fig, delta_fig)

    Note: Caching removed to prevent signature mismatch issues on Streamlit Cloud
    """

    # Create base household structure for income sweep
    base_household = {
        "people": {
            "you": {"age": {2026: age_head}}
        },
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: state}
            }
        },
        "axes": [
            [
                {
                    "name": "employment_income",
                    "count": 1001,  # 1001 points for exact 1k increments (0 to 1M)
                    "min": 0,
                    "max": 1000000
                }
            ]
        ]
    }
    
    # Add county if provided
    if county:
        county_pe_format = county.upper().replace(' ', '_') + '_' + state
        base_household["households"]["your household"]["county"] = {2026: county_pe_format}

    # Add spouse if married
    if age_spouse:
        base_household["people"]["your partner"] = {"age": {2026: age_spouse}}
        base_household["families"]["your family"]["members"].append("your partner")
        base_household["spm_units"]["your household"]["members"].append("your partner")
        base_household["tax_units"]["your tax unit"]["members"].append("your partner")
        base_household["households"]["your household"]["members"].append("your partner")
        base_household["marital_units"] = {"your marital unit": {"members": ["you", "your partner"]}}

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

        # Add child's marital unit
        if "marital_units" not in base_household:
            base_household["marital_units"] = {}
        base_household["marital_units"][f"{child_id}'s marital unit"] = {
            "members": [child_id]
        }

    try:
        # Create reform for chart calculation
        from policyengine_core.reforms import Reform
        reform = Reform.from_dict({
            "gov.aca.ptc_phase_out_rate[0].amount": {"2026-01-01.2100-12-31": 0},
            "gov.aca.ptc_phase_out_rate[1].amount": {"2025-01-01.2100-12-31": 0},
            "gov.aca.ptc_phase_out_rate[2].amount": {"2026-01-01.2100-12-31": 0},
            "gov.aca.ptc_phase_out_rate[3].amount": {"2026-01-01.2100-12-31": 0.02},
            "gov.aca.ptc_phase_out_rate[4].amount": {"2026-01-01.2100-12-31": 0.04},
            "gov.aca.ptc_phase_out_rate[5].amount": {"2026-01-01.2100-12-31": 0.06},
            "gov.aca.ptc_phase_out_rate[6].amount": {"2026-01-01.2100-12-31": 0.085},
            "gov.aca.ptc_income_eligibility[2].amount": {"2026-01-01.2100-12-31": True}
        }, country_id="us")
        
        # Calculate both curves - baseline and reform for 2026
        sim_baseline = Simulation(situation=base_household)
        sim_reform = Simulation(situation=base_household, reform=reform)

        income_range = sim_baseline.calculate("employment_income", map_to="household", period=2026)
        ptc_range_baseline = sim_baseline.calculate("aca_ptc", map_to="household", period=2026)
        ptc_range_reform = sim_reform.calculate("aca_ptc", map_to="household", period=2026)

        # Calculate Medicaid and CHIP values
        medicaid_range = sim_baseline.calculate("medicaid_cost", map_to="household", period=2026)
        chip_range = sim_baseline.calculate("per_capita_chip", map_to="household", period=2026)

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

            # Check if eligible for Medicaid or CHIP
            if medicaid > 0:
                text += f"<b>Medicaid eligible</b><br>Estimated value: ${medicaid:,.0f}/year<br>"
            elif chip > 0:
                text += f"<b>CHIP eligible</b><br>Estimated value: ${chip:,.0f}/year<br>"
            else:
                # Show PTC information
                text += f"<b>PTC (current law):</b> ${ptc_base:,.0f}/year<br>"
                text += f"<b>PTC (extended):</b> ${ptc_ref:,.0f}/year<br>"
                if delta > 0:
                    text += f"<b>Difference:</b> -${delta:,.0f}/year"
                elif delta < 0:
                    text += f"<b>Difference:</b> +${abs(delta):,.0f}/year"
                else:
                    text += f"<b>Difference:</b> $0"

            hover_text.append(text)

        # Create the plot
        fig = go.Figure()

        # Add invisible hover trace with unified information
        fig.add_trace(go.Scatter(
            x=income_range,
            y=np.maximum.reduce([medicaid_range, chip_range, ptc_range_baseline, ptc_range_reform]),
            mode='lines',
            line=dict(width=0),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False,
            name=''
        ))

        # Add Medicaid line
        fig.add_trace(go.Scatter(
            x=income_range,
            y=medicaid_range,
            mode='lines',
            name='Medicaid',
            line=dict(color=COLORS['green'], width=3),
            hoverinfo='skip',
            visible=True
        ))

        # Add Children's Health Insurance Program (CHIP) line
        fig.add_trace(go.Scatter(
            x=income_range,
            y=chip_range,
            mode='lines',
            name="Children's Health Insurance Program (CHIP)",
            line=dict(color=COLORS['secondary'], width=3),
            hoverinfo='skip',
            visible=True
        ))

        # Add baseline line (current law) - show first in legend
        fig.add_trace(go.Scatter(
            x=income_range,
            y=ptc_range_baseline,
            mode='lines',
            name='PTC (current law)',
            line=dict(color=COLORS['gray'], width=3),
            hoverinfo='skip'
        ))

        # Add reform line (enhanced PTCs extended)
        fig.add_trace(go.Scatter(
            x=income_range,
            y=ptc_range_reform,
            mode='lines',
            name='PTC (enhanced PTCs extended)',
            line=dict(color=COLORS['primary'], width=3),
            hoverinfo='skip'
        ))
        
        # Add user's position markers
        fig.add_trace(go.Scatter(
            x=[income, income],
            y=[ptc_baseline, ptc_with_ira],
            mode='markers',
            name='Your Household',
            marker=dict(
                color=[COLORS['gray'], COLORS['primary']],
                size=12,
                symbol='diamond',
                line=dict(width=2, color='white')
            ),
            hoverinfo='skip',
            showlegend=False
        ))

        # Add annotations for user's points (only if income > 0 to avoid cramping y-axis)
        if income > 10000:
            fig.add_annotation(
                x=income,
                y=ptc_baseline,
                text=f"Current law: ${ptc_baseline:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=COLORS['gray'],
                ax=60,
                ay=40,
                bgcolor='white',
                bordercolor=COLORS['gray'],
                borderwidth=2
            )

            fig.add_annotation(
                x=income,
                y=ptc_with_ira,
                text=f"Extended: ${ptc_with_ira:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=COLORS['primary'],
                ax=60,
                ay=-40,
                bgcolor='white',
                bordercolor=COLORS['primary'],
                borderwidth=2
            )
        
        # Update layout for comparison chart
        fig.update_layout(
            title={
                "text": "Healthcare assistance by household income",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Annual healthcare assistance value",
            height=500,
            xaxis=dict(tickformat='$,.0f', range=[0, x_axis_max], automargin=True),
            yaxis=dict(tickformat='$,.0f', rangemode='tozero', automargin=True),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Roboto, sans-serif'),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=80, r=40, t=60, b=60),
            **add_logo_to_layout()
        )

        # Create delta chart
        fig_delta = go.Figure()

        user_difference = ptc_with_ira - ptc_baseline

        # Create hover text for delta chart
        delta_hover_text = []
        for i in range(len(income_range)):
            inc = income_range[i]
            delta = delta_range[i]
            medicaid = medicaid_range[i]
            chip = chip_range[i]

            text = f"<b>Income: ${inc:,.0f}</b><br><br>"

            # Check if eligible for Medicaid or CHIP
            if medicaid > 0:
                text += f"<b>Medicaid eligible</b><br>Premium tax credits not applicable"
            elif chip > 0:
                text += f"<b>CHIP eligible</b><br>Premium tax credits not applicable"
            else:
                # Show gain from extension
                if delta > 0:
                    text += f"<b>Gain from extension:</b> ${delta:,.0f}/year"
                elif delta < 0:
                    text += f"<b>Loss from extension:</b> -${abs(delta):,.0f}/year"
                else:
                    text += f"<b>No change</b>"

            delta_hover_text.append(text)

        # Add delta line
        fig_delta.add_trace(go.Scatter(
            x=income_range,
            y=delta_range,
            mode='lines',
            name='PTC gain from extension',
            line=dict(color=COLORS['primary'], width=3),
            fill='tozeroy',
            fillcolor=f"rgba(44, 100, 150, 0.2)",
            hovertext=delta_hover_text,
            hoverinfo='text'
        ))

        # Add user's position marker
        if income > 10000:
            fig_delta.add_trace(go.Scatter(
                x=[income],
                y=[user_difference],
                mode='markers',
                name='Your household',
                marker=dict(
                    color=COLORS['primary'],
                    size=12,
                    symbol='diamond',
                    line=dict(width=2, color='white')
                ),
                hoverinfo='skip',
                showlegend=False
            ))

            fig_delta.add_annotation(
                x=income,
                y=user_difference,
                text=f"You: ${user_difference:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=COLORS['primary'],
                ax=60,
                ay=-40,
                bgcolor='white',
                bordercolor=COLORS['primary'],
                borderwidth=2
            )

        fig_delta.update_layout(
            title={
                "text": "PTC gain from extending enhanced subsidies",
                "font": {"size": 20, "color": COLORS["primary"]},
            },
            xaxis_title="Annual household income",
            yaxis_title="Annual PTC gain (extended - current law)",
            height=500,
            xaxis=dict(tickformat='$,.0f', range=[0, x_axis_max], automargin=True),
            yaxis=dict(tickformat='$,.0f', rangemode='tozero', automargin=True),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Roboto, sans-serif'),
            showlegend=False,
            margin=dict(l=80, r=40, t=60, b=60),
            **add_logo_to_layout()
        )

        return fig, fig_delta
        
    except Exception as e:
        # Fallback to simple bar charts if curve fails
        colors = [COLORS['gray'], COLORS['primary']]

        # Comparison bar chart
        fig_comp = go.Figure(data=[
            go.Bar(
                x=['Current law', 'Enhanced PTCs<br>extended'],
                y=[ptc_baseline, ptc_with_ira],
                text=[f'${ptc_baseline:,.0f}', f'${ptc_with_ira:,.0f}'],
                textposition='outside',
                marker_color=colors
            )
        ])

        fig_comp.update_layout(
            title="Annual premium tax credit comparison",
            yaxis_title="Credit amount ($)",
            height=400,
            showlegend=False,
            yaxis=dict(rangemode='tozero'),
            plot_bgcolor='white',
            **add_logo_to_layout()
        )

        # Delta bar chart
        user_difference = ptc_with_ira - ptc_baseline
        fig_delta = go.Figure(data=[
            go.Bar(
                x=['PTC gain from<br>extending enhanced subsidies'],
                y=[user_difference],
                text=[f'${user_difference:,.0f}'],
                textposition='outside',
                marker_color=COLORS['primary']
            )
        ])

        fig_delta.update_layout(
            title="PTC gain from extending enhanced subsidies",
            yaxis_title="Gain ($)",
            height=400,
            showlegend=False,
            yaxis=dict(rangemode='tozero'),
            plot_bgcolor='white',
            **add_logo_to_layout()
        )

        return fig_comp, fig_delta

if __name__ == "__main__":
    main()