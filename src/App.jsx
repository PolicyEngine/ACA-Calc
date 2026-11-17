import { useState, useEffect } from "react";
import ContributionScheduleChart from "./components/ContributionScheduleChart";
import ExampleHouseholdsTable from "./components/ExampleHouseholdsTable";
import HouseholdYearTable, { householdAt } from "./components/HouseholdYearTable";
import PremiumChart from "./components/PremiumChart";
import MarginalRateChart from "./components/MarginalRateChart";
import Calculator from "./components/Calculator";
import Methodology from "./components/Methodology";
import useActiveSection from "./components/useActiveSection";
import useMediaQuery from "./components/useMediaQuery";
import { Reveal } from "./components/Motion";
import "./App.css";

// Precomputed with policyengine-us: the Pennsylvania example across incomes
// (precompute_cliff_household.py), four example households
// (precompute_households.py) and the contribution schedules
// (precompute_contribution_schedules.py). The national estimates
// (precompute_national.py, national_impacts.json) are held off the page until
// they are validated.
import cliffDemoData from "./data/households/cliff_demo.json";
import examples from "./data/households/examples.json";
import schedules from "./data/contribution_schedules.json";

const formatDollars = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
const monthly = (annual) => formatDollars(annual / 12);
const share = (value, digits = 1) => `${(100 * value).toFixed(digits)}%`;

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

  // The same Pennsylvania adult at two incomes, below and above 400% FPL
  // (HouseholdYearTable shows the same two).
  const below = householdAt(50000);
  const above = householdAt(household.pennsylvania_single.income);
  const aboutFpl = (income, step) => Math.round((100 * income) / cliffDemoData.fpl / step) * step;
  const shareOfIncome = (value, income) => `${((100 * value) / income).toFixed(2)}%`;

  // The Pennsylvania example across incomes: where current law's credit ends,
  // and where H.R. 1834's would: the income at which the enhanced schedule's
  // top share (8.5%) reaches the benchmark premium, to the nearest $50.
  const cliffIncome = 4 * cliffDemoData.fpl;
  const enhancedCap = Math.max(...schedules.schedules.enhanced.filter((rate) => rate !== null));
  const revivedEnd = Math.round(pennsylvania.current.slcsp / (enhancedCap / 100) / 50) * 50;

  // The Pennsylvania adult's marginal tax rates in 2027: the share of each
  // extra $1,000 of earnings lost to taxes and a smaller credit.
  const incomes = cliffDemoData.income;
  const median = (values) => {
    const sorted = [...values].sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)];
  };
  const typicalRate = (rates, lowPercent, highPercent) =>
    100 *
    median(
      rates.filter(
        (_, i) =>
          incomes[i] >= (lowPercent / 100) * cliffDemoData.fpl &&
          incomes[i] <= (highPercent / 100) * cliffDemoData.fpl
      )
    );
  // The step on the income axis that crosses 400% FPL.
  const cliffStep = incomes.findIndex((value) => value > cliffIncome) - 1;
  const creditLost = cliffDemoData.ptc_baseline[cliffStep] - cliffDemoData.ptc_baseline[cliffStep + 1];
  const netLost =
    cliffDemoData.net_income_baseline[cliffStep] - cliffDemoData.net_income_baseline[cliffStep + 1];
  const cliffRate = 100 * cliffDemoData.mtr_baseline[cliffStep];
  // How much higher H.R. 1834's rate is than current law's between 400% FPL
  // and the end of its credit.
  const pointsHigher = typicalRate(
    cliffDemoData.mtr_ira.map((rate, i) => rate - cliffDemoData.mtr_baseline[i]),
    420,
    (100 * (revivedEnd - 2000)) / cliffDemoData.fpl
  );

  return [
    // PART 1: How the credits work
    {
      id: "how_credits_work",
      title: "How premium tax credits work",
      content: `The Affordable Care Act's **premium tax credits** (PTCs) reduce premiums for enrollees who purchase health insurance through the marketplace.

The PTCs cap how much of their income enrollees are required to pay for a **benchmark health plan**—the second-lowest-cost silver plan (SLCSP) in their area. If the benchmark plan costs more than the required contribution, the government pays the difference as a tax credit.

The chart shows the share of income a household pays for the benchmark plan under current law in ${year}: from **${minNow}%** to **${maxNow}%**, with no credit above 400% of the federal poverty line (FPL).`,
      chart: { type: "schedule", policies: [`current${year}`] },
    },
    {
      id: "enhancements",
      title: "The 2021–2025 enhancements",
      content: `The American Rescue Plan Act (ARPA) of 2021 and the Inflation Reduction Act (IRA) of 2022 enhanced the subsidies from 2021 through 2025:
• Households paid **0%** of income for the benchmark plan up to 150% FPL
• No household paid more than **8.5%** of its income
• Credits reached incomes above 400% FPL, with no income limit

The chart compares the enhanced schedule with current law for ${year}.`,
      chart: { type: "schedule", policies: [`current${year}`, "enhanced"] },
    },
    {
      id: "expiration",
      title: "The enhancements expired",
      content: `The enhancements expired at the end of 2025. Under the original rules, which returned in 2026, enrollees pay a larger share of their income for the benchmark plan, and those above 400% FPL get no credit.

The IRS sets the shares each year: **${min2026}%** to **${max2026}%** of income in ${priorYear}, and **${minNow}%** to **${maxNow}%** in ${year}.`,
      chart: { type: "schedule", policies: [`current${priorYear}`, `current${year}`] },
    },

    // PART 2: A household facing the 2027 increase
    {
      id: "household_prior",
      title: "Example: two middle-income households",
      content: `Consider two ${cliffDemoData.household_info.age}-year-old single adults in Lebanon County, Pennsylvania: one earning **${formatDollars(below.income)}** a year, about ${aboutFpl(below.income, 5)}% of the federal poverty line, and one earning **${formatDollars(above.income)}**, about ${aboutFpl(above.income, 50)}%.

In ${priorYear} the benchmark plan costs both **${monthly(below.prior.slcsp)}/month**. The ${formatDollars(below.income)} household gets a credit of ${monthly(below.prior.ptc)}/month and pays ${monthly(below.prior.net)}/month, ${shareOfIncome(below.prior.net, below.income)} of its income. The ${formatDollars(above.income)} household, above 400% FPL, gets no credit and pays the whole premium.`,
      chart: { type: "household", columns: ["prior"] },
    },
    {
      id: "household_current",
      title: `${year}: the premium rises again`,
      content: `For ${year}, the benchmark premium rises by ${monthly(above.current.slcsp - above.prior.slcsp)} (${((100 * (above.current.slcsp - above.prior.slcsp)) / above.prior.slcsp).toFixed(1)}%), to **${monthly(above.current.slcsp)}/month**.

Below 400% FPL, the credit absorbs the increase. The ${formatDollars(below.income)} household's credit rises by ${monthly(below.current.ptc - below.prior.ptc)} to ${monthly(below.current.ptc)}/month, so what it pays rises only ${monthly(below.current.net - below.prior.net)}, to **${monthly(below.current.net)}/month**, because its share of income rises from ${shareOfIncome(below.prior.net, below.income)} to ${shareOfIncome(below.current.net, below.income)}.

Above 400% FPL, the ${formatDollars(above.income)} household still gets no credit, so it pays the whole increase: **${monthly(above.current.net)}/month**, ${share(above.current.net / above.income, 0)} of its income.

Lebanon County is in Pennsylvania's highest-cost rating area in the model's ${year} premium data. The model's benchmark premiums for ${priorYear} and ${year} come from KFF's premium data for each rating area.`,
      chart: { type: "household", columns: ["prior", "current"] },
    },

    // PART 3: A clean extension of the enhanced credits
    {
      id: "extension",
      title: "What a clean extension would do",
      content: `A clean extension of the enhanced credits would bring back the 2021–2025 schedule unchanged. H.R. 1834 would do this for 2026 through 2028. It passed the House on January 8, 2026; it has not been enacted.

Under the extension, neither household would pay more than 8.5% of its income for the benchmark plan in ${year}. The ${formatDollars(below.income)} household would pay **${monthly(below.revived.net)}/month**, against ${monthly(below.current.net)} under current law. The ${formatDollars(above.income)} household would pay **${monthly(above.revived.net)}/month**, with a credit of ${monthly(above.revived.ptc)}/month, against ${monthly(above.current.net)}/month and no credit under current law.`,
      chart: { type: "household", columns: ["prior", "current", "revived"] },
    },
    {
      id: "across_incomes",
      title: "Across incomes",
      content: `For a ${cliffDemoData.household_info.age}-year-old in Lebanon County, the extension would lower the payment at every income above Pennsylvania's Medicaid limit (138% FPL) up to about **${formatDollars(revivedEnd)}**, where 8.5% of its income reaches the benchmark premium of ${formatDollars(pennsylvania.current.slcsp)} a year.

Under current law the payment rises with income up to 400% FPL (${formatDollars(cliffIncome)}), then jumps to the full premium of ${monthly(pennsylvania.current.slcsp)}/month.`,
      chart: { type: "premium", lines: ["prior", "current", "revived"] },
    },
    {
      id: "marginal_rates",
      title: "No cliff at 400% FPL",
      content: `A household's **marginal tax rate** is the share of an extra dollar of earnings it loses to taxes and to a smaller credit.

Under current law, the Pennsylvania adult's credit ends at 400% FPL (${formatDollars(cliffIncome)}). Earning ${formatDollars(incomes[cliffStep + 1] - incomes[cliffStep])} more, from ${formatDollars(incomes[cliffStep])} to ${formatDollars(incomes[cliffStep + 1])}, costs it ${formatDollars(creditLost)} of credit, so its net income falls by **${formatDollars(netLost)}**: a marginal tax rate of ${cliffRate.toFixed(0)}% on that ${formatDollars(incomes[cliffStep + 1] - incomes[cliffStep])}.

Under the extension there is no cliff. Above 400% FPL the household pays at most 8.5% of its income for the benchmark plan, so each extra dollar lowers its credit by 8.5 cents. Its marginal tax rate is **${pointsHigher.toFixed(1)} points higher** than under current law at each income from 400% FPL until the credit ends at about ${formatDollars(revivedEnd)}; beyond that, the two are the same.`,
      chart: { type: "mtr" },
    },

    // PART 4: Other households
    {
      id: "other_households",
      title: "Four example households",
      content: `Benchmark premiums rise in ${year} for each of four example households, by **${Math.min(...benchmarkChanges).toFixed(1)}%** to **${Math.max(...benchmarkChanges).toFixed(1)}%**.

Below 400% FPL, the credit grows with the premium, so what households pay barely changes: the Texas adult earning ${formatDollars(household.texas_single.income)} pays ${monthly(texas.current.net_premium)}/month for the benchmark plan in ${year}, against ${monthly(texas.prior.net_premium)} in ${priorYear}, and the Florida family earning ${formatDollars(household.florida_family.income)} pays ${monthly(florida.current.net_premium)}, against ${monthly(florida.prior.net_premium)}.

Above 400% FPL, the California couple in their 60s earning ${formatDollars(household.california_couple.income)} pays the whole premium, **${monthly(california.current.net_premium)}/month**: ${share(california.current.net_premium / household.california_couple.income, 0)} of its income. Like the Pennsylvania adult, it lives in its state's highest-cost rating area in the model's ${year} premium data.

The table shows what each would pay under current law and under the extension.`,
      chart: { type: "examples", view: "net" },
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
  "methodology": "methodology",
};

const ROUTE_PAGES = {
  "main": "",
  "calculator": "calculator",
  "methodology": "methodology",
};

const ArrowIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <path d="M5 12h14M12 5l7 7-7 7" />
  </svg>
);

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

// **bold** spans within a line.
function Inline({ text }) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part
  );
}

// A section's text: paragraphs split by blank lines; lines starting with "•"
// become a list.
function Prose({ content }) {
  return content.split("\n\n").map((block, i) => {
    const lines = block.split("\n");
    const bullets = lines.filter((line) => line.startsWith("•"));
    if (!bullets.length) return <p key={i}><Inline text={block} /></p>;
    const lead = lines.filter((line) => !line.startsWith("•")).join(" ");
    return (
      <div key={i}>
        {lead && <p><Inline text={lead} /></p>}
        <ul>
          {bullets.map((line, j) => (
            <li key={j}><Inline text={line.replace(/^•\s*/, "")} /></li>
          ))}
        </ul>
      </div>
    );
  });
}

function Chart({ chart }) {
  switch (chart.type) {
    case "examples":
      return <ExampleHouseholdsTable view={chart.view} />;
    case "household":
      return <HouseholdYearTable columns={chart.columns} />;
    case "schedule":
      return <ContributionScheduleChart showPolicies={chart.policies} />;
    case "premium":
      return (
        <PremiumChart
          data={cliffDemoData}
          lines={chart.lines}
          title={`What a ${cliffDemoData.household_info.age}-year-old in ${cliffDemoData.household_info.location} pays for the benchmark plan, per month`}
        />
      );
    case "mtr":
      return (
        <MarginalRateChart
          data={cliffDemoData}
          title={`Marginal tax rate of a ${cliffDemoData.household_info.age}-year-old in ${cliffDemoData.household_info.location}, ${cliffDemoData.year}`}
        />
      );
    default:
      return null;
  }
}

// The story's parts, each opening with a heading, in the order the earlier
// version of the app told it: how the credits work, one household, a policy
// option, other households.
const PARTS = {
  how_credits_work: "How the credits work",
  household_prior: `Two households facing the ${examples.year} increase`,
  extension: "A clean extension of the enhanced credits",
  other_households: "Other households",
};

function App() {
  const [currentPage, setCurrentPage] = useState(() => getPageFromHash());
  const [embedded] = useState(() => isEmbedded());
  // The split layout's breakpoint (App.css): wide screens pin the chart.
  const wide = useMediaQuery("(min-width: 1025px)");
  const activeId = useActiveSection(SECTIONS, currentPage === "main" && wide);
  const activeSection = SECTIONS.find((section) => section.id === activeId) || SECTIONS[0];

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

  // The Overview, as the earlier version of the app laid it out: on wide
  // screens the active section's chart stays pinned on the left while the
  // text scrolls past in cards on the right; on narrower screens, one column
  // with each chart under its text.
  const renderMainPage = () => (
    <div className="overview">
      <div className="scrolly">
        {wide && (
          <div className="scrolly-chart">
            <figure className="scrolly-sticky" aria-label={activeSection.title}>
              <div key={activeSection.id} className="scrolly-swap">
                <Chart chart={activeSection.chart} />
              </div>
            </figure>
          </div>
        )}
        <main className="scrolly-text">
          {SECTIONS.map((section) => (
            <section
              key={section.id}
              id={section.id}
              className={`story-section scroll-card${wide && section.id === activeSection.id ? " active" : ""}`}
            >
              {PARTS[section.id] && <p className="story-part">{PARTS[section.id]}</p>}
              <h2>{section.title}</h2>
              <div className="story-prose">
                <Prose content={section.content} />
              </div>
              {!wide && section.chart && (
                <Reveal as="figure" className="story-figure">
                  <Chart chart={section.chart} />
                </Reveal>
              )}
            </section>
          ))}
          <div className="story-ctas">
            <button type="button" onClick={() => navigateToPage("calculator")} className="story-cta">
              Calculate your household
              <ArrowIcon />
            </button>
            <button type="button" onClick={() => navigateToPage("methodology")} className="story-cta secondary">
              How we estimated this
              <ArrowIcon />
            </button>
          </div>
        </main>
      </div>
    </div>
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
              How 2027 premiums change under current law, and what a clean extension of the enhanced credits would do
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
              <button
                className={`page-tab ${currentPage === "methodology" ? "active" : ""}`}
                onClick={() => navigateToPage("methodology")}
              >
                Methodology
              </button>
            </div>
          </div>
        </header>
      )}

      {currentPage === "main" && renderMainPage()}
      {currentPage === "calculator" && renderCalculatorPage()}
      {currentPage === "methodology" && <Methodology onCalculator={() => navigateToPage("calculator")} />}

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
