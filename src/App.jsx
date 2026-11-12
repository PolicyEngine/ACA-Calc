import { useState, useRef, useEffect } from "react";
import ScrollSection from "./components/ScrollSection";
import ContributionScheduleChart from "./components/ContributionScheduleChart";
import ExampleHouseholdsTable from "./components/ExampleHouseholdsTable";
import NationalImpactChart from "./components/NationalImpactChart";
import PremiumChart from "./components/PremiumChart";
import Calculator from "./components/Calculator";
import "./App.css";

// Precomputed with policyengine-us: the Pennsylvania example across incomes
// (precompute_cliff_household.py), four example households
// (precompute_households.py), the contribution schedules
// (precompute_contribution_schedules.py) and the national figures
// (precompute_national.py).
import cliffDemoData from "./data/households/cliff_demo.json";
import examples from "./data/households/examples.json";
import schedules from "./data/contribution_schedules.json";
import national from "./data/national_impacts.json";

const formatDollars = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
const monthly = (annual) => formatDollars(annual / 12);
const percentChange = (from, to, digits = 1) => {
  const change = (100 * (to - from)) / from;
  return `${change >= 0 ? "+" : "−"}${Math.abs(change).toFixed(digits)}%`;
};
const billions = (value) => `$${(value / 1e9).toFixed(1)} billion`;
const millions = (value) => `${(value / 1e6).toFixed(1)} million`;
// A count of people: millions from a million up, else to the nearest thousand.
const people = (value) =>
  value >= 1e6 ? millions(value) : (Math.round(value / 1000) * 1000).toLocaleString("en-US");
const share = (value, digits = 1) => `${(100 * value).toFixed(digits)}%`;
const ordinal = (n) => `${n}${{ 1: "st", 2: "nd", 3: "rd" }[n] || "th"}`;

// The lowest and highest share of income a schedule charges where it gives a credit.
const rateRange = (key) => {
  const rates = schedules.schedules[key].filter((rate) => rate !== null && rate > 0);
  return [Math.min(...rates).toFixed(2), Math.max(...rates).toFixed(2)];
};

function buildSections() {
  const year = examples.year;
  const priorYear = examples.prior_year;
  const household = Object.fromEntries(examples.examples.map((example) => [example.key, example]));
  const values = (key) => ({
    prior: household[key].scenarios[`current_${priorYear}`],
    current: household[key].scenarios[`current_${year}`],
    revived: household[key].scenarios[`hr1834_${year}`],
  });
  const texas = values("texas_single");
  const florida = values("florida_family");
  const pennsylvania = values("pennsylvania_single");
  const california = values("california_couple");

  const benchmarkChanges = examples.examples.map((example) => {
    const { prior, current } = values(example.key);
    return (100 * (current.slcsp - prior.slcsp)) / prior.slcsp;
  });
  const [min2026, max2026] = rateRange(`current_${priorYear}`);
  const [minNow, maxNow] = rateRange(`current_${year}`);

  // The Pennsylvania example across incomes: where current law's credit ends
  // and where H.R. 1834's would.
  const cliffIncome = 4 * cliffDemoData.fpl;
  let revivedEnd = 0;
  cliffDemoData.ptc_ira.forEach((credit, i) => {
    if (credit > 0) revivedEnd = cliffDemoData.income[i];
  });

  // National figures.
  const lawPrior = national.current_law[String(priorYear)];
  const lawNow = national.current_law[String(year)];
  const enhanced = national.enhanced;
  const aboveCliff = national.by_fpl
    .filter((band) => band.band.startsWith("400%") || band.band.startsWith("Above"))
    .reduce((sum, band) => sum + band.reform_ptc - band.baseline_ptc, 0);
  const deciles = national.deciles;
  const largestGain = deciles.reduce((a, b) => (b.absolute_change > a.absolute_change ? b : a));
  const largestShare = deciles.reduce((a, b) => (b.relative_change > a.relative_change ? b : a));
  const decilesGaining = deciles.filter((row) => row.absolute_change > 0).length;
  const winners = national.winners_losers.all;
  const gaining = winners.gain_more_than_5pct + winners.gain_less_than_5pct;
  const losing = winners.lose_more_than_5pct + winners.lose_less_than_5pct;
  const poverty = national.poverty.spm;
  const deep = national.poverty.deep;
  const povertyChange = (group) =>
    percentChange(group.baseline_rate, group.reform_rate);
  const lifted = poverty.all.baseline_headcount - poverty.all.reform_headcount;
  const { baseline: inequalityBefore, reform: inequalityAfter } = national.inequality;

  return [
    // PART 1: 2027 premiums under current law
    {
      id: "premiums",
      title: `Benchmark premiums rise in ${year}`,
      content: `The premium tax credit is pegged to a **benchmark plan**: the second-lowest-cost silver plan where a household lives.

For ${year}, benchmark premiums rise for each of these four households, by **${Math.min(...benchmarkChanges).toFixed(1)}%** to **${Math.max(...benchmarkChanges).toFixed(1)}%**.

Across all tax units receiving a credit, PolicyEngine estimates the average benchmark premium at **${monthly(lawNow.mean_benchmark_premium)}/month** in ${year}, against ${monthly(lawPrior.mean_benchmark_premium)} in ${priorYear} (${percentChange(lawPrior.mean_benchmark_premium, lawNow.mean_benchmark_premium)}).`,
      chart: { type: "examples", view: "benchmark" },
    },
    {
      id: "below_cliff",
      title: "Below 400% FPL, the credit absorbs the increase",
      content: `Current law limits what a household pays for the benchmark plan to a share of its income, from **${minNow}%** to **${maxNow}%** in ${year} (${min2026}% to ${max2026}% in ${priorYear}). The credit pays the rest of the premium, so it grows when premiums do.

The Texas adult earning ${formatDollars(household.texas_single.income)} pays **${monthly(texas.current.net_premium)}/month** for the benchmark plan in ${year}, against ${monthly(texas.prior.net_premium)} in ${priorYear}, while the premium rises from ${monthly(texas.prior.slcsp)} to ${monthly(texas.current.slcsp)}.

The Florida family earning ${formatDollars(household.florida_family.income)} pays ${monthly(florida.current.net_premium)}/month in ${year}, against ${monthly(florida.prior.net_premium)} in ${priorYear}.`,
      chart: { type: "schedule", policies: [`current${priorYear}`, `current${year}`] },
    },
    {
      id: "above_cliff",
      title: "Above 400% FPL, households pay all of it",
      content: `The enhanced credits that reached incomes above 400% FPL expired at the end of 2025. Under current law, households there get no credit and pay the whole benchmark premium, the increase included.

The Pennsylvania adult earning ${formatDollars(household.pennsylvania_single.income)} pays **${monthly(pennsylvania.current.net_premium)}/month** in ${year}, ${monthly(pennsylvania.current.net_premium - pennsylvania.prior.net_premium)} more than in ${priorYear}.

The California couple in their 60s earning ${formatDollars(household.california_couple.income)} pays **${monthly(california.current.net_premium)}/month**, ${monthly(california.current.net_premium - california.prior.net_premium)} more than in ${priorYear}: ${share(california.current.net_premium / household.california_couple.income, 0)} of its income.

The chart shows the Pennsylvania adult at every income: the payment jumps to the full premium above 400% FPL (${formatDollars(cliffIncome)}).`,
      chart: { type: "premium", lines: ["prior", "current"] },
    },

    // PART 2: Reviving the enhanced credits
    {
      id: "enhanced",
      title: "H.R. 1834 would revive the enhanced credits",
      content: `From 2021 through 2025, the American Rescue Plan Act and the Inflation Reduction Act enhanced the credits: households paid **0%** of income for the benchmark plan up to 150% FPL, and at most **8.5%** at any income, with no income limit.

H.R. 1834 would revive that schedule for 2026 through 2028. It passed the House on January 8, 2026; it has not been enacted.

The chart compares the enhanced schedule with current law for ${year}.`,
      chart: { type: "schedule", policies: [`current${year}`, "enhanced"] },
    },
    {
      id: "enhanced_households",
      title: "What it would mean for these households",
      content: `Under H.R. 1834, each household would pay less for its benchmark plan in ${year}:
• Texas adult: **${monthly(texas.revived.net_premium)}/month**, against ${monthly(texas.current.net_premium)} under current law
• Florida family: **${monthly(florida.revived.net_premium)}/month**, against ${monthly(florida.current.net_premium)}
• Pennsylvania adult: **${monthly(pennsylvania.revived.net_premium)}/month**, against ${monthly(pennsylvania.current.net_premium)}
• California couple: **${monthly(california.revived.net_premium)}/month**, against ${monthly(california.current.net_premium)}

The two households above 400% FPL would pay 8.5% of their income instead of the full premium.`,
      chart: { type: "examples", view: "net" },
    },
    {
      id: "enhanced_by_income",
      title: "Across incomes",
      content: `For the Pennsylvania adult, H.R. 1834 would lower the payment at every income above Pennsylvania's Medicaid limit (138% FPL) up to about **${formatDollars(revivedEnd)}**, where 8.5% of income reaches the full benchmark premium.

Under current law the payment rises with income up to 400% FPL, then jumps to the full premium of ${monthly(pennsylvania.current.slcsp)}/month.`,
      chart: { type: "premium", lines: ["prior", "current", "revived"] },
    },

    // PART 3: National effects
    {
      id: "national_cost",
      title: "Cost and reach",
      content: `PolicyEngine estimates that H.R. 1834 would raise federal spending on premium tax credits by **${billions(national.budget.federal_cost)}** in ${year}, from ${billions(lawNow.total_ptc)} under current law to ${billions(enhanced.total_ptc)}. Under current law, spending is ${billions(lawPrior.total_ptc)} in ${priorYear}.

The number of people receiving a credit would rise from ${millions(lawNow.people_receiving)} to **${millions(enhanced.people_receiving)}**, including ${millions(national.recipients.people_newly_receiving)} who get no credit under current law.

Of the added spending, ${share(aboveCliff / national.budget.federal_cost, 0)} goes to tax units above 400% FPL.`,
      chart: { type: "national", mode: "spending" },
    },
    {
      id: "national_deciles",
      title: "Gains by income decile",
      content: `Ranking households by net income into deciles of equal population, average net income rises in ${decilesGaining} of 10 deciles.

The average gain is largest in the **${ordinal(largestGain.decile)} decile**, at ${formatDollars(largestGain.absolute_change)} a year. Relative to net income, it is largest in the ${ordinal(largestShare.decile)} decile, at ${largestShare.relative_change.toFixed(2)}%.`,
      chart: { type: "national", mode: "deciles" },
    },
    {
      id: "national_winners",
      title: "Who gains",
      content: `**${share(gaining)}** of people live in households whose net income rises under H.R. 1834; ${share(winners.gain_more_than_5pct)} gain more than 5%.

${losing > 0 ? `${share(losing)} of people live in households whose net income falls.` : "No household's net income falls: the bill only raises credits."} The rest see no change: no one in their household gets a credit under either policy.`,
      chart: { type: "national", mode: "winners" },
    },
    {
      id: "national_poverty",
      title: "Poverty",
      content: `The Supplemental Poverty Measure subtracts what households pay for health coverage, so a larger credit, which lowers the premiums enrollees pay, raises their resources. H.R. 1834 changes the poverty rate from ${share(poverty.all.baseline_rate, 2)} to **${share(poverty.all.reform_rate, 2)}** (${povertyChange(poverty.all)}): ${people(Math.abs(lifted))} ${lifted >= 0 ? "fewer" : "more"} people in poverty.

By age, poverty changes ${povertyChange(poverty.child)} for children, ${povertyChange(poverty.adult)} for adults 18 to 64 and ${povertyChange(poverty.senior)} for seniors. Deep poverty, below half the poverty line, changes ${povertyChange(deep.all)}.`,
      chart: { type: "national", mode: "poverty" },
    },
    {
      id: "national_inequality",
      title: "Inequality",
      content: `The Gini index of household net income moves from ${inequalityBefore.gini.toFixed(4)} to **${inequalityAfter.gini.toFixed(4)}** (${percentChange(inequalityBefore.gini, inequalityAfter.gini, 2)}).

The top 10%'s share of net income moves from ${share(inequalityBefore.top_10_share, 2)} to ${share(inequalityAfter.top_10_share, 2)}, and the top 1%'s from ${share(inequalityBefore.top_1_share, 2)} to ${share(inequalityAfter.top_1_share, 2)}.`,
      chart: { type: "national", mode: "inequality" },
    },
    {
      id: "methodology",
      title: "How we estimated this",
      content: `We ran PolicyEngine US ${national.model_version} over its 2024 microdata, projected to ${priorYear} and ${year}, under current law and with H.R. 1834's schedule. The household examples use the same model and each county's benchmark premiums.

PolicyEngine's household net income leaves out health coverage, including the premium tax credit, so we add each household's change in its credit to its net income. Its poverty measure counts the credit already: it subtracts what households pay for coverage, including marketplace premiums net of the credit.

The estimates are static: the same people enroll under each policy, so they leave out people who would start or stop buying coverage as credits change. Marketplace enrollment comes from the 2024 data.`,
      chart: { type: "examples", view: "net" },
      showCalculatorButton: true,
    },
  ];
}

const SECTIONS = buildSections();

// URL routing helpers. The Explore Households page is gone; its old links
// open the Overview.
const PAGE_ROUTES = {
  "": "main",
  "overview": "main",
  "households": "main",
  "calculator": "calculator",
};

const ROUTE_PAGES = {
  "main": "",
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

  // What the sticky panel shows for the current section
  const renderChartArea = () => {
    const { chart } = currentSection;
    switch (chart.type) {
      case "examples":
        return <ExampleHouseholdsTable view={chart.view} />;
      case "schedule":
        return <ContributionScheduleChart showPolicies={chart.policies} />;
      case "premium":
        return (
          <PremiumChart
            data={cliffDemoData}
            lines={chart.lines}
            title={`What a ${cliffDemoData.household_info.age}-year-old in ${cliffDemoData.household_info.location} pays for the benchmark plan`}
          />
        );
      case "national":
        return <NationalImpactChart mode={chart.mode} />;
      default:
        return null;
    }
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
              onOpenCalculator={() => navigateToPage("calculator")}
            />
          ))}
        </div>
      </main>
    </>
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
              How 2027 premiums change under current law, and what reviving the enhanced credits would do
            </p>
            <div className="page-tabs">
              <button
                className={`page-tab ${currentPage === "main" ? "active" : ""}`}
                onClick={() => navigateToPage("main")}
              >
                Overview
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
