"use client";

import StoryRail from "./StoryRail";
import useActiveSection from "./useActiveSection";
import examples from "../data/households/examples.json";
import schedules from "../data/contribution_schedules.json";
import "./Methodology.css";

const REPOSITORY = "https://github.com/PolicyEngine/ACA-Calc";

function Link({ href, children }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}

const Script = ({ name }) => (
  <Link href={`${REPOSITORY}/blob/main/${name}`}>
    <code>{name}</code>
  </Link>
);

// The lowest and highest share of income a schedule charges where it gives a credit.
const rateRange = (key) => {
  const rates = schedules.schedules[key].filter((rate) => rate !== null && rate > 0);
  return [Math.min(...rates).toFixed(2), Math.max(...rates).toFixed(2)];
};

function buildSections() {
  const year = examples.year;
  const priorYear = examples.prior_year;
  const [min2026, max2026] = rateRange(`current_${priorYear}`);
  const [minNow, maxNow] = rateRange(`current_${year}`);
  const enhancedCap = Math.max(...schedules.schedules.enhanced.filter((rate) => rate !== null));

  return [
    {
      id: "method_data",
      title: "Model and data",
      body: (
        <>
          <p>
            Our figures come from{" "}
            <Link href="https://github.com/PolicyEngine/policyengine-us">PolicyEngine US</Link>{" "}
            {examples.model_version}, an open-source model of federal and state taxes and benefits.
          </p>
          <p>
            The example households and the calculator run the model for one household at a time,
            with the benchmark premium (the second-lowest-cost silver plan) in the household's county, which
            the model takes from{" "}
            <Link href="https://www.kff.org/interactive/subsidy-calculator/">KFF's premium data</Link> for{" "}
            {priorYear} and {year}.
          </p>
          <p>
            The scripts that produce the figures are in the app's{" "}
            <Link href={REPOSITORY}>repository</Link>: <Script name="precompute_households.py" /> for the four
            example households, <Script name="precompute_cliff_household.py" /> for the Pennsylvania example across incomes, and{" "}
            <Script name="precompute_contribution_schedules.py" /> for the contribution schedules.
          </p>
        </>
      ),
    },
    {
      id: "method_policies",
      title: "Policies compared",
      body: (
        <>
          <ul>
            <li>
              <strong>{priorYear} current law.</strong> Tax units between 100% and 400% of the federal poverty
              line can get a credit, and pay {min2026}% to {max2026}% of their income for the benchmark plan.
            </li>
            <li>
              <strong>{year} current law.</strong> The same rules, with the IRS's {year} contribution
              percentages, {minNow}% to {maxNow}% of income.
            </li>
            <li>
              <strong>H.R. 1834.</strong> Revives the enhanced credits for 2026 through 2028: tax units pay
              nothing for the benchmark plan up to 150% FPL, the share rises to {enhancedCap}% of income at 400%
              FPL, and it stays at {enhancedCap}% above that, with no income limit. The House passed the bill on January 8, 2026; it has not
              been enacted.
            </li>
          </ul>
          <p>
            The credit measures income against the previous year's poverty guideline: {priorYear}'s for{" "}
            {year} coverage. Alaska and Hawaii have their own guidelines.
          </p>
        </>
      ),
    },
    {
      id: "method_limits",
      title: "Limitations",
      body: (
        <p>
          The example households assume every member buys the benchmark plan; a household that picks another
          plan pays a different amount, though its credit is the same up to that plan's premium.
        </p>
      ),
    },
  ];
}

const SECTIONS = buildSections();

function Methodology({ onCalculator }) {
  const active = useActiveSection(SECTIONS);
  return (
    <div className="story-layout">
      <StoryRail sections={SECTIONS} parts={{}} active={active} />
      <main className="story">
        {SECTIONS.map((section) => (
          <section key={section.id} id={section.id} className="story-section">
            <h2>{section.title}</h2>
            <div className="story-prose">{section.body}</div>
          </section>
        ))}
        <div className="story-ctas">
          <button type="button" onClick={onCalculator} className="story-cta">
            Calculate your household
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </main>
    </div>
  );
}

export default Methodology;
