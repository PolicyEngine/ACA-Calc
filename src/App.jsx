import { useState, useRef, useEffect } from "react";
import HealthBenefitsChart from "./components/HealthBenefitsChart";
import ScrollSection from "./components/ScrollSection";
import CliffComparisonTable from "./components/CliffComparisonTable";
import ContributionScheduleTable from "./components/ContributionScheduleTable";
import ContributionScheduleChart from "./components/ContributionScheduleChart";
import HouseholdExplorer from "./components/HouseholdExplorer";
import Calculator from "./components/Calculator";
import "./App.css";

// Import precomputed data: the example household and the contribution
// schedules (precompute_cliff_household.py, precompute_contribution_schedules.py)
import cliffDemoData from "./data/households/cliff_demo.json";
import schedules from "./data/contribution_schedules.json";

const REVENUE_PROCEDURES = { 2026: "Revenue Procedure 2025-25", 2027: "Revenue Procedure 2026-26" };

const formatDollars = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
const monthly = (annual) => formatDollars(annual / 12);
const percentChange = (from, to) => {
  const change = (100 * (to - from)) / from;
  return `${change >= 0 ? "+" : ""}${change.toFixed(1)}%`;
};
const netPremium = (row) => Math.max(0, row.slcsp - row.ptc);

// The lowest and highest share of income a schedule charges where it gives a credit.
const rateRange = (key) => {
  const rates = schedules.schedules[key].filter((rate) => rate !== null && rate > 0);
  return [Math.min(...rates).toFixed(2), Math.max(...rates).toFixed(2)];
};

// The highest income at which the example adult has Medicaid, rounded to $1,000.
const medicaidLimit = (data) => {
  let limit = 0;
  data.income.forEach((income, i) => {
    if (data.medicaid[i] > 0) limit = income;
  });
  return formatDollars(Math.round(limit / 1000) * 1000);
};

// Scroll sections content - background first, then household example, then health programs, then reforms
function buildSections(data) {
  const year = data.year;
  const y2025 = data.years["2025"];
  const y2026 = data.years["2026"];
  const yNow = data.years[String(year)];
  const { hr1834, bill700 } = data.proposals;
  const [min2026, max2026] = rateRange("current_2026");
  const [minNow, maxNow] = rateRange(`current_${year}`);
  const netChange = netPremium(yNow) - netPremium(y2025);

  return [
    // PART 1: Background on how ACA subsidies work
    {
      id: "intro",
      title: "How ACA premium tax credits work",
      content: `The Affordable Care Act (ACA) created **premium tax credits** to help Americans afford health insurance purchased through the marketplace.

These credits work by capping how much of your income you're required to pay for a benchmark health plan—the **second-lowest cost silver plan (SLCSP)** in your area.

If the benchmark plan costs more than your required contribution, the government pays the difference as a tax credit.`,
      showContributionChart: true,
      chartPolicies: [`current${year}`],
    },
    {
      id: "arpa_ira",
      title: "ARPA and IRA enhancements (2021–2025)",
      content: `The **American Rescue Plan Act (ARPA)** of 2021 temporarily enhanced these subsidies. The **Inflation Reduction Act (IRA)** of 2022 extended them through 2025.

Key changes:
• Removed the 400% FPL ceiling—credits available at any income
• Capped contributions at 8.5% of income for everyone
• Lowered contributions at every income level

The chart shows the enhanced schedule (blue) against current law for ${year} (gray).`,
      showContributionChart: true,
      chartPolicies: [`current${year}`, "enhanced"],
    },
    {
      id: "expiration",
      title: "What happened in 2026",
      content: `The ARPA/IRA enhancements **expired** at the end of 2025.

The subsidy structure reverted to the **original ACA rules**:
• The 400% FPL ceiling returned
• Required contributions rose to between **${min2026}%** and **${max2026}%** of income

The contribution schedule now requires **higher payments** and ends at 400% FPL—the "subsidy cliff."`,
      showContributionChart: true,
      chartPolicies: ["current2026"],
    },
    {
      id: "current_law",
      title: `${year}: current law`,
      content: `For ${year}, the IRS updated the schedule (${REVENUE_PROCEDURES[year]}): required contributions run from **${minNow}%** to **${maxNow}%** of income, and the 400% FPL ceiling remains.

No extension of the enhanced credits has been enacted, so these are the rules for ${year} coverage.`,
      showContributionChart: true,
      chartPolicies: ["current2026", `current${year}`],
    },

    // PART 2: Household example
    {
      id: "example_intro",
      title: "Example: a middle-income household",
      content: `To illustrate the impact, consider a 45-year-old single adult in Lebanon County, Pennsylvania, earning **${formatDollars(data.example_income)}** a year—about **${yNow.fpl_percent}% of the federal poverty level** in ${year}.

In 2025, under the enhanced credits, this household:
• Paid **${monthly(y2025.slcsp)}/month** for the benchmark plan (SLCSP)
• Received a **${monthly(y2025.ptc)}/month** tax credit
• Paid a net premium of **${monthly(netPremium(y2025))}/month**`,
      cliffRows: ["2025"],
      showSlcsp: true,
    },
    {
      id: "example_after",
      title: `2026 and ${year}: after expiration`,
      content: `In 2026, this household:

**a) Faced a higher premium** for its benchmark plan: ${monthly(y2026.slcsp)}/month (${percentChange(y2025.slcsp, y2026.slcsp)} from 2025)

**b) Lost its subsidy** entirely: the tax credit dropped from ${monthly(y2025.ptc)}/month to **$0** because its income is above the 400% FPL ceiling

In ${year}, the benchmark plan costs **${monthly(yNow.slcsp)}/month** and current law still provides no credit, so the net premium is **${monthly(netPremium(yNow))}/month**: ${monthly(netChange)}/month (${percentChange(netPremium(y2025), netPremium(yNow))}) more than in 2025.`,
      cliffRows: ["2025", "2026", String(year)],
      showSlcsp: true,
      showBreakdown: true,
    },

    // PART 3: Policy options for this household
    {
      id: "reform_options",
      title: "Policy options",
      content: `Two bills in Congress would restore credits above 400% FPL in ${year}. Neither has been enacted.

**H.R. 1834:** Extends the enhanced credits, with the 8.5% cap, through 2028. It passed the House on January 8, 2026.
• Tax credit: **${monthly(hr1834.ptc)}/month** → Net premium: **${monthly(netPremium(hr1834))}/month**

**Bipartisan Health Insurance Affordability Act:** Introduced by Rep. Dunn (R-FL) and Rep. Schneider (D-IL) on December 9, 2025, this bill extends eligibility to 700% FPL with a 9.25% cap
• Tax credit: **${monthly(bill700.ptc)}/month** → Net premium: **${monthly(netPremium(bill700))}/month**`,
      cliffRows: [String(year), "hr1834", "bill700"],
    },

    // PART 4: Health programs overview (using PA single adult)
    {
      id: "health_programs",
      title: "The full picture: health coverage programs",
      content: `Premium tax credits are one part of the health coverage landscape. Americans may also qualify for:

• **Medicaid:** Free coverage for low-income households (eligibility varies by state)
• **Marketplace subsidies:** PTCs for those not eligible for other programs

The chart shows how these programs interact across income levels for our Pennsylvania example in ${year}.`,
      chartState: "all_programs",
    },
    {
      id: "medicaid",
      title: "Medicaid coverage",
      content: `**Medicaid** provides coverage for low-income Americans. Pennsylvania expanded Medicaid, so adults qualify up to **138% FPL**.

For our 45-year-old, this means Medicaid covers incomes up to about ${medicaidLimit(data)}. If they earn more, they may be eligible for premium tax credits (PTCs).`,
      chartState: "medicaid_focus",
    },
    {
      id: "reforms_chart",
      title: "Premium tax credits under different policies",
      content: `The chart shows premium tax credits across income levels in ${year} under three scenarios:

• **Gray line:** Current law
• **Blue line:** H.R. 1834
• **Purple line:** Bipartisan Health Insurance Affordability Act

Current law drops to zero at 400% FPL. Both bills continue providing credits at higher incomes.`,
      chartState: "both_reforms",
    },
    {
      id: "ira_impact_chart",
      title: "H.R. 1834: the difference",
      content: `The **blue shaded area** represents the additional premium tax credits available under H.R. 1834 compared to current law.

For this Pennsylvania household:
• Below 400% FPL: H.R. 1834 provides **lower required contributions**
• Above 400% FPL: H.R. 1834 provides **credits** where current law provides none

The size of the shaded area shows the dollar value of the difference at each income level.`,
      chartState: "ira_impact",
    },

    // PART 5: Household case studies - links to explorer
    {
      id: "explore_households",
      title: "Explore different households",
      content: `The impact of ACA policy changes varies by household type, location, and income level.

Click below to explore how four different households are affected—with details on Medicaid expansion, CHIP eligibility, and the subsidy cliff for each.`,
      chartState: "both_reforms",
      showHouseholdExplorerLink: true,
    },
  ];
}

const SECTIONS = buildSections(cliffDemoData);

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
  if (typeof window === "undefined") {
    return "main";
  }
  const hash = window.location.hash.slice(1); // Remove the #
  const [route] = hash.split("?"); // Ignore query params for page routing
  return PAGE_ROUTES[route] || "main";
}

// Check if running in embedded mode (iframe)
function isEmbedded() {
  if (typeof window === "undefined") {
    return false;
  }
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
    if (currentSection.cliffRows) {
      return (
        <CliffComparisonTable
          data={cliffDemoData}
          rows={currentSection.cliffRows}
          showSlcsp={currentSection.showSlcsp}
          showBreakdown={currentSection.showBreakdown}
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
            <h1>ACA Premium Tax Credits</h1>
            <p className="subtitle">
              How the expiration of the enhanced credits, and proposals to extend them, affect health insurance costs
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
