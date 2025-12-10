"""
ACA Health Coverage Interactive Story
======================================
A scrollytelling experience explaining how ACA premium tax credits work
and how proposed reforms would affect different households.

Uses precomputed PolicyEngine US simulation data for instant loading.
"""

import streamlit as st
import numpy as np
import json
import os
from pathlib import Path
import plotly.graph_objects as go
import base64

st.set_page_config(
    page_title="Understanding ACA Health Coverage Reforms",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# Design Tokens (PolicyEngine App V2 Style)
# ============================================================================

COLORS = {
    # Primary brand - teal
    "primary": "#319795",
    "primary_light": "#4FD1C5",
    "primary_dark": "#285E61",

    # Secondary - gray scale
    "gray_50": "#F9FAFB",
    "gray_100": "#F2F4F7",
    "gray_200": "#E2E8F0",
    "gray_300": "#D1D5DB",
    "gray_400": "#9CA3AF",
    "gray_500": "#6B7280",
    "gray_600": "#4B5563",
    "gray_700": "#344054",
    "gray_800": "#1F2937",
    "gray_900": "#101828",

    # Semantic
    "success": "#22C55E",
    "warning": "#FEC601",
    "error": "#EF4444",

    # Chart colors
    "baseline": "#9CA3AF",  # Gray for baseline/current law
    "ira_reform": "#2C6496",  # Blue for IRA extension
    "bipartisan_reform": "#9467BD",  # Purple for 700% FPL
    "medicaid": "#319795",  # Teal for Medicaid
    "chip": "#38B2AC",  # Lighter teal for CHIP

    # Text
    "text_primary": "#000000",
    "text_secondary": "#5A5A5A",

    # Background
    "bg_primary": "#FFFFFF",
    "bg_secondary": "#F5F9FF",
}

FONTS = {
    "primary": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "body": "Roboto, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
}

# ============================================================================
# Preset Households
# ============================================================================

PRESET_HOUSEHOLDS = {
    "tampa_family": {
        "name": "Tampa Family of 4",
        "description": "Two parents (age 40) with two children (ages 10 and 8) in Florida",
        "age_head": 40,
        "age_spouse": 40,
        "dependent_ages": [10, 8],
        "state": "FL",
        "county": "Hillsborough County",
        "is_expansion_state": False,
        "key_insight": "Florida didn't expand Medicaid, creating a coverage gap for parents between 32% and 100% FPL.",
    },
    "california_couple": {
        "name": "California Couple",
        "description": "An older couple (ages 64 and 62) in San Benito County, California",
        "age_head": 64,
        "age_spouse": 62,
        "dependent_ages": [],
        "state": "CA",
        "county": "San Benito County",
        "is_expansion_state": True,
        "key_insight": "This older couple faces high premiums due to age-based rating, making subsidies especially valuable.",
    },
    "texas_single": {
        "name": "Single Adult in Texas",
        "description": "A single 35-year-old in Harris County, Texas",
        "age_head": 35,
        "age_spouse": None,
        "dependent_ages": [],
        "state": "TX",
        "county": "Harris County",
        "is_expansion_state": False,
        "key_insight": "Texas didn't expand Medicaid. Single adults below 100% FPL fall into the coverage gap with no affordable options.",
    },
    "ny_family": {
        "name": "Young Family in New York",
        "description": "Two parents (ages 30 and 28) with a toddler (age 2) in New York City",
        "age_head": 30,
        "age_spouse": 28,
        "dependent_ages": [2],
        "state": "NY",
        "county": "New York County",
        "is_expansion_state": True,
        "key_insight": "New York expanded Medicaid, so this family has coverage options at lower incomes, but faces the 400% FPL cliff.",
    },
}

# ============================================================================
# Scroll Section Content
# ============================================================================

SCROLL_SECTIONS = [
    {
        "id": "intro",
        "title": "Health Coverage in America",
        "content": """
        Health insurance coverage in America is a patchwork of programs: **Medicaid** for low-income
        households, **CHIP** for children, and **marketplace plans** with premium tax credits (PTCs)
        for those who don't qualify for other coverage.

        The Affordable Care Act's premium tax credits help make marketplace coverage affordable, but
        they're set to change dramatically in 2026 when current enhancements expire.

        **Scroll to explore how these programs work and how proposed reforms would affect real families.**
        """,
        "chart_state": "all_programs",
        "highlight": None,
    },
    {
        "id": "medicaid",
        "title": "Medicaid: The Foundation",
        "content": """
        **Medicaid** provides free or low-cost coverage for low-income Americans. But eligibility
        varies dramatically by state.

        In **expansion states** (like California and New York), adults qualify up to **138% of the
        Federal Poverty Level (FPL)**.

        In **non-expansion states** (like Florida and Texas), parents may only qualify up to
        **~32% FPL**, and childless adults often don't qualify at all—regardless of how low
        their income is.

        This creates the infamous **"coverage gap"**: people too poor for subsidies but not
        poor enough for Medicaid.
        """,
        "chart_state": "medicaid_focus",
        "highlight": "medicaid",
    },
    {
        "id": "chip",
        "title": "CHIP: Children's Coverage",
        "content": """
        The **Children's Health Insurance Program (CHIP)** covers children in families with
        incomes too high for Medicaid but who can't afford private insurance.

        CHIP eligibility extends much higher than adult Medicaid—typically up to **200-300% FPL**
        depending on the state.

        This means in many families, children have coverage through CHIP while parents must
        find other options.
        """,
        "chart_state": "chip_focus",
        "highlight": "chip",
    },
    {
        "id": "ptc_basics",
        "title": "Premium Tax Credits: How They Work",
        "content": """
        **Premium Tax Credits** help pay for marketplace health insurance. The credit equals
        the difference between:

        - The cost of the **benchmark plan** (second-lowest-cost Silver plan in your area)
        - Your **required contribution** (a percentage of your income)

        The lower your income, the lower your required contribution percentage, and the
        larger your tax credit.

        Currently, PTCs are available from **100% to 400% FPL** under baseline law.
        """,
        "chart_state": "ptc_baseline",
        "highlight": "ptc_baseline",
    },
    {
        "id": "the_cliff",
        "title": "The 400% FPL Cliff",
        "content": """
        Under current law (after IRA enhancements expire), premium tax credits **completely
        disappear** at 400% of the Federal Poverty Level.

        This creates a brutal "**subsidy cliff**" where earning just one more dollar can cost
        a family **thousands** in lost subsidies.

        For a family of four, this cliff hits at around **$124,800** in 2026.

        Watch how the gray baseline line drops to zero—this is the cliff millions of
        Americans face.
        """,
        "chart_state": "cliff_focus",
        "highlight": "cliff",
    },
    {
        "id": "ira_extension",
        "title": "The IRA Extension",
        "content": """
        The **Inflation Reduction Act** enhanced premium tax credits through 2025, but these
        enhancements are set to expire.

        **Extending the IRA subsidies** would:

        - **Eliminate the 400% FPL cliff** entirely
        - **Cap contributions at 8.5%** of income for everyone
        - Provide credits to households **at any income level** above 400% FPL

        The **blue line** shows how much more generous this is compared to baseline.
        """,
        "chart_state": "ira_reform",
        "highlight": "ira",
    },
    {
        "id": "bipartisan_bill",
        "title": "The Bipartisan Health Insurance Affordability Act",
        "content": """
        A bipartisan group of lawmakers has proposed an alternative: the **Bipartisan Health
        Insurance Affordability Act**.

        This bill would:

        - Extend eligibility to **700% FPL** (not unlimited like IRA)
        - Use a different contribution schedule topping out at **9.25%**
        - Create a **gradual phase-out** rather than a cliff

        The **purple line** shows this alternative. It's less generous than the IRA extension
        at high incomes, but still far better than baseline.
        """,
        "chart_state": "both_reforms",
        "highlight": "bipartisan",
    },
    {
        "id": "impact",
        "title": "The Impact: Who Benefits?",
        "content": """
        Both reforms primarily benefit households in the **middle-income range**—those earning
        between 200% and 600% of FPL.

        For our example households:

        - **Younger families** see modest but meaningful gains
        - **Older households** (like our California couple) see the largest dollar benefits
          because their premiums are higher
        - **Everyone above 400% FPL** benefits from cliff elimination

        The chart now shows the **change in net income**—the total benefit from reform.
        """,
        "chart_state": "impact",
        "highlight": "impact",
    },
    {
        "id": "your_turn",
        "title": "See How It Affects You",
        "content": """
        Every household's situation is different. Your age, location, family size, and
        income all affect your premium tax credits.

        **Try our calculator** to see exactly how these reforms would affect your family:

        👉 [Open the ACA Calculator](/calc)

        Or explore the example households above to understand the patterns.
        """,
        "chart_state": "both_reforms",
        "highlight": None,
    },
]

# ============================================================================
# Data Loading Functions
# ============================================================================

# Path to precomputed household data
DATA_DIR = Path(__file__).parent / "data" / "households"


@st.cache_data
def load_household_data(household_key):
    """Load precomputed household data from JSON file.

    Data is precomputed by running: python precompute_households.py
    This avoids expensive PolicyEngine simulations on page load.
    """
    json_file = DATA_DIR / f"{household_key}.json"

    if json_file.exists():
        with open(json_file, "r") as f:
            return json.load(f)
    else:
        st.error(f"Precomputed data not found for {household_key}. Run `python precompute_households.py` to generate.")
        return None


@st.cache_data
def load_all_household_data():
    """Load all precomputed household data at once."""
    combined_file = DATA_DIR / "all_households.json"

    if combined_file.exists():
        with open(combined_file, "r") as f:
            return json.load(f)
    else:
        # Fall back to loading individual files
        all_data = {}
        for key in PRESET_HOUSEHOLDS.keys():
            data = load_household_data(key)
            if data:
                all_data[key] = data
        return all_data


def create_chart(data, chart_state, highlight=None):
    """Create a Plotly chart based on the current scroll state."""
    income = np.array(data["income"])
    fpl = data["fpl"]

    fig = go.Figure()

    # Determine x-axis range
    if chart_state == "cliff_focus":
        x_max = fpl * 5  # Show up to 500% FPL for cliff focus
    else:
        # Find where PTCs end
        ptc_ira = np.array(data["ptc_ira"])
        last_nonzero = np.where(ptc_ira > 0)[0]
        x_max = income[last_nonzero[-1]] * 1.1 if len(last_nonzero) > 0 else 200000
        x_max = min(x_max, 300000)

    # Common layout settings
    layout_kwargs = dict(
        height=500,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=FONTS["body"], size=14),
        margin=dict(l=80, r=40, t=60, b=80),
        xaxis=dict(
            tickformat="$,.0f",
            range=[0, x_max],
            gridcolor=COLORS["gray_200"],
            title="Household Income",
            title_font=dict(size=14, color=COLORS["text_secondary"]),
        ),
        yaxis=dict(
            tickformat="$,.0f",
            gridcolor=COLORS["gray_200"],
            rangemode="tozero",
            title_font=dict(size=14, color=COLORS["text_secondary"]),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        hovermode="x unified",
    )

    # Add FPL markers as vertical lines
    fpl_markers = [
        (1.0, "100% FPL"),
        (1.38, "138% FPL"),
        (4.0, "400% FPL"),
        (7.0, "700% FPL"),
    ]

    for mult, label in fpl_markers:
        fpl_income = fpl * mult
        if fpl_income < x_max:
            fig.add_vline(
                x=fpl_income,
                line_dash="dot",
                line_color=COLORS["gray_300"],
                line_width=1,
                annotation_text=label,
                annotation_position="top",
                annotation_font_size=10,
                annotation_font_color=COLORS["gray_500"],
            )

    # Build traces based on chart state
    if chart_state in ["all_programs", "medicaid_focus", "chip_focus"]:
        # Show all health programs
        medicaid = np.array(data["medicaid"])
        chip = np.array(data["chip"])
        ptc_baseline = np.array(data["ptc_baseline"])

        # Medicaid trace
        opacity = 1.0 if chart_state == "medicaid_focus" or highlight == "medicaid" else 0.7
        fig.add_trace(go.Scatter(
            x=income, y=medicaid,
            mode="lines",
            name="Medicaid",
            line=dict(color=COLORS["medicaid"], width=3 if opacity == 1.0 else 2),
            opacity=opacity,
        ))

        # CHIP trace (if any children)
        if np.any(chip > 0):
            opacity = 1.0 if chart_state == "chip_focus" or highlight == "chip" else 0.7
            fig.add_trace(go.Scatter(
                x=income, y=chip,
                mode="lines",
                name="CHIP",
                line=dict(color=COLORS["chip"], width=3 if opacity == 1.0 else 2),
                opacity=opacity,
            ))

        # PTC baseline
        fig.add_trace(go.Scatter(
            x=income, y=ptc_baseline,
            mode="lines",
            name="Premium Tax Credit (Baseline)",
            line=dict(color=COLORS["baseline"], width=2),
            opacity=0.7,
        ))

        layout_kwargs["yaxis"]["title"] = "Annual Benefit Value"
        layout_kwargs["title"] = dict(
            text="Health Coverage Programs by Income",
            font=dict(size=20, color=COLORS["primary"]),
        )

    elif chart_state in ["ptc_baseline", "cliff_focus"]:
        # Focus on PTC baseline and the cliff
        ptc_baseline = np.array(data["ptc_baseline"])

        fig.add_trace(go.Scatter(
            x=income, y=ptc_baseline,
            mode="lines",
            name="PTC (Current Law after 2025)",
            line=dict(color=COLORS["baseline"], width=3),
            fill="tozeroy",
            fillcolor="rgba(156, 163, 175, 0.2)",
        ))

        # Add cliff annotation
        if chart_state == "cliff_focus":
            cliff_income = fpl * 4
            fig.add_annotation(
                x=cliff_income,
                y=0,
                text="<b>THE CLIFF</b><br>Credits drop to $0",
                showarrow=True,
                arrowhead=2,
                arrowcolor=COLORS["error"],
                ax=0,
                ay=-60,
                bgcolor=COLORS["error"],
                font=dict(color="white", size=12),
                borderpad=8,
            )

        layout_kwargs["yaxis"]["title"] = "Annual Premium Tax Credit"
        layout_kwargs["title"] = dict(
            text="Premium Tax Credits Under Current Law",
            font=dict(size=20, color=COLORS["primary"]),
        )

    elif chart_state == "ira_reform":
        # Show baseline vs IRA reform
        ptc_baseline = np.array(data["ptc_baseline"])
        ptc_ira = np.array(data["ptc_ira"])

        fig.add_trace(go.Scatter(
            x=income, y=ptc_baseline,
            mode="lines",
            name="Baseline (Current Law)",
            line=dict(color=COLORS["baseline"], width=2),
        ))

        fig.add_trace(go.Scatter(
            x=income, y=ptc_ira,
            mode="lines",
            name="IRA Extension",
            line=dict(color=COLORS["ira_reform"], width=3),
            fill="tonexty",
            fillcolor="rgba(44, 100, 150, 0.2)",
        ))

        layout_kwargs["yaxis"]["title"] = "Annual Premium Tax Credit"
        layout_kwargs["title"] = dict(
            text="IRA Extension vs Current Law",
            font=dict(size=20, color=COLORS["primary"]),
        )

    elif chart_state == "both_reforms":
        # Show all three scenarios
        ptc_baseline = np.array(data["ptc_baseline"])
        ptc_ira = np.array(data["ptc_ira"])
        ptc_700fpl = np.array(data["ptc_700fpl"]) if data["ptc_700fpl"] else None

        fig.add_trace(go.Scatter(
            x=income, y=ptc_baseline,
            mode="lines",
            name="Baseline",
            line=dict(color=COLORS["baseline"], width=2),
        ))

        fig.add_trace(go.Scatter(
            x=income, y=ptc_ira,
            mode="lines",
            name="IRA Extension",
            line=dict(color=COLORS["ira_reform"], width=3),
        ))

        if ptc_700fpl is not None:
            fig.add_trace(go.Scatter(
                x=income, y=ptc_700fpl,
                mode="lines",
                name="Bipartisan 700% FPL",
                line=dict(color=COLORS["bipartisan_reform"], width=3),
            ))

        layout_kwargs["yaxis"]["title"] = "Annual Premium Tax Credit"
        layout_kwargs["title"] = dict(
            text="Comparing Reform Options",
            font=dict(size=20, color=COLORS["primary"]),
        )

    elif chart_state == "impact":
        # Show change in net income
        net_baseline = np.array(data["net_income_baseline"])
        net_ira = np.array(data["net_income_ira"])
        net_700fpl = np.array(data["net_income_700fpl"]) if data["net_income_700fpl"] else None

        delta_ira = net_ira - net_baseline
        delta_700fpl = net_700fpl - net_baseline if net_700fpl is not None else None

        fig.add_trace(go.Scatter(
            x=income, y=delta_ira,
            mode="lines",
            name="Gain from IRA Extension",
            line=dict(color=COLORS["ira_reform"], width=3),
            fill="tozeroy",
            fillcolor="rgba(44, 100, 150, 0.2)",
        ))

        if delta_700fpl is not None:
            fig.add_trace(go.Scatter(
                x=income, y=delta_700fpl,
                mode="lines",
                name="Gain from Bipartisan Bill",
                line=dict(color=COLORS["bipartisan_reform"], width=3),
            ))

        # Add zero line
        fig.add_hline(y=0, line_color=COLORS["gray_400"], line_width=1)

        layout_kwargs["yaxis"]["title"] = "Change in Annual Net Income"
        layout_kwargs["title"] = dict(
            text="Impact of Reform on Household Finances",
            font=dict(size=20, color=COLORS["primary"]),
        )

    fig.update_layout(**layout_kwargs)
    return fig


# ============================================================================
# Custom CSS for Scrollytelling Layout
# ============================================================================

def inject_custom_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto:wght@400;500&display=swap');

    /* Base styles */
    .stApp {
        font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    /* Header styling */
    .main-header {
        font-family: 'Inter', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: #319795;
        text-align: center;
        margin-bottom: 0.5rem;
        line-height: 1.2;
    }

    .sub-header {
        font-size: 1.1rem;
        color: #5A5A5A;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* Household selector pills */
    .household-selector {
        display: flex;
        justify-content: center;
        gap: 0.75rem;
        flex-wrap: wrap;
        margin-bottom: 2rem;
        padding: 1rem;
        background: #F5F9FF;
        border-radius: 12px;
    }

    .household-pill {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 2px solid transparent;
    }

    .household-pill.active {
        background: #319795;
        color: white;
    }

    .household-pill:not(.active) {
        background: white;
        color: #344054;
        border-color: #E2E8F0;
    }

    .household-pill:not(.active):hover {
        border-color: #319795;
        color: #319795;
    }

    /* Scroll section styling */
    .scroll-section {
        padding: 2rem;
        margin-bottom: 1rem;
        background: white;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    .scroll-section.active {
        border-color: #319795;
        box-shadow: 0 4px 16px rgba(49, 151, 149, 0.15);
    }

    .section-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: #319795;
        margin-bottom: 1rem;
    }

    .section-content {
        font-size: 1.05rem;
        line-height: 1.7;
        color: #344054;
    }

    .section-content strong {
        color: #1F2937;
    }

    /* Insight box */
    .insight-box {
        background: linear-gradient(135deg, #E6FFFA 0%, #B2F5EA 100%);
        padding: 1rem 1.25rem;
        border-radius: 8px;
        margin-top: 1rem;
        border-left: 4px solid #319795;
    }

    .insight-box p {
        margin: 0;
        color: #285E61;
        font-size: 0.95rem;
    }

    /* Calculator link button */
    .calc-button {
        display: inline-block;
        padding: 0.75rem 1.5rem;
        background: #319795;
        color: white !important;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        margin-top: 1rem;
        transition: background 0.2s ease;
    }

    .calc-button:hover {
        background: #285E61;
    }

    /* Chart container */
    .chart-container {
        position: sticky;
        top: 0;
        padding: 1rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    /* Household info card */
    .household-card {
        background: #F5F9FF;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    .household-card h4 {
        margin: 0 0 0.5rem 0;
        color: #319795;
        font-family: 'Inter', sans-serif;
    }

    .household-card p {
        margin: 0;
        color: #5A5A5A;
        font-size: 0.9rem;
    }

    /* Progress indicator */
    .progress-dots {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        margin: 1rem 0;
    }

    .progress-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #E2E8F0;
    }

    .progress-dot.active {
        background: #319795;
        width: 24px;
        border-radius: 4px;
    }

    .progress-dot.completed {
        background: #B2F5EA;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Responsive adjustments */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.75rem;
        }

        .scroll-section {
            padding: 1.25rem;
        }

        .section-title {
            font-size: 1.25rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# Main App
# ============================================================================

def main():
    inject_custom_css()

    # Header
    st.markdown('<h1 class="main-header">Understanding ACA Health Coverage Reforms</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">An interactive guide to how premium tax credits work and what\'s at stake in 2026</p>', unsafe_allow_html=True)

    # Household selector
    st.markdown("### Select an Example Household")

    cols = st.columns(len(PRESET_HOUSEHOLDS))
    selected_household = st.session_state.get("selected_household", "tampa_family")

    for i, (key, household) in enumerate(PRESET_HOUSEHOLDS.items()):
        with cols[i]:
            is_selected = key == selected_household
            button_type = "primary" if is_selected else "secondary"
            if st.button(
                household["name"],
                key=f"btn_{key}",
                type=button_type,
                use_container_width=True,
            ):
                st.session_state.selected_household = key
                st.rerun()

    # Show household info
    household = PRESET_HOUSEHOLDS[selected_household]
    st.markdown(f"""
    <div class="household-card">
        <h4>{household['name']}</h4>
        <p>{household['description']}</p>
        <div class="insight-box">
            <p><strong>Key insight:</strong> {household['key_insight']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load precomputed data for selected household
    data = load_household_data(selected_household)

    if data is None:
        st.stop()

    # Two-column layout: scrollable text on right, sticky chart on left
    chart_col, text_col = st.columns([3, 2])

    # Track current section
    current_section = st.session_state.get("current_section", 0)

    with text_col:
        # Progress indicator
        progress_html = '<div class="progress-dots">'
        for i in range(len(SCROLL_SECTIONS)):
            if i < current_section:
                progress_html += '<div class="progress-dot completed"></div>'
            elif i == current_section:
                progress_html += '<div class="progress-dot active"></div>'
            else:
                progress_html += '<div class="progress-dot"></div>'
        progress_html += '</div>'
        st.markdown(progress_html, unsafe_allow_html=True)

        # Navigation buttons
        nav_cols = st.columns([1, 3, 1])
        with nav_cols[0]:
            if current_section > 0:
                if st.button("← Back", use_container_width=True):
                    st.session_state.current_section = current_section - 1
                    st.rerun()
        with nav_cols[2]:
            if current_section < len(SCROLL_SECTIONS) - 1:
                if st.button("Next →", use_container_width=True, type="primary"):
                    st.session_state.current_section = current_section + 1
                    st.rerun()

        # Current section content
        section = SCROLL_SECTIONS[current_section]
        st.markdown(f"### {section['title']}")
        st.markdown(section['content'])

        # Link to calculator on last section
        if section['id'] == 'your_turn':
            st.markdown("---")
            if st.button("🧮 Open the Full Calculator", type="primary", use_container_width=True):
                st.switch_page("pages/calculator.py")

    with chart_col:
        # Create and display chart based on current section
        section = SCROLL_SECTIONS[current_section]
        fig = create_chart(data, section['chart_state'], section.get('highlight'))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Show key metrics below chart
        if section['chart_state'] in ['ira_reform', 'both_reforms', 'impact']:
            fpl = data['fpl']

            # Calculate key values at 400% FPL
            income_arr = np.array(data['income'])
            idx_400fpl = np.argmin(np.abs(income_arr - fpl * 4))

            ptc_baseline = data['ptc_baseline'][idx_400fpl]
            ptc_ira = data['ptc_ira'][idx_400fpl]
            ptc_700 = data['ptc_700fpl'][idx_400fpl] if data['ptc_700fpl'] else 0

            metric_cols = st.columns(3)
            with metric_cols[0]:
                st.metric(
                    "At 400% FPL",
                    f"${fpl * 4:,.0f}",
                    help="Income at 400% of Federal Poverty Level"
                )
            with metric_cols[1]:
                st.metric(
                    "Baseline PTC",
                    f"${ptc_baseline:,.0f}",
                    help="Premium tax credit under current law"
                )
            with metric_cols[2]:
                reform_value = ptc_ira if section['chart_state'] != 'both_reforms' else max(ptc_ira, ptc_700)
                gain = reform_value - ptc_baseline
                st.metric(
                    "With Reform",
                    f"${reform_value:,.0f}",
                    f"+${gain:,.0f}" if gain > 0 else None,
                )


if __name__ == "__main__":
    main()
