import { useState, useEffect, useRef } from "react";
import { useInView } from "react-intersection-observer";
import HouseholdSelector from "./components/HouseholdSelector";
import HealthBenefitsChart from "./components/HealthBenefitsChart";
import ScrollSection from "./components/ScrollSection";
import CliffComparisonTable from "./components/CliffComparisonTable";
import ContributionScheduleTable from "./components/ContributionScheduleTable";
import ContributionScheduleChart from "./components/ContributionScheduleChart";
import "./App.css";

// Calculator URL - uses environment variable or defaults to localhost for development
const CALCULATOR_URL = import.meta.env.VITE_CALCULATOR_URL || "http://localhost:8501";

// Import precomputed household data
import householdData from "../data/households/all_households.json";
import cliffDemoData from "../data/households/cliff_demo.json";

// Preset household definitions
const HOUSEHOLDS = {
  florida_family: {
    name: "Florida Family",
    shortName: "Florida",
    description: "Two parents (40) with two kids (10, 8) in Florida",
    location: "Hillsborough County, FL",
    isExpansion: false,
  },
  california_couple: {
    name: "California Couple",
    shortName: "California",
    description: "Older couple (64, 62) in California",
    location: "San Benito County, CA",
    isExpansion: true,
  },
  texas_single: {
    name: "Texas Single",
    shortName: "Texas",
    description: "Single adult (35) in Texas",
    location: "Harris County, TX",
    isExpansion: false,
  },
  ny_family: {
    name: "NY Family",
    shortName: "New York",
    description: "Young parents (30, 28) with toddler (2) in NYC",
    location: "New York County, NY",
    isExpansion: true,
  },
};

// Scroll sections content - background first, then household example, then health programs, then reforms
const SECTIONS = [
  // PART 1: Background on how ACA subsidies work
  {
    id: "intro",
    title: "How the ACA Makes Health Insurance Affordable",
    content: `The Affordable Care Act (ACA) created **premium tax credits** to help Americans afford health insurance purchased through the marketplace.

These credits work by capping how much of your income you're required to pay for a benchmark health plan—the **second-lowest cost silver plan (SLCSP)** in your area.

If the benchmark plan costs more than your required contribution, the government pays the difference as a tax credit.`,
    showContributionChart: true,
    chartPolicies: ["baseline"],
  },
  {
    id: "arpa_ira",
    title: "ARPA and IRA Enhancements (2021-2025)",
    content: `The **American Rescue Plan Act (ARPA)** of 2021 temporarily enhanced these subsidies. The **Inflation Reduction Act (IRA)** of 2022 extended them through 2025.

Key changes:
- **Removed the 400% FPL ceiling**—credits now available at any income
- **Capped contributions at 8.5%** of income for everyone
- **Lowered contributions** at every income level

The chart shows how the IRA (blue) differs from the original ACA (gray).`,
    showContributionChart: true,
    chartPolicies: ["baseline", "ira"],
  },
  {
    id: "expiration",
    title: "What Happens in 2026?",
    content: `The ARPA/IRA enhancements are **scheduled to expire** at the end of 2025.

Without congressional action, the subsidy structure will revert to the **original ACA rules**:
- The 400% FPL ceiling returns
- Required contributions increase
- Millions of households will see higher premiums or lose subsidies entirely

Notice how the gray baseline line ends at 400% FPL—the "subsidy cliff."`,
    showContributionChart: true,
    chartPolicies: ["baseline", "ira"],
  },

  // PART 2: Household example
  {
    id: "example_intro",
    title: "Example: A Middle-Income Household",
    content: `To illustrate the impact, consider a 45-year-old single adult in Lebanon County, Pennsylvania, earning **$104,200** a year—about **650% of the federal poverty level**.

In 2025, under the IRA enhancements:
- Benchmark plan (SLCSP): **$963/month**
- Tax credit: **$242/month**
- Net premium: **$720/month**`,
    useCliffData: true,
    showCliffTable: true,
    showSlcsp: true,
    showReforms: false,
  },
  {
    id: "example_2026",
    title: "2026: After Expiration",
    content: `In 2026, two things change:

**1. Premium increase:** The benchmark plan rises from $963/month to $1,003/month (+4.2%).

**2. Subsidy loss:** Their tax credit drops from $242/month to **$0** (−100%) because they exceed the 400% FPL ceiling.

Net premium rises from $720/month to **$1,003/month**—an increase of **$283/month (+39%)**.`,
    useCliffData: true,
    showCliffTable: true,
    showSlcsp: false,
    showReforms: false,
  },

  // PART 3: Policy options for this household
  {
    id: "reform_options",
    title: "Policy Options",
    content: `Two proposals would preserve subsidies for this household:

**IRA Extension:** Maintain the current 8.5% cap structure
- Tax credit: **$265/month** → Net premium: **$738/month** (−26% vs baseline)

**700% FPL Proposal:** Extend eligibility to 700% FPL with 9.25% cap
- Tax credit: **$223/month** → Net premium: **$780/month** (−22% vs baseline)`,
    useCliffData: true,
    showCliffTable: true,
    showSlcsp: false,
    showReforms: true,
  },

  // PART 4: Health programs overview (using PA single adult)
  {
    id: "health_programs",
    title: "The Full Picture: Health Coverage Programs",
    content: `Premium tax credits are just one part of the health coverage landscape. Americans may also qualify for:

- **Medicaid:** Free coverage for low-income households (eligibility varies by state)
- **Marketplace subsidies:** PTCs for those not eligible for other programs

The chart shows how these programs interact across income levels for our Pennsylvania example.`,
    useCliffData: true,
    chartState: "all_programs",
  },
  {
    id: "medicaid",
    title: "Medicaid Coverage",
    content: `**Medicaid** provides coverage for low-income Americans. Pennsylvania expanded Medicaid, so adults qualify up to **138% FPL**.

For our 45-year-old, this means Medicaid covers incomes up to about $22,000. Above that threshold, marketplace subsidies (PTCs) help cover premiums.`,
    useCliffData: true,
    chartState: "medicaid_focus",
  },
  {
    id: "reforms_chart",
    title: "Premium Tax Credits Under Different Policies",
    content: `The chart shows premium tax credits across income levels under:

- **Gray line:** Baseline (post-IRA expiration)
- **Blue line:** IRA extension
- **Purple line:** 700% FPL proposal

Notice how the baseline drops to zero at 400% FPL, while both reform options continue providing credits at higher incomes.`,
    useCliffData: true,
    chartState: "both_reforms",
  },

  // PART 5: Explore other households
  {
    id: "explore_households",
    title: "Explore Other Households",
    content: `The impact varies significantly by household type, location, and income level.

Use the selector above to explore how different households are affected by ACA policy changes.`,
    useCliffData: false,
    chartState: "both_reforms",
    showHouseholdExplorer: true,
  },

  // PART 6: Calculator
  {
    id: "calculator",
    title: "Model Your Own Household",
    content: `Want to see results for your specific situation?

**Use our full calculator** to enter your own age, location, family size, and income.`,
    useCliffData: false,
    chartState: "both_reforms",
    showHouseholdExplorer: true,
    showCalculatorLink: true,
  },
];

function App() {
  const [selectedHousehold, setSelectedHousehold] = useState("florida_family");
  const [activeSection, setActiveSection] = useState(0);
  const chartRef = useRef(null);

  // Get data for selected household
  const householdChartData = householdData[selectedHousehold];
  const householdInfo = HOUSEHOLDS[selectedHousehold];

  // Get current section
  const currentSection = SECTIONS[activeSection] || SECTIONS[0];

  // Use cliff demo data when section specifies it
  const useCliffData = currentSection.useCliffData;
  const chartData = useCliffData ? cliffDemoData : householdChartData;

  // Handle section visibility changes
  const handleSectionInView = (index) => {
    setActiveSection(index);
  };

  // Show household selector when section enables it
  const showHouseholdSelector = currentSection.showHouseholdExplorer;

  // Determine what to show in the chart area
  const renderChartArea = () => {
    if (currentSection.showContributionChart) {
      return (
        <ContributionScheduleChart
          showPolicies={currentSection.chartPolicies}
        />
      );
    }
    if (currentSection.showContributionSchedule) {
      return (
        <ContributionScheduleTable
          showSchedules={currentSection.schedules}
        />
      );
    }
    if (currentSection.showCliffTable) {
      return (
        <CliffComparisonTable
          data={cliffDemoData}
          showReforms={currentSection.showReforms}
          showSlcsp={currentSection.showSlcsp}
        />
      );
    }
    return (
      <HealthBenefitsChart
        data={chartData}
        chartState={currentSection.chartState || "both_reforms"}
        householdInfo={useCliffData ? cliffDemoData.household_info : householdInfo}
      />
    );
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>ACA Premium Tax Credits: 2025 vs 2026</h1>
          <p className="subtitle">
            Modeling how the scheduled expiration of IRA enhancements affects health insurance costs
          </p>
        </div>
      </header>

      {showHouseholdSelector && (
        <div className="household-selector-container">
          <HouseholdSelector
            households={HOUSEHOLDS}
            selected={selectedHousehold}
            onSelect={setSelectedHousehold}
          />
          <div className="household-info">
            <span className="location">{householdInfo.location}</span>
            <span className={`expansion-badge ${householdInfo.isExpansion ? "expansion" : "non-expansion"}`}>
              {householdInfo.isExpansion ? "Medicaid Expansion" : "Non-Expansion State"}
            </span>
          </div>
        </div>
      )}

      <main className="scrollytelling-container">
        <div className="chart-column" ref={chartRef}>
          <div className="chart-sticky">
            {renderChartArea()}
          </div>
        </div>

        <div className="text-column">
          {SECTIONS.map((section, index) => (
            <ScrollSection
              key={section.id}
              section={section}
              index={index}
              isActive={activeSection === index}
              onInView={handleSectionInView}
            />
          ))}
        </div>
      </main>

      <footer className="footer">
        <p>
          Built by <a href="https://policyengine.org" target="_blank" rel="noopener noreferrer">PolicyEngine</a>
          {" | "}
          <a href={CALCULATOR_URL} target="_blank" rel="noopener noreferrer" className="calc-link">Custom Calculator</a>
        </p>
      </footer>
    </div>
  );
}

export default App;
