"use client";

import StoryRail from "./StoryRail";
import useActiveSection from "./useActiveSection";
import national from "../data/national_impacts.json";
import cbo from "../data/cbo_estimate.json";
import schedules from "../data/contribution_schedules.json";
import "./Methodology.css";

const billions = (value) => `$${(value / 1e9).toFixed(1)} billion`;
const millions = (value) => `${(value / 1e6).toFixed(1)} million`;
const share = (value, digits = 1) => `${(100 * value).toFixed(digits)}%`;

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

// PolicyEngine's figures beside CBO's, for the same year.
function CboTable() {
  const year = national.year;
  const law = national.current_law[String(year)];
  const enrollment = national.enrollment.current_law;
  const rows = [
    [
      `Added cost of H.R. 1834, ${year}`,
      `${billions(national.budget.federal_cost)} (calendar year, credits)`,
      `${billions(cbo.estimate.deficit_increase_fy2027)} (fiscal year, deficit)`,
    ],
    [`Added cost, ${cbo.estimate.window}`, "Not estimated", billions(cbo.estimate.deficit_increase_10_year)],
    [`Change in people insured, ${year}`, "None: enrollment is held fixed", `+${millions(cbo.estimate.insured_increase_2027)}`],
    [`Change in benchmark premiums, ${year}`, "None", `−${share(-cbo.estimate.benchmark_premium_change_2027)}`],
    [
      `Credits under current law, ${year}`,
      `${billions(law.total_ptc)} (calendar year)`,
      `${billions(cbo.baseline.credits_fy2027)} (fiscal year)`,
    ],
    [
      `People with a credit under current law, ${year}`,
      millions(law.people_receiving),
      millions(cbo.baseline.subsidized_enrollment_2027),
    ],
    [
      `Marketplace enrollees without a credit, ${year}`,
      millions(enrollment.people_unsubsidized),
      millions(cbo.baseline.unsubsidized_enrollment_2027),
    ],
  ];
  return (
    <figure className="story-figure method-table">
      <div className="method-table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col"></th>
              <th scope="col">PolicyEngine</th>
              <th scope="col">CBO</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, ours, theirs]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td>{ours}</td>
                <td>{theirs}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

function buildSections() {
  const year = national.year;
  const priorYear = year - 1;
  const build = national.dataset.split("@")[1];
  const enrollment = national.enrollment.current_law;
  const takeup = national.enrollment.takeup_above_400[String(year)];
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
            {national.model_version}, an open-source model of federal and state taxes and benefits.
          </p>
          <p>
            The national estimates run the model over PolicyEngine's microdata for 2024, built from the Census
            Bureau's Current Population Survey (build <code>{build}</code>) and projected to {priorYear} and{" "}
            {year}. The example households and the calculator run the same model for one household at a time,
            with the benchmark premium (the second-lowest-cost silver plan) in the household's county.
          </p>
          <p>
            The scripts that produce the figures are in the app's{" "}
            <Link href={REPOSITORY}>repository</Link>: <Script name="precompute_national.py" /> for the
            national estimates, <Script name="precompute_households.py" /> for the four example households,{" "}
            <Script name="precompute_cliff_household.py" /> for the Pennsylvania example across incomes, and{" "}
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
      id: "method_credit",
      title: "How the credit is counted",
      body: (
        <>
          <p>
            The credit figures are the credit each tax unit uses: the credit it is eligible for, capped at the
            premium of the plan it enrolls in.
          </p>
          <p>
            Household net income counts that credit as a refundable tax credit. The Supplemental Poverty
            Measure counts it through the lower premiums enrollees pay, so the change in households' poverty
            resources equals the cost of the bill.
          </p>
        </>
      ),
    },
    {
      id: "method_enrollment",
      title: "Who enrolls",
      body: (
        <>
          <p>
            Whether a household buys marketplace coverage comes from the survey. At or below 400% FPL, we use
            the survey's take-up as it is.
          </p>
          <p>
            Above 400% FPL, the survey's take-up alone would make more people unsubsidized marketplace buyers
            than CBO projects at all incomes ({millions(cbo.baseline.unsubsidized_enrollment_2027)}), and H.R.
            1834 would give each of them a credit. So above 400% FPL
            we count as enrollees only tax units in which someone reported marketplace or other individual
            coverage in the survey. That keeps {millions(takeup.tax_units_above_400_kept)} tax units and leaves
            out {millions(takeup.tax_units_switched_off)}, for {millions(enrollment.people_enrolled_above_400)}{" "}
            enrollees above 400% FPL in {year}.
          </p>
          <p>
            In all, {millions(enrollment.people_enrolled)} people buy marketplace coverage in {year} under
            current law: {millions(enrollment.people_subsidized)} with a credit and{" "}
            {millions(enrollment.people_unsubsidized)} without. The same people enroll under H.R. 1834.
          </p>
        </>
      ),
    },
    {
      id: "method_cbo",
      title: "Comparison with CBO",
      body: (
        <>
          <p>
            The Congressional Budget Office's estimate of H.R. 1834 includes how people would respond:{" "}
            {millions(cbo.estimate.insured_increase_2027)} more people insured in {year}, and benchmark premiums{" "}
            {share(-cbo.estimate.benchmark_premium_change_2027)} lower as healthier people enroll. Ours holds
            enrollment and premiums fixed, so it leaves out the cost of new enrollees. CBO's figure is the change in
            the deficit in fiscal year {year}, October {priorYear} through September {year}; ours is the change
            in credits in calendar year {year}.
          </p>
          <CboTable />
          <p>
            Our current-law credits are below CBO's baseline even though we count more people with a credit, so
            our average credit is lower than CBO's. We haven't traced that gap, so the Overview reports the
            change H.R. 1834 makes rather than spending levels.
          </p>
          <p>
            Sources: <Link href={cbo.estimate.url}>{cbo.estimate.title}</Link>;{" "}
            <Link href={cbo.baseline.url}>{cbo.baseline.title}</Link>.
          </p>
        </>
      ),
    },
    {
      id: "method_limits",
      title: "Limitations",
      body: (
        <ul>
          <li>
            The estimates are static: the same people enroll, at the same premiums, under each policy. They
            leave out people who would start or stop buying coverage, and changes in employer coverage.
          </li>
          <li>Enrollment comes from people's answers in the 2024 survey, projected forward.</li>
          <li>
            Our current-law spending is below CBO's baseline, as above, so we report changes rather than
            levels.
          </li>
          <li>
            The example households assume every member buys the benchmark plan; a household that picks another
            plan pays a different amount, though its credit is the same up to that plan's premium.
          </li>
        </ul>
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
          <section
            key={section.id}
            id={section.id}
            className={`story-section${section.id === active ? " is-active" : ""}`}
          >
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
