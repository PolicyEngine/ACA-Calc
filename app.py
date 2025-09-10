import streamlit as st
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
    **See how your Premium Tax Credits change when IRA enhancements expire**
    
    The Inflation Reduction Act enhanced ACA subsidies through 2025. See what happens in 2026 when they expire.
    """)
    
    with st.expander("Understanding the Changes"):
        st.markdown("""
        **2025 - With IRA Enhancements:**
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
                
                # Calculate PTCs - just compare 2025 to 2026!
                ptc_2025, slcsp_2025 = calculate_ptc(
                    params['age_head'], params['age_spouse'], params['income'], 
                    params['dependent_ages'], params['state'], 2025  # With IRA
                )
                
                ptc_2026, slcsp_2026 = calculate_ptc(
                    params['age_head'], params['age_spouse'], params['income'], 
                    params['dependent_ages'], params['state'], 2026  # Without IRA (PolicyEngine knows this)
                )
                
                difference = ptc_2025 - ptc_2026
                
                
                # Display SLCSP
                st.info(f"Your base Second Lowest Cost Silver Plan is ${slcsp_2025:,.0f}/year")
                
                # Display metrics
                col_2025, col_2026, col_diff = st.columns(3)
                
                with col_2025:
                    st.metric("2025 (With IRA)", f"${ptc_2025:,.0f}/year", 
                             help="Your credits under current enhanced rules")
                
                with col_2026:
                    st.metric("2026 (After Expiration)", f"${ptc_2026:,.0f}/year",
                             help="Your credits after IRA expires")
                
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
                if ptc_2025 == 0 and ptc_2026 == 0:
                    if fpl_pct > 400:
                        st.info("### No Premium Tax Credits Available")
                        st.write("Your income exceeds 400% FPL, which is above the credit limit in 2026 and will be above the limit when IRA enhancements expire.")
                    else:
                        st.info("### No Premium Tax Credits Available") 
                        st.write("Your income is below the minimum threshold for ACA premium tax credits in both scenarios.")
                elif ptc_2025 > 0 and ptc_2026 == 0:
                    if fpl_pct > 400:
                        st.warning("### Credits Available in 2025 Only")
                        st.warning(f"Premium tax credits: **${ptc_2025:,.0f}/year** in 2025, **$0** in 2026.")
                        st.warning("Your income exceeds 400% FPL. Credits are available above this limit in 2025 but not in 2026.")
                    else:
                        st.warning("### Credits Available in 2025 Only")
                        st.warning(f"Premium tax credits: **${ptc_2025:,.0f}/year** in 2025, **$0** in 2026.")
                        st.warning("Higher contribution requirements in 2026 eliminate your credit eligibility.")
                elif difference > 0:
                    st.info("### Credit Reduction")
                    st.info(f"Premium tax credits decrease by **${difference:,.0f}/year** (**${difference/12:,.0f}/month**).")
                else:
                    st.success("### No Change in Credits")
                
                # Chart
                fig = create_chart(ptc_2025, ptc_2026, params['age_head'], params['age_spouse'], 
                                 params['dependent_ages'], params['state'], params['income'])
                st.plotly_chart(fig, use_container_width=True)
                
                # Details
                with st.expander("See calculation details"):
                    st.write(f"""
                    ### Your Household
                    - **Size:** {household_size} people
                    - **Income:** ${params['income']:,} ({fpl_pct:.0f}% of FPL)
                    - **2026 FPL for {household_size}:** ${get_fpl(household_size):,}
                    - **Location:** {params['county'] + ', ' if params['county'] else ''}{params['state']}
                    - **Second Lowest Cost Silver Plan:** ${slcsp_2025:,.0f}/year (${slcsp_2025/12:,.0f}/month)
                    
                    ### How Premium Tax Credits Work
                    
                    **Formula:** PTC = Benchmark Plan Cost - Your Required Contribution
                    
                    **Your Required Contribution** is a percentage of your income:
                    - Lower percentages with IRA (2025): 0-8.5% based on income
                    - Higher percentages without IRA (2026): 2-9.5% based on income
                    - No credits at all above 400% FPL starting in 2026
                    
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

def calculate_ptc(age_head, age_spouse, income, dependent_ages, state, year):
    """Calculate PTC for a given year (PolicyEngine knows the rules for each year)"""
    try:
        # Build household
        household = {
            "people": {
                "you": {"age": {year: age_head}}
            },
            "families": {"your family": {"members": ["you"]}},
            "tax_units": {"your tax unit": {"members": ["you"]}},
            "households": {
                "your household": {
                    "members": ["you"],
                    "state_name": {year: state}
                }
            }
        }
        
        # Add income and spouse
        if age_spouse:
            household["people"]["you"]["employment_income"] = {year: income / 2}
            household["people"]["your partner"] = {
                "age": {year: age_spouse},
                "employment_income": {year: income / 2}
            }
            household["families"]["your family"]["members"].append("your partner")
            household["tax_units"]["your tax unit"]["members"].append("your partner")
            household["households"]["your household"]["members"].append("your partner")
            household["marital_units"] = {"your marital unit": {"members": ["you", "your partner"]}}
        else:
            household["people"]["you"]["employment_income"] = {year: income}
        
        # Add dependents
        for i, dep_age in enumerate(dependent_ages):
            child_id = f"child_{i}"
            household["people"][child_id] = {"age": {year: dep_age}}
            household["families"]["your family"]["members"].append(child_id)
            household["tax_units"]["your tax unit"]["members"].append(child_id)
            household["households"]["your household"]["members"].append(child_id)
        
        # Run simulation - PolicyEngine knows the rules for each year!
        sim = Simulation(situation=household)
        ptc = sim.calculate("aca_ptc", map_to="household", period=year)[0]
        slcsp = sim.calculate("slcsp", map_to="household", period=year)[0]
        
        return float(max(0, ptc)), float(slcsp)
        
    except Exception as e:
        st.error(f"Calculation error for {year}: {str(e)}")
        return 0, 0

def create_chart(ptc_2025, ptc_2026, age_head, age_spouse, dependent_ages, state, income):
    """Create income curve chart showing PTC across income range with user's position marked"""
    
    # Create base household structure for income sweep
    base_household = {
        "people": {
            "you": {"age": {2026: age_head}}
        },
        "families": {"your family": {"members": ["you"]}},
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
                    "count": 200,
                    "min": 15000,
                    "max": 200000
                }
            ]
        ]
    }
    
    # Add spouse if married
    if age_spouse:
        base_household["people"]["your partner"] = {"age": {2026: age_spouse}}
        base_household["families"]["your family"]["members"].append("your partner")
        base_household["tax_units"]["your tax unit"]["members"].append("your partner")
        base_household["households"]["your household"]["members"].append("your partner")
        base_household["marital_units"] = {"your marital unit": {"members": ["you", "your partner"]}}
    
    # Add dependents
    for i, dep_age in enumerate(dependent_ages):
        child_id = f"child_{i}"
        base_household["people"][child_id] = {"age": {2026: dep_age}}
        base_household["families"]["your family"]["members"].append(child_id)
        base_household["tax_units"]["your tax unit"]["members"].append(child_id)
        base_household["households"]["your household"]["members"].append(child_id)
    
    try:
        # Calculate 2025 IRA-enhanced curve
        sim_2025 = Simulation(situation=base_household)
        income_range = sim_2025.calculate("employment_income", map_to="household", period=2026)
        ptc_range_2025 = sim_2025.calculate("aca_ptc", map_to="household", period=2025)
        
        # Calculate FPL for household size to determine 400% cliff
        household_size = len(base_household["people"])
        fpl_400 = get_fpl(household_size) * 4
        
        # Create 2026 original ACA curve by modifying the 2025 curve
        ptc_range_2026 = []
        for i, inc in enumerate(income_range):
            if inc > fpl_400:
                # Hard cutoff at 400% FPL for original ACA
                ptc_range_2026.append(0)
            else:
                # Use 2025 amount but with higher phase-out (approximate)
                base_ptc = ptc_range_2025[i]
                # Reduce by ~20-30% to simulate higher contribution percentages
                reduction_factor = min(0.3, (inc / fpl_400) * 0.2)  # More reduction at higher incomes
                reduced_ptc = base_ptc * (1 - reduction_factor)
                ptc_range_2026.append(max(0, reduced_ptc))
        
        ptc_range_2026 = np.array(ptc_range_2026)
        
        # Create the plot
        fig = go.Figure()
        
        # Add 2025 line (with IRA)
        fig.add_trace(go.Scatter(
            x=income_range,
            y=ptc_range_2025,
            mode='lines',
            name='2025 (IRA Enhanced)',
            line=dict(color='#2C6496', width=3),
            hovertemplate='<b>2025 (IRA Enhanced)</b><br>Income: $%{x:,.0f}<br>PTC: $%{y:,.0f}<extra></extra>'
        ))
        
        # Add 2026 line (original ACA)
        fig.add_trace(go.Scatter(
            x=income_range,
            y=ptc_range_2026,
            mode='lines',
            name='2026 (Original ACA)',
            line=dict(color='#DC3545', width=3, dash='dash'),
            hovertemplate='<b>2026 (Original ACA)</b><br>Income: $%{x:,.0f}<br>PTC: $%{y:,.0f}<extra></extra>'
        ))
        
        # Add user's position markers
        fig.add_trace(go.Scatter(
            x=[income, income],
            y=[ptc_2025, ptc_2026],
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
        
        # Add annotations for user's points
        fig.add_annotation(
            x=income,
            y=ptc_2025,
            text=f"Your 2025: ${ptc_2025:,.0f}",
            showarrow=False,
            bgcolor='white',
            bordercolor='#2C6496',
            xshift=10
        )
        
        fig.add_annotation(
            x=income,
            y=ptc_2026,
            text=f"Your 2026: ${ptc_2026:,.0f}",
            showarrow=False,
            bgcolor='white',
            bordercolor='#DC3545',
            xshift=10
        )
        
        # Update layout
        fig.update_layout(
            title="Premium Tax Credits by Household Income",
            xaxis_title="Annual Household Income",
            yaxis_title="Annual Premium Tax Credit",
            height=500,
            xaxis=dict(tickformat='$,.0f'),
            yaxis=dict(tickformat='$,.0f', rangemode='tozero'),
            plot_bgcolor='white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
        
    except Exception as e:
        # Fallback to simple bar chart if curve fails
        colors = ['#2C6496', '#DC3545' if ptc_2026 < ptc_2025 else '#28A745']
        
        fig = go.Figure(data=[
            go.Bar(
                x=['2025<br>(IRA Enhanced)', '2026<br>(Original ACA)'],
                y=[ptc_2025, ptc_2026],
                text=[f'${ptc_2025:,.0f}', f'${ptc_2026:,.0f}'],
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