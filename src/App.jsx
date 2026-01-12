import { useState, useRef, useEffect } from "react";
import HealthBenefitsChart from "./components/HealthBenefitsChart";
import ScrollSection from "./components/ScrollSection";
import CliffComparisonTable from "./components/CliffComparisonTable";
import ContributionScheduleTable from "./components/ContributionScheduleTable";
import ContributionScheduleChart from "./components/ContributionScheduleChart";
import HouseholdExplorer from "./components/HouseholdExplorer";
import Calculator from "./components/Calculator";
import "./App.css";

// Import precomputed household data
import cliffDemoData from "./data/households/cliff_demo.json";

// Scroll sections content - background first, then household example, then health programs, then reforms
const SECTIONS = [
  // PART 1: Background on how ACA subsidies work
  {
    id: "intro",
    title: "How ACA premium tax credits work",
    content: `The Affordable Care Act (ACA) created **premium tax credits** to help Americans afford health insurance purchased through the marketplace.

These credits work by capping how much of your income you're required to pay for a benchmark health plan—the **second-lowest cost silver plan (SLCSP)** in your area.

If the benchmark plan costs more than your required contribution, the government pays the difference as a tax credit.`,
    showContributionChart: true,
    chartPolicies: ["baseline"],
  },
  {
    id: "arpa_ira",
    title: "ARPA and IRA enhancements (2021–2025)",
    content: `The **American Rescue Plan Act (ARPA)** of 2021 temporarily enhanced these subsidies. The **Inflation Reduction Act (IRA)** of 2022 extended them through 2025.

Key changes:
• Removed the 400% FPL ceiling—credits available at any income
• Capped contributions at 8.5% of income for everyone
• Lowered contributions at every income level

The chart shows how the IRA (blue) differs from the original ACA (gray).`,
    showContributionChart: true,
    chartPolicies: ["baseline", "ira"],
  },
  {
    id: "expiration",
    title: "What happened in 2026",
    content: `The ARPA/IRA enhancements **expired** at the end of 2025.

The subsidy structure reverted to the **original ACA rules**:
• The 400% FPL ceiling returned
• Required contributions increased

The baseline contribution schedule now requires **higher payments** and ends at 400% FPL—the "subsidy cliff."`,
    showContributionChart: true,
    chartPolicies: ["baseline"],
  },

  // PART 2: Household example
  {
    id: "example_intro",
    title: "Example: a middle-income household",
    content: `To illustrate the impact, consider a 45-year-old single adult in Lebanon County, Pennsylvania, earning **$104,200** a year—about **650% of the federal poverty level**.

In 2025, under the IRA enhancements, this household:
• Paid **$963/month** for the benchmark plan (SLCSP)
• Received a **$242/month** tax credit
• Paid a net premium of **$720/month**`,
    useCliffData: true,
    showCliffTable: true,
    showSlcsp: true,
    showBaseline2026: false,
    showReforms: false,
  },
  {
    id: "example_2026",
    title: "2026: after expiration",
    content: `In 2026, this household:

**a) Faces a higher premium** for their benchmark plan: $1,003/month (up from $963/month, +4.2%)

**b) Lost their subsidy** entirely: tax credit dropped from $242/month to **$0** because they exceed the 400% FPL ceiling

Net premium rose from $720/month to **$1,003/month**—an increase of **$283/month (+39%)**.`,
    useCliffData: true,
    showCliffTable: true,
    showSlcsp: true,
    showBaseline2026: true,
    showReforms: false,
  },

  // PART 3: Policy options for this household
  {
    id: "reform_options",
    title: "Policy options",
    content: `Two proposals were introduced in Congress:

**IRA Extension:** Maintains the 8.5% cap structure
• Tax credit: **$265/month** → Net premium: **$738/month**

**Bipartisan Health Insurance Affordability Act:** Introduced by Rep. Dunn (R-FL) and Rep. Schneider (D-IL) on December 9, 2025, this bill extends eligibility to 700% FPL with a 9.25% cap
• Tax credit: **$223/month** → Net premium: **$780/month**`,
    useCliffData: true,
    showCliffTable: true,
    showSlcsp: false,
    showReforms: true,
  },

  // PART 4: Health programs overview (using PA single adult)
  {
    id: "health_programs",
    title: "The full picture: health coverage programs",
    content: `Premium tax credits are one part of the health coverage landscape. Americans may also qualify for:

• **Medicaid:** Free coverage for low-income households (eligibility varies by state)
• **Marketplace subsidies:** PTCs for those not eligible for other programs

The chart shows how these programs interact across income levels for our Pennsylvania example.`,
    useCliffData: true,
    chartState: "all_programs",
  },
  {
    id: "medicaid",
    title: "Medicaid coverage",
    content: `**Medicaid** provides coverage for low-income Americans. Pennsylvania expanded Medicaid, so adults qualify up to **138% FPL**.

For our 45-year-old, this means Medicaid covers incomes up to about $22,000. If they earn more, they may be eligible for premium tax credits (PTCs).`,
    useCliffData: true,
    chartState: "medicaid_focus",
  },
  {
    id: "reforms_chart",
    title: "Premium tax credits under different policies",
    content: `The chart shows premium tax credits across income levels under three scenarios:

• **Gray line:** Baseline (post-IRA expiration)
• **Blue line:** IRA extension
• **Purple line:** Bipartisan Health Insurance Affordability Act

The baseline drops to zero at 400% FPL. Both reform options continue providing credits at higher incomes.`,
    useCliffData: true,
    chartState: "both_reforms",
  },
  {
    id: "ira_impact_chart",
    title: "IRA extension: the difference",
    content: `The **blue shaded area** represents the additional premium tax credits available under the IRA extension compared to baseline.

For this Pennsylvania household:
• Below 400% FPL: The IRA provides **lower required contributions**
• Above 400% FPL: The IRA provides **full subsidy access** where baseline provides none

The size of the shaded area shows the dollar value of the difference at each income level.`,
    useCliffData: true,
    chartState: "ira_impact",
  },

  // PART 5: Household case studies - links to explorer
  {
    id: "explore_households",
    title: "Explore different households",
    content: `The impact of ACA policy changes varies by household type, location, and income level.

Click below to explore how four different households are affected—with details on Medicaid expansion, CHIP eligibility, and the subsidy cliff for each.`,
    useCliffData: true,
    chartState: "both_reforms",
    showHouseholdExplorerLink: true,
  },
];

// URL routing helpers
const PAGE_ROUTES = {
  "": "main",
  "overview": "main",
  "households": "households",
  "calculator": "calculator",
};

const ROUTE_PAGES = {
  "main": "",
  "households": "households",
  "calculator": "calculator",
};

function getPageFromHash() {
  const hash = window.location.hash.slice(1); // Remove the #
  const [route] = hash.split("?"); // Ignore query params for page routing
  return PAGE_ROUTES[route] || "main";
}

// Check if running in embedded mode (iframe)
function isEmbedded() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get("embedded") === "true";
}

function App() {
  const [activeSection, setActiveSection] = useState(0);
  const [currentPage, setCurrentPage] = useState(() => getPageFromHash());
  const [embedded] = useState(() => isEmbedded());
  const chartRef = useRef(null);

  // Sync URL hash with page state
  useEffect(() => {
    const handleHashChange = () => {
      const page = getPageFromHash();
      setCurrentPage(page);
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  // Update URL when page changes (but not on initial load)
  const navigateToPage = (page) => {
    const route = ROUTE_PAGES[page];
    const currentHash = window.location.hash.slice(1);
    const [, queryString] = currentHash.split("?");

    // Preserve query params when navigating to calculator
    if (page === "calculator" && queryString) {
      window.location.hash = `${route}?${queryString}`;
    } else {
      window.location.hash = route;
    }
    setCurrentPage(page);
  };

  // Scroll to top when page changes
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [currentPage]);

  // Get current section
  const currentSection = SECTIONS[activeSection] || SECTIONS[0];

  // Handle section visibility changes
  const handleSectionInView = (index) => {
    setActiveSection(index);
  };

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
          showBaseline2026={currentSection.showBaseline2026 !== false}
        />
      );
    }
    return (
      <HealthBenefitsChart
        data={cliffDemoData}
        chartState={currentSection.chartState || "both_reforms"}
        householdInfo={cliffDemoData.household_info}
      />
    );
  };

  // Render the main scrolly page
  const renderMainPage = () => (
    <>
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
              onExploreHouseholds={() => navigateToPage("households")}
            />
          ))}
        </div>
      </main>
    </>
  );

  // Render the households explorer page
  const renderHouseholdsPage = () => (
    <main className="households-page">
      <HouseholdExplorer />
    </main>
  );

  // Render the calculator page
  const renderCalculatorPage = () => (
    <main className="calculator-page">
      <Calculator />
    </main>
  );

  return (
    <div className={`app ${embedded ? "embedded" : ""}`}>
      {!embedded && (
        <header className="header">
          <div className="header-content">
            <h1>ACA Premium Tax Credits: 2025 vs 2026</h1>
            <p className="subtitle">
              Modeling how the scheduled expiration of IRA enhancements affects health insurance costs
            </p>
            <div className="page-tabs">
              <button
                className={`page-tab ${currentPage === "main" ? "active" : ""}`}
                onClick={() => navigateToPage("main")}
              >
                Overview
              </button>
              <button
                className={`page-tab ${currentPage === "households" ? "active" : ""}`}
                onClick={() => navigateToPage("households")}
              >
                Explore Households
              </button>
              <button
                className={`page-tab ${currentPage === "calculator" ? "active" : ""}`}
                onClick={() => navigateToPage("calculator")}
              >
                Calculator
              </button>
            </div>
          </div>
        </header>
      )}

      {currentPage === "main" && renderMainPage()}
      {currentPage === "households" && renderHouseholdsPage()}
      {currentPage === "calculator" && renderCalculatorPage()}

      {!embedded && (
        <footer className="footer">
          <p>
            Built by <a href="https://policyengine.org" target="_blank" rel="noopener noreferrer">PolicyEngine</a>
          </p>
        </footer>
      )}
    </div>
  );
}

export default App;
