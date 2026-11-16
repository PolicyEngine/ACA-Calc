import { useState, useEffect } from "react";
import ContributionScheduleChart from "./components/ContributionScheduleChart";
import ExampleHouseholdsTable from "./components/ExampleHouseholdsTable";
import NationalImpactChart from "./components/NationalImpactChart";
import PremiumChart from "./components/PremiumChart";
import MarginalRateChart from "./components/MarginalRateChart";
import Calculator from "./components/Calculator";
import StoryRail from "./components/StoryRail";
import { CountUp, Reveal } from "./components/Motion";
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
import cbo from "./data/cbo_estimate.json";

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

  // National figures.
  const lawPrior = national.current_law[String(priorYear)];
  const lawNow = national.current_law[String(year)];
  const enhanced = national.enhanced;
  const benchmarkRise =
    (100 * (lawNow.mean_benchmark_premium - lawPrior.mean_benchmark_premium)) /
    lawPrior.mean_benchmark_premium;
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

Across all tax units receiving a credit, PolicyEngine estimates the average benchmark premium at ${monthly(lawNow.mean_benchmark_premium)}/month in ${year}, against ${monthly(lawPrior.mean_benchmark_premium)} in ${priorYear}, **an average ${benchmarkRise >= 0 ? "increase" : "decrease"} of ${Math.abs(benchmarkRise).toFixed(1)}%**.`,
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
    {
      id: "marginal_rates",
      title: "No cliff at 400% FPL",
      content: `A household's **marginal tax rate** is the share of an extra dollar of earnings it loses to taxes and to a smaller credit.

Under current law, the Pennsylvania adult's credit ends at 400% FPL (${formatDollars(cliffIncome)}). Earning ${formatDollars(incomes[cliffStep + 1] - incomes[cliffStep])} more, from ${formatDollars(incomes[cliffStep])} to ${formatDollars(incomes[cliffStep + 1])}, costs it ${formatDollars(creditLost)} of credit, so its net income falls by **${formatDollars(netLost)}**: a marginal tax rate of ${cliffRate.toFixed(0)}% on that ${formatDollars(incomes[cliffStep + 1] - incomes[cliffStep])}.

Under H.R. 1834 there is no cliff. Above 400% FPL the household pays at most 8.5% of its income for the benchmark plan, so each extra dollar lowers its credit by 8.5 cents. Its marginal tax rate is **${pointsHigher.toFixed(1)} points higher** than under current law at each income from 400% FPL until the credit ends at about ${formatDollars(revivedEnd)}; beyond that, the two are the same.`,
      chart: { type: "mtr" },
    },

    // PART 3: National effects
    {
      id: "national_cost",
      title: "Cost and reach",
      content: `PolicyEngine estimates that H.R. 1834 would raise federal spending on premium tax credits by **${billions(national.budget.federal_cost)}** in ${year}. The estimate is static: it holds enrollment fixed, so it leaves out people who would start buying coverage when credits grow, and lower premiums as healthier people enroll.

The Congressional Budget Office, whose estimate includes both, expects the bill to add **${billions(cbo.estimate.deficit_increase_fy2027)}** to the deficit in fiscal year ${year} and ${billions(cbo.estimate.deficit_increase_10_year)} over ${cbo.estimate.window}. In CBO's estimate, ${millions(cbo.estimate.insured_increase_2027)} more people would have health insurance in ${year}, and benchmark premiums would be ${share(-cbo.estimate.benchmark_premium_change_2027)} lower.

The number of people receiving a credit would rise from ${millions(lawNow.people_receiving)} to **${millions(enhanced.people_receiving)}**, including ${millions(national.recipients.people_newly_receiving)} who get no credit under current law. Of the added spending, ${share(aboveCliff / national.budget.federal_cost, 0)} goes to tax units above 400% FPL.`,
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

The credit figures are the credit each tax unit uses: the credit it is eligible for, capped at the premium of the plan it enrolls in. Household net income counts that credit as a refundable tax credit, and the poverty measure counts it through the lower premiums enrollees pay.

Above 400% FPL, the survey's marketplace take-up flags would make far more people unsubsidized marketplace buyers than CBO projects (${millions(cbo.baseline.unsubsidized_enrollment_2027)} unsubsidized enrollees at all incomes), and H.R. 1834 would give each of them a credit. So above 400% FPL we count as enrollees only households in which someone reported marketplace or other individual coverage in the survey: ${millions(national.enrollment.current_law.people_enrolled_above_400)} people in ${year}.

Our current-law credits, ${billions(lawNow.total_ptc)} in ${year}, are below CBO's baseline of ${billions(cbo.baseline.credits_fy2027)} for fiscal year ${year}, and the survey's marketplace enrollees don't match CBO's projections, so we report the change H.R. 1834 makes rather than spending levels.

The estimates are static: the same people enroll under each policy, so they leave out people who would start or stop buying coverage as credits change. Marketplace enrollment comes from the 2024 data.`,
      showCalculatorButton: true,
    },
  ];
}

const SECTIONS = buildSections();

// The figures the Overview opens with, from the national estimates.
function buildKeyFigures() {
  const year = national.year;
  const prior = national.current_law[String(year - 1)];
  const now = national.current_law[String(year)];
  const rise = (100 * (now.mean_benchmark_premium - prior.mean_benchmark_premium)) / prior.mean_benchmark_premium;
  return [
    {
      value: `${rise.toFixed(1)}%`,
      label: `average rise in benchmark premiums from ${year - 1} to ${year}, for tax units with a credit`,
    },
    {
      value: billions(national.budget.federal_cost),
      label: `added federal spending on credits in ${year} under H.R. 1834, PolicyEngine's static estimate`,
    },
    {
      value: millions(national.recipients.people_newly_receiving),
      label: `more people with a credit in ${year} under H.R. 1834`,
    },
  ];
}

const KEY_FIGURES = buildKeyFigures();

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
    case "national":
      return <NationalImpactChart mode={chart.mode} />;
    default:
      return null;
  }
}

// The story's parts, each opening with a heading.
const PARTS = {
  premiums: `Premiums in ${examples.year} under current law`,
  enhanced: "Reviving the enhanced credits",
  national_cost: "National effects",
};

function App() {
  const [currentPage, setCurrentPage] = useState(() => getPageFromHash());
  const [embedded] = useState(() => isEmbedded());

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

  // The Overview: one column, each section's chart under its text.
  const renderMainPage = () => (
    <div className="story-layout">
    <StoryRail sections={SECTIONS} parts={PARTS} />
    <main className="story">
      <section className="key-figures" aria-label="Key figures">
        {KEY_FIGURES.map((figure) => (
          <div key={figure.label} className="key-figure">
            <p className="key-figure-value">
              <CountUp value={figure.value} />
            </p>
            <p className="key-figure-label">{figure.label}</p>
          </div>
        ))}
      </section>
      {SECTIONS.map((section) => (
        <section key={section.id} id={section.id} className="story-section">
          {PARTS[section.id] && <p className="story-part">{PARTS[section.id]}</p>}
          <h2>{section.title}</h2>
          <div className="story-prose">
            <Prose content={section.content} />
          </div>
          {section.chart && (
            <Reveal as="figure" className="story-figure">
              <Chart chart={section.chart} />
            </Reveal>
          )}
          {section.showCalculatorButton && (
            <button onClick={() => navigateToPage("calculator")} className="story-cta">
              Calculate your household
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </section>
      ))}
    </main>
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
