"""
ACA Premium Tax Credit Calculator
==================================
Compare 2026 premium tax credits with and without IRA enhancements.

This app calculates ACA premium tax credits under two scenarios:
1. Baseline: Original ACA rules (after IRA expires)
2. Reform: With IRA enhancements extended to 2026

Uses PolicyEngine US for accurate tax-benefit microsimulation.
"""

import streamlit as st

try:
    import pandas as pd
    import numpy as np
    import json
    from policyengine_us import Simulation
    import plotly.graph_objects as go

    # Try to import reform capability
    try:
        from policyengine_core.reforms import Reform
        REFORM_AVAILABLE = True
    except ImportError:
        REFORM_AVAILABLE = False

    st.set_page_config(
        page_title="ACA Premium Tax Credit Calculator",
        layout="wide",
        initial_sidebar_state="expanded"
    )

except Exception as e:
    st.error(f"Startup Error: {str(e)}")
    st.error("Please report this error with the details above.")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

# Load counties from PolicyEngine data
@st.cache_data
def load_counties():
    try:
        with open('counties.json', 'r') as f:
            return json.load(f)
    except:
        return None

def main():
    st.title("ACA Premium Tax Credit Calculator")
    st.markdown("""
    **Compare 2026 Premium Tax Credits with and without IRA enhancements**
    
    The Inflation Reduction Act enhanced ACA subsidies through 2025. Compare what your credits would be in 2026 with and without extending these enhancements.
    """)
    
    with st.expander("Understanding the Changes"):
        st.markdown("""
        **2026 - With IRA Enhancements Extended:**
        - No income cap - households above 400% FPL can still get credits
        - Lower premium contribution percentages (0-8.5% of income)
        - More generous subsidies at all income levels
        
        **2026 - After IRA Expires (Original ACA):**
        - Hard cap at 400% FPL - no credits above this level (the "cliff")
        - Higher contribution percentages (2-9.5% of income)
        - Less generous subsidies, especially for middle incomes
        """)
    
    counties = load_counties()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Your Information")
        
        st.subheader("Household")
        
        marital_status = st.selectbox(
            "Filing Status",
            ["Single", "Married filing jointly", "Head of household"]
        )
        
        age_head = st.number_input("Your Age", min_value=18, max_value=100, value=35)
        
        if marital_status == "Married filing jointly":
            age_spouse = st.number_input("Spouse's Age", min_value=18, max_value=100, value=35)
        else:
            age_spouse = None
        
        num_dependents = st.number_input("Number of Children/Dependents", min_value=0, max_value=10, value=0)
        dependent_ages = []
        
        if num_dependents > 0:
            st.write("Ages of dependents:")
            cols = st.columns(min(3, max(1, num_dependents)))
            for i in range(num_dependents):
                with cols[i % len(cols)]:
                    age_dep = st.number_input(f"Child {i+1}", min_value=0, max_value=25, value=10, key=f"dep_{i}")
                    dependent_ages.append(age_dep)
        
        st.subheader("Income")
        income = st.number_input(
            "Annual Household Income ($)", 
            min_value=0, 
            value=63450,  # Default to 300% FPL for couple
            step=1000,
            help="Total household income from all sources"
        )
        
        st.subheader("Location")
        
        states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", 
                 "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
                 "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", 
                 "VA", "WA", "WV", "WI", "WY", "DC"]
        
        state = st.selectbox("State", states, index=states.index("TX"))
        
        # County selection if available
        county = None
        if counties and state in counties:
            county = st.selectbox(
                "County (optional)",
                [""] + counties[state],
                help="Select your county for more accurate calculations"
            )
            if county == "":
                county = None
        
        if st.button("Calculate Premium Tax Credits", type="primary", use_container_width=True):
            st.session_state.calculate = True
            st.session_state.params = {
                'age_head': age_head,
                'age_spouse': age_spouse,
                'income': income,
                'dependent_ages': dependent_ages,
                'state': state,
                'county': county,
                'marital_status': marital_status
            }
    
    with col2:
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
                    st.info(f"Your base Second Lowest Cost Silver Plan is ${slcsp_2026:,.0f}/year (${slcsp_2026/12:,.0f}/month)")
                
                # Display metrics with custom CSS to prevent truncation
                st.markdown("""
                <style>
                [data-testid="stMetricValue"] {
                    font-size: 1.5rem !important;
                    white-space: nowrap !important;
                    overflow: visible !important;
                }
                </style>
                """, unsafe_allow_html=True)

                col_with_ira, col_baseline, col_diff = st.columns(3)

                with col_with_ira:
                    st.metric("2026 (With IRA)", f"${ptc_2026_with_ira:,.0f}/year",
                             help="Your credits if IRA enhancements were extended")

                with col_baseline:
                    st.metric("2026 (After Expiration)", f"${ptc_2026_baseline:,.0f}/year",
                             help="Your credits after IRA expires (original ACA)")

                with col_diff:
                    if difference > 0:
                        st.metric("You Lose", f"${difference:,.0f}/year",
                                 f"-${difference/12:,.0f}/month", delta_color="inverse")
                    elif difference < 0:
                        # This shouldn't happen but just in case
                        st.metric("You Gain?", f"${abs(difference):,.0f}/year",
                                 f"+${abs(difference)/12:,.0f}/month", delta_color="normal")
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
                        st.warning("### Credits Available Only With IRA Extension")
                        st.warning(f"Premium tax credits: ${ptc_2026_with_ira:,.0f}/year with IRA extension, $0 without.")
                        st.warning("Your income exceeds 400% FPL. Credits are available above this limit with IRA enhancements but not without.")
                    else:
                        st.warning("### Credits Available Only With IRA Extension")
                        st.warning(f"Premium tax credits: ${ptc_2026_with_ira:,.0f}/year with IRA extension, $0 without.")
                        st.warning("Higher contribution requirements without IRA eliminate your credit eligibility.")
                elif difference > 0:
                    st.info("### Credit Reduction")
                    st.info(f"Premium tax credits decrease by ${difference:,.0f}/year (${difference/12:,.0f}/month) when IRA enhancements expire.")
                else:
                    st.success("### No Change in Credits")

                # Optional Chart - only generate when requested
                st.markdown("---")
                if st.button("📊 Show Income Comparison Chart", help="Generate an interactive chart showing how credits change across income levels"):
                    with st.spinner("Generating chart..."):
                        fig = create_chart(ptc_2026_with_ira, ptc_2026_baseline, params['age_head'], params['age_spouse'],
                                         tuple(params['dependent_ages']), params['state'], params['income'], params['county'])
                        st.plotly_chart(fig, use_container_width=True)

                # Details
                with st.expander("See calculation details"):
                    st.write(f"""
                    ### Your Household
                    - **Size:** {household_size} people
                    - **Income:** ${params['income']:,} ({fpl_pct:.0f}% of FPL)
                    - **2026 FPL for {household_size}:** ${get_fpl(household_size):,}
                    - **Location:** {params['county'] + ', ' if params['county'] else ''}{params['state']}
                    - **Second Lowest Cost Silver Plan:** ${slcsp_2026:,.0f}/year (${slcsp_2026/12:,.0f}/month)
                    
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
                "members": [child_id],
                "marital_unit_id": {2026: i + 1}  # Sequential IDs: 1, 2, 3, ...
            }

        # Deep copy and inject income (matches notebook pattern)
        sit = copy.deepcopy(situation)

        # Split income between adults if married, otherwise single person gets all
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
    """Create income curve chart showing PTC across income range with user's position marked

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
                    "count": 50,  # Reduced for memory optimization
                    "min": 0,
                    "max": 200000
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
            "members": [child_id],
            "marital_unit_id": {2026: i + 1}  # Sequential IDs
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

        # Create the plot
        fig = go.Figure()

        # Add Medicaid line
        fig.add_trace(go.Scatter(
            x=income_range,
            y=medicaid_range,
            mode='lines',
            name='Medicaid',
            line=dict(color='#28A745', width=3, dash='dot'),
            hovertemplate='<b>Medicaid</b><br>Income: $%{x:,.0f}<br>Value: $%{y:,.0f}<extra></extra>',
            visible=True
        ))

        # Add CHIP line
        fig.add_trace(go.Scatter(
            x=income_range,
            y=chip_range,
            mode='lines',
            name='CHIP',
            line=dict(color='#FFC107', width=3, dash='dot'),
            hovertemplate='<b>CHIP</b><br>Income: $%{x:,.0f}<br>Value: $%{y:,.0f}<extra></extra>',
            visible=True
        ))

        # Add reform line (with IRA extension)
        fig.add_trace(go.Scatter(
            x=income_range,
            y=ptc_range_reform,
            mode='lines',
            name='PTC (With IRA)',
            line=dict(color='#2C6496', width=3),
            hovertemplate='<b>PTC (With IRA Extension)</b><br>Income: $%{x:,.0f}<br>PTC: $%{y:,.0f}<extra></extra>'
        ))

        # Add baseline line (original ACA)
        fig.add_trace(go.Scatter(
            x=income_range,
            y=ptc_range_baseline,
            mode='lines',
            name='PTC (After IRA Expires)',
            line=dict(color='#DC3545', width=3, dash='dash'),
            hovertemplate='<b>PTC (After IRA Expires)</b><br>Income: $%{x:,.0f}<br>PTC: $%{y:,.0f}<extra></extra>'
        ))
        
        # Add user's position markers
        fig.add_trace(go.Scatter(
            x=[income, income],
            y=[ptc_with_ira, ptc_baseline],
            mode='markers',
            name='Your Household',
            marker=dict(
                color=['#2C6496', '#DC3545'],
                size=12,
                symbol='diamond',
                line=dict(width=2, color='white')
            ),
            showlegend=False
        ))

        # Add annotations for user's points (only if income > 0 to avoid cramping y-axis)
        if income > 10000:
            fig.add_annotation(
                x=income,
                y=ptc_with_ira,
                text=f"Your w/ IRA: ${ptc_with_ira:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor='#2C6496',
                ax=60,
                ay=-40,
                bgcolor='white',
                bordercolor='#2C6496',
                borderwidth=2
            )

            fig.add_annotation(
                x=income,
                y=ptc_baseline,
                text=f"Your baseline: ${ptc_baseline:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor='#DC3545',
                ax=60,
                ay=40,
                bgcolor='white',
                bordercolor='#DC3545',
                borderwidth=2
            )
        
        # Update layout
        fig.update_layout(
            title="Healthcare Assistance by Household Income",
            xaxis_title="Annual Household Income",
            yaxis_title="Annual Healthcare Assistance Value",
            height=500,
            xaxis=dict(tickformat='$,.0f', range=[0, 200000], automargin=True),
            yaxis=dict(tickformat='$,.0f', rangemode='tozero', automargin=True),
            plot_bgcolor='white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=80, r=40, t=60, b=60)
        )
        
        return fig
        
    except Exception as e:
        # Fallback to simple bar chart if curve fails
        colors = ['#2C6496', '#DC3545' if ptc_baseline < ptc_with_ira else '#28A745']
        
        fig = go.Figure(data=[
            go.Bar(
                x=['2026<br>(With IRA Extension)', '2026<br>(After IRA Expires)'],
                y=[ptc_with_ira, ptc_baseline],
                text=[f'${ptc_with_ira:,.0f}', f'${ptc_baseline:,.0f}'],
                textposition='outside',
                marker_color=colors
            )
        ])
        
        fig.update_layout(
            title="Annual Premium Tax Credit Comparison",
            yaxis_title="Credit Amount ($)",
            height=400,
            showlegend=False,
            yaxis=dict(rangemode='tozero'),
            plot_bgcolor='white'
        )
        
        return fig

if __name__ == "__main__":
    main()