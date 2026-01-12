import { useState, useEffect } from "react";
import { useInView } from "react-intersection-observer";
import HealthBenefitsChart from "./HealthBenefitsChart";
import "./HouseholdExplorer.css";

// Import precomputed household data
import householdData from "../data/households/all_households.json";

// Household definitions with detailed narratives and chart states
const HOUSEHOLDS = {
  florida_family: {
    name: "Florida Family of Four",
    shortName: "Florida Family",
    description: "Two parents (40) with two kids (10, 8)",
    location: "Hillsborough County, FL",
    isExpansion: false,
    hasChildren: true,
    sections: [
      {
        id: "fl_intro",
        title: "Meet the Florida Family",
        content: `A family of four in **Hillsborough County, Florida**: two 40-year-old parents with children ages 10 and 8.

The chart shows all the health programs this family might access across different income levels. Let's break down each one.`,
        chartState: "all_programs",
      },
      {
        id: "fl_medicaid",
        title: "Medicaid: Limited for Parents",
        content: `**Medicaid** (teal line) provides coverage at low incomes, but Florida has **not expanded Medicaid** under the ACA.

This creates a **coverage gap** for parents: adults without disabilities may not qualify for Medicaid even at very low incomes, while in expansion states they'd be covered up to 138% FPL.

The children may still qualify for Medicaid at low incomes.`,
        chartState: "medicaid_focus",
      },
      {
        id: "fl_chip",
        title: "CHIP: Covering the Children",
        content: `**CHIP** (Children's Health Insurance Program) covers children in families with incomes too high for Medicaid but who still need help affording coverage.

In Florida, children can qualify for CHIP at higher income levels than their parents qualify for Medicaid. This means the kids might have coverage through CHIP while parents need marketplace plans with premium tax credits.`,
        chartState: "chip_focus",
      },
      {
        id: "fl_cliff",
        title: "The 400% FPL Cliff",
        content: `The **gray baseline line** shows premium tax credits under the original ACA rules (returning in 2026). Notice how it drops to **zero at 400% FPL**—that's the "subsidy cliff."

For this family of four, 400% FPL is about **$132,000**. Above that income, they'd lose all subsidies under baseline 2026 rules.

With children, their FPL threshold is higher than a single adult's, giving them more room before hitting the cliff.`,
        chartState: "cliff_focus",
      },
      {
        id: "fl_ira",
        title: "IRA Extension Impact",
        content: `The **blue shaded area** shows the additional premium tax credits this family would receive if the IRA enhancements are extended.

Key differences from baseline:
- **No cliff**—subsidies continue above 400% FPL
- **Lower contributions** at every income level
- **8.5% cap** on required premium contributions`,
        chartState: "ira_impact",
      },
      {
        id: "fl_reform",
        title: "Comparing All Options",
        content: `The chart shows all three scenarios:
- **Gray:** Baseline (2026, IRA expires)
- **Blue:** IRA Extension
- **Purple:** 700% FPL Proposal

For this family of four, 400% FPL is about **$132,000** and 700% FPL is about **$231,000**.`,
        chartState: "both_reforms",
      },
    ],
  },
  california_couple: {
    name: "California Couple",
    shortName: "CA Couple",
    description: "Older couple (64, 62)",
    location: "San Benito County, CA",
    isExpansion: true,
    hasChildren: false,
    sections: [
      {
        id: "ca_intro",
        title: "Meet the California Couple",
        content: `An older couple in **San Benito County, California**: ages 64 and 62, approaching Medicare eligibility.

The chart shows their coverage options across income levels. As a childless couple, they have fewer program options—but premium subsidies are crucial given their age.`,
        chartState: "all_programs",
      },
      {
        id: "ca_medicaid",
        title: "Medicaid: Expansion State Advantage",
        content: `California **expanded Medicaid** (called Medi-Cal), so this couple qualifies for free coverage at incomes up to **138% FPL** (about $27,000 for a couple).

This is a significant advantage over non-expansion states, where adults without children often fall into a coverage gap at low incomes.

Above the Medicaid threshold, they transition to marketplace coverage with premium tax credits.`,
        chartState: "medicaid_focus",
      },
      {
        id: "ca_cliff",
        title: "The Cliff and Age-Based Rating",
        content: `**Age-based rating** allows insurers to charge older adults up to **3x more** than younger people. This couple's benchmark plan costs significantly more than a younger person's.

At 400% FPL (~$87,000 for a couple), losing subsidies means paying the full, age-rated premium.

The cliff's dollar impact is larger for older adults due to their higher baseline premiums.`,
        chartState: "cliff_focus",
      },
      {
        id: "ca_ira",
        title: "IRA Extension Impact",
        content: `The **blue shaded area** shows the additional premium tax credits this couple would receive with the IRA extension.

Key differences from baseline:
- Subsidies continue at **any income level**
- **8.5% cap** on required contributions
- No cliff—gradual phase-out instead of sudden loss

The shaded area is larger for older adults due to their higher premiums.`,
        chartState: "ira_impact",
      },
      {
        id: "ca_reform",
        title: "Reform Comparison",
        content: `The chart shows all three scenarios:
- **IRA Extension** (blue): 8.5% cap, no income limit
- **700% FPL Proposal** (purple): Extends to ~$152,000, 9.25% cap

For this couple, 400% FPL is about **$87,000** and 700% FPL is about **$152,000**.`,
        chartState: "both_reforms",
      },
    ],
  },
  texas_couple: {
    name: "Young Texas Couple",
    shortName: "Texas Couple",
    description: "Married couple (28, 27)",
    location: "Harris County, TX",
    isExpansion: false,
    hasChildren: false,
    sections: [
      {
        id: "tx_intro",
        title: "Meet the Texas Couple",
        content: `A married couple in their late 20s in **Harris County, Texas** (Houston area): ages 28 and 27.

As a childless couple in a non-expansion state, they face unique challenges in accessing affordable coverage.`,
        chartState: "all_programs",
      },
      {
        id: "tx_medicaid",
        title: "Medicaid: The Coverage Gap",
        content: `Texas has **not expanded Medicaid**, creating a significant problem for low-income adults.

Adults without disabilities or dependent children typically don't qualify for Texas Medicaid regardless of how low their income is. Yet they also may not qualify for marketplace subsidies below 100% FPL.

This is the infamous **"coverage gap"**—too poor for subsidies, not eligible for Medicaid.`,
        chartState: "medicaid_focus",
      },
      {
        id: "tx_cliff",
        title: "The 400% FPL Cliff",
        content: `For a couple, 400% FPL is about **$87,000** in 2026.

Above this threshold, baseline subsidies drop to zero. The cliff occurs at a higher dollar amount for couples than for single adults due to larger household size.`,
        chartState: "cliff_focus",
      },
      {
        id: "tx_ira",
        title: "IRA Extension Impact",
        content: `The **blue shaded area** shows the additional subsidies available with the IRA extension:

- Subsidies continue above $87,000
- **8.5% cap** on required contributions
- Coverage available below 100% FPL (where baseline provides none in non-expansion states)`,
        chartState: "ira_impact",
      },
      {
        id: "tx_reform",
        title: "Reform Comparison",
        content: `The chart shows all three scenarios:
- **IRA Extension** (blue): No income limit, 8.5% cap
- **700% FPL Proposal** (purple): Extends to ~$152,000, 9.25% cap

For this couple, 400% FPL is about **$87,000** and 700% FPL is about **$152,000**.`,
        chartState: "both_reforms",
      },
    ],
  },
  ny_family: {
    name: "Young NYC Family",
    shortName: "NYC Family",
    description: "Young parents (30, 28) with toddler (2)",
    location: "New York County, NY",
    isExpansion: true,
    hasChildren: true,
    sections: [
      {
        id: "ny_intro",
        title: "Meet the NYC Family",
        content: `A young family in **Manhattan**: parents ages 30 and 28 with a 2-year-old toddler.

New York has **high premiums for young adults** because insurers cannot charge different rates based on age, which raises costs for younger enrollees.`,
        chartState: "all_programs",
      },
      {
        id: "ny_medicaid",
        title: "Medicaid: Generous in New York",
        content: `New York **expanded Medicaid** and has some of the most generous eligibility rules in the country.

This family qualifies for Medicaid at incomes up to **138% FPL** (about $41,000 for a family of 3). New York also has higher income limits for children and pregnant women.

The transition from Medicaid to marketplace coverage is smoother in expansion states.`,
        chartState: "medicaid_focus",
      },
      {
        id: "ny_chip",
        title: "Child Health Plus for the Toddler",
        content: `New York's **Child Health Plus** program (CHIP) covers children at income levels well above the Medicaid threshold.

This means the 2-year-old may have coverage through Child Health Plus even when the parents need to purchase marketplace plans. The child's coverage remains stable as family income changes.`,
        chartState: "chip_focus",
      },
      {
        id: "ny_cliff",
        title: "The Cliff for a Family of Three",
        content: `For a family of 3, 400% FPL is about **$109,000** in 2026.

Above this threshold, baseline subsidies drop to zero. The FPL threshold is the same regardless of local cost of living.`,
        chartState: "cliff_focus",
      },
      {
        id: "ny_ira",
        title: "IRA Extension Impact",
        content: `The **blue shaded area** shows the additional premium tax credits available under the IRA extension:

- Subsidies continue above $109,000
- **8.5% cap** on required contributions
- Gradual phase-out instead of cliff`,
        chartState: "ira_impact",
      },
      {
        id: "ny_reform",
        title: "Reform Comparison",
        content: `The chart shows all three scenarios:
- **IRA Extension** (blue): No cliff, 8.5% cap at any income
- **700% FPL Proposal** (purple): Extends to ~$191,000, 9.25% cap

For this family of three, 400% FPL is about **$109,000** and 700% FPL is about **$191,000**.`,
        chartState: "both_reforms",
      },
    ],
  },
};

const HOUSEHOLD_KEYS = ["florida_family", "california_couple", "texas_couple", "ny_family"];

// Parse markdown-style bold text
const parseContent = (text) => {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};

// Individual scroll section within a household
function HouseholdScrollSection({ section, index, isActive, onInView }) {
  const { ref, inView } = useInView({
    threshold: 0.5,
    rootMargin: "-20% 0px -40% 0px",
  });

  useEffect(() => {
    if (inView) {
      onInView(index);
    }
  }, [inView, index, onInView]);

  return (
    <div
      ref={ref}
      className={`household-scroll-section ${isActive ? "active" : ""}`}
    >
      <h3 className="household-section-title">{section.title}</h3>
      <div className="household-section-content">
        {section.content.split("\n\n").map((paragraph, i) => (
          <p key={i}>{parseContent(paragraph)}</p>
        ))}
      </div>
    </div>
  );
}

function HouseholdExplorer() {
  const [selectedHousehold, setSelectedHousehold] = useState("florida_family");
  const [activeSection, setActiveSection] = useState(0);

  const household = HOUSEHOLDS[selectedHousehold];
  const data = householdData[selectedHousehold];
  const currentSection = household.sections[activeSection] || household.sections[0];

  // Reset section when changing households
  useEffect(() => {
    setActiveSection(0);
  }, [selectedHousehold]);

  return (
    <div className="household-explorer">
      {/* Household tabs */}
      <div className="household-tabs">
        {HOUSEHOLD_KEYS.map((key) => (
          <button
            key={key}
            className={`household-tab ${selectedHousehold === key ? "active" : ""}`}
            onClick={() => setSelectedHousehold(key)}
          >
            <span className="tab-name">{HOUSEHOLDS[key].shortName}</span>
            <span className="tab-location">{HOUSEHOLDS[key].location}</span>
          </button>
        ))}
      </div>

      {/* Household info bar */}
      <div className="household-info-bar">
        <span className="household-description">{household.description}</span>
        <span className={`expansion-badge ${household.isExpansion ? "expansion" : "non-expansion"}`}>
          {household.isExpansion ? "Medicaid Expansion" : "Non-Expansion State"}
        </span>
      </div>

      {/* Scrollytelling container for this household */}
      <div className="household-scrolly-container">
        <div className="household-chart-column">
          <div className="household-chart-sticky">
            <HealthBenefitsChart
              data={data}
              chartState={currentSection.chartState}
              householdInfo={household}
            />
          </div>
        </div>

        <div className="household-text-column">
          {household.sections.map((section, index) => (
            <HouseholdScrollSection
              key={section.id}
              section={section}
              index={index}
              isActive={activeSection === index}
              onInView={setActiveSection}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default HouseholdExplorer;
