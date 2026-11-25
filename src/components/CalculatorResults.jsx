import { useState, useEffect } from "react";
import PremiumChart from "./PremiumChart";
import { MAX_EARNINGS, useHouseholdAtIncome } from "./householdAtIncome";
import { EXPANSION_STATES } from "./medicaidExpansion";
import "./Calculator.css";

const TABS = [
  { id: "net", label: "What you'd pay" },
  { id: "credit", label: "Premium tax credits" },
  { id: "impact", label: "Your household" },
];

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

// A monthly change in what the household pays, such as "+$12/month".
const formatChange = (monthly) => {
  const rounded = Math.round(monthly);
  if (rounded === 0) return "No change";
  return `${rounded > 0 ? "+" : "−"}${formatCurrency(Math.abs(rounded))}/month`;
};

const joinList = (items) =>
  items.length <= 1 ? items[0] ?? "" : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

const indicesWhere = (items, test) =>
  items.flatMap((item, i) => (test(item, i) ? [i] : []));

// Names some of the household's members for a sentence: "you", "you and your
// spouse", "your children", "you and your child aged 20".
function describeMembers(indices, people) {
  const picked = new Set(indices);
  const label = (i) => {
    const { relationship, age } = people[i];
    if (relationship === "head") return "you";
    if (relationship === "spouse") return "your spouse";
    return `your ${age < 19 ? "child" : "dependent"} aged ${age}`;
  };
  const adults = indicesWhere(people, (person, i) => person.relationship !== "dependent" && picked.has(i));
  const dependents = indicesWhere(people, (person) => person.relationship === "dependent");
  const pickedDependents = dependents.filter((i) => picked.has(i));

  if (adults.length === 2 && pickedDependents.length === 0) return "you and your spouse";
  const parts = adults.map(label);
  if (pickedDependents.length > 0 && pickedDependents.length === dependents.length) {
    const children = pickedDependents.every((i) => people[i].age < 19);
    if (dependents.length === 1) parts.push(children ? "your child" : "your dependent");
    else parts.push(children ? "your children" : "your dependents");
  } else {
    parts.push(...pickedDependents.map(label));
  }
  return joinList(parts);
}

const isCovered = (member) => member.medicaid || member.chip;

// Each state's Basic Health Program, as policyengine-us 2.138.2 models it
// (gov.hhs.basic_health_program): adults aged 19 to 64 with incomes above
// Medicaid's limit up to 200% FPL. New York's limit was 250% until its section
// 1332 waiver ended on June 30, 2026; the model's eligibility is annual, so it
// keeps 250% for all of 2026. People the program covers can't enroll in a
// Marketplace plan (42 U.S.C. 18051(e)), but the API doesn't report this
// coverage yet, so the results name the program instead.
const BASIC_HEALTH_PROGRAMS = {
  DC: {
    state: "DC",
    name: "the Healthy DC Plan",
    limit: "200% FPL",
    url: "https://hbx.dc.gov/sites/default/files/dc/sites/hbx/page_content/attachments/Healthy%20DC%20Plan%20Overview%20-%20October%202025.pdf",
  },
  MN: {
    state: "Minnesota",
    name: "MinnesotaCare",
    limit: "200% FPL",
    url: "https://mn.gov/dhs/health-care/minnesotacare/",
  },
  NY: {
    state: "New York",
    name: "the Essential Plan",
    limit: "200% FPL (250% FPL until June 30, 2026)",
    url: "https://info.nystateofhealth.ny.gov/EssentialPlan",
  },
  OR: {
    state: "Oregon",
    name: "OHP Bridge",
    limit: "200% FPL",
    url: "https://www.oregon.gov/oha/ohp/pages/bridge.aspx",
  },
};

function BasicHealthProgramNote({ state }) {
  const program = BASIC_HEALTH_PROGRAMS[state];
  if (!program) return null;
  return (
    <p className="results-notice">
      {program.state}'s Basic Health Program, {program.name}, covers adults aged 19 to 64 with
      incomes above Medicaid's limit and up to {program.limit}. People it covers can't enroll in a
      Marketplace plan or get a premium tax credit. These results don't include {program.name} yet:
      at those incomes, the "Your household" cards show what a Marketplace plan would cost, and the
      charts show $0.{" "}
      <a href={program.url} target="_blank" rel="noopener noreferrer">
        Learn about {program.name}
      </a>
      .
    </p>
  );
}

// "Medicaid would cover your children, and CHIP would cover ...", naming each
// program only for the members it covers.
function coverageSentence(coverage, people) {
  const medicaid = indicesWhere(coverage, (member) => member.medicaid);
  const chip = indicesWhere(coverage, (member) => !member.medicaid && member.chip);
  return [
    medicaid.length > 0 && `Medicaid would cover ${describeMembers(medicaid, people)}`,
    chip.length > 0 && `CHIP would cover ${describeMembers(chip, people)}`,
  ]
    .filter(Boolean)
    .join(", and ");
}

// What a scenario's card shows, in annual amounts.
function cardValues(scenario) {
  if (scenario.coverage.every(isCovered)) {
    const programs = [
      scenario.coverage.some((member) => member.medicaid) && "Medicaid",
      scenario.coverage.some((member) => !member.medicaid && member.chip) && "CHIP",
    ].filter(Boolean);
    return { covered: true, programs: programs.join(" and ") };
  }
  // In the coverage gap the model prices no plan, since it assumes no one there
  // buys one; the card shows what one would cost without a credit.
  const gap = scenario.benchmark === 0;
  const benchmark = gap ? scenario.full_premium : scenario.benchmark;
  const credit = gap ? 0 : scenario.credit;
  return { covered: false, gap, benchmark, credit, net: Math.max(0, benchmark - credit) };
}

// What the household pays each month, as its card shows it.
const monthlyNet = (values) => Math.round(values.net / 12);

// The credit's income as a share of the poverty line, in whole percents
// rounded down, as Form 8962 line 5 has it; just over 400% FPL rounds down to
// 400, which still qualifies, so it's worded.
function fplText(scenario) {
  const percent = (100 * scenario.magi) / scenario.fpl;
  if (percent > 400 && percent < 401) return "just over 400";
  return String(Math.floor(percent));
}

function Explanation({ answer, state, year, compareEnhanced }) {
  const { people, current, ira, prior_year: priorYear } = answer;
  const fpl = fplText(current);
  const percent = (100 * current.magi) / current.fpl;
  const monthly = (annual) => `${formatCurrency(annual / 12)}/month`;
  // The credit as the cards show it: the rounded premium less the rounded payment.
  const monthlyCredit = (values) =>
    `${formatCurrency(Math.round(values.benchmark / 12) - Math.round(values.net / 12))}/month`;

  const covered = indicesWhere(current.coverage, isCovered);
  const uncovered = indicesWhere(current.coverage, (member) => !isCovered(member));
  if (uncovered.length === 0) {
    // Medicaid and CHIP measure income against the coverage year's guideline,
    // not the credit's, so the share of the credit's guideline isn't named.
    return (
      <p>
        At this income in {year}, {coverageSentence(current.coverage, people)}. Premium tax credits
        are not available to people eligible for these programs.
      </p>
    );
  }

  // Members Medicaid or CHIP covers leave the benchmark plan to the others.
  const lead = covered.length > 0 && (
    <>
      {capitalize(coverageSentence(current.coverage, people))}, so the benchmark plan covers{" "}
      {describeMembers(uncovered, people)}.{" "}
    </>
  );
  const who = describeMembers(uncovered, people);
  const values = cardValues(current);
  const revived = ira ? cardValues(ira) : null;
  const prior = priorYear && !priorYear.coverage.every(isCovered) ? cardValues(priorYear) : null;

  if (percent < 100 && current.credit <= 0 && (ira?.credit ?? 0) <= 0) {
    const barred = uncovered.some((i) => current.coverage[i].medicaid_work_requirement);
    let reason;
    if (barred) {
      // The model applies Medicaid's work requirement from 2027, counting
      // earnings of 80 hours a month at the federal minimum wage ($7.25).
      reason = (
        <>
          {who} wouldn't qualify for Medicaid: from 2027, Medicaid requires most adults in the
          expansion group, aged 19 to 64, to work or do other qualifying activities for 80 hours a
          month, which the model counts as earnings of at least $580 a month. The {year} estimate
          assumes no qualifying activity beyond these earnings and no exemption. Premium tax credits
          start at 100% FPL.
        </>
      );
    } else if (!EXPANSION_STATES.includes(state)) {
      reason = (
        <>
          {who} fall into the <strong>coverage gap</strong>. Your state has not expanded
          Medicaid, so adults at this income don't qualify, and premium tax credits start at 100% FPL.
        </>
      );
    } else {
      reason = (
        <>
          {who} wouldn't qualify for Medicaid, and premium tax credits start at 100% FPL.
        </>
      );
    }
    return (
      <p>
        {lead}In {year}, at {fpl}% FPL, {reason}
      </p>
    );
  }

  if (current.credit <= 0 && percent > 400) {
    return (
      <p>
        {lead}At {fpl}% FPL, your household is <strong>above current law's 400% FPL limit</strong>, so
        it receives no credit and pays the whole benchmark premium: {monthly(values.net)} in {year}
        {prior && <>, against {monthly(prior.net)} in {year - 1}</>}.{" "}
        {compareEnhanced &&
          revived &&
          (revived.credit > 0
            ? `H.R. 1834 would limit what it pays for the benchmark plan to 8.5% of income, a credit of ${monthlyCredit(revived)}.`
            : "Under H.R. 1834 it would receive no credit either: the benchmark plan costs less than 8.5% of its income.")}
      </p>
    );
  }

  if (current.credit > 0) {
    return (
      <p>
        {lead}At {fpl}% FPL, current law limits what your household pays for the benchmark plan to a
        share of its income, and the credit pays the rest, so the credit grows when premiums do.
        Your household would pay {monthly(values.net)} in {year}
        {prior && <>, against {monthly(prior.net)} in {year - 1}</>}.
        {compareEnhanced && revived && <> H.R. 1834 would lower its share of income, to {monthly(revived.net)}.</>}
      </p>
    );
  }

  // Above 100% FPL, where a state with a Basic Health Program has no plan
  // priced for the members left, the model has the program covering them.
  const program = BASIC_HEALTH_PROGRAMS[state];
  if (program && values.gap) {
    return (
      <p>
        {lead}In {year}, at {fpl}% FPL, {program.name} would cover {who}, so the model gives no
        credit.{compareEnhanced && revived?.gap && " H.R. 1834 wouldn't change this."}
      </p>
    );
  }

  return (
    <p>
      {lead}In {year}, at {fpl}% FPL, the benchmark plan costs less than the share of income current
      law asks your household to pay, so it receives no credit.{" "}
      {compareEnhanced &&
        revived &&
        (revived.credit > 0
          ? `H.R. 1834 would lower that share, giving a credit of ${monthlyCredit(revived)}.`
          : "H.R. 1834 wouldn't give it a credit either.")}
    </p>
  );
}

function CalculatorResults({
  data,
  formData,
  compareEnhanced = false,
  initialTab = "net",
  initialIncome = null,
  storedAtIncome = null,
  onViewChange,
}) {
  // The tab and income a link opened on, or an example household's income,
  // so its cards match the Overview.
  const [activeTab, setActiveTab] = useState(initialTab);
  const [userIncome, setUserIncome] = useState(initialIncome ? String(initialIncome) : "");

  // Tell the calculator what's on screen, for the page's link.
  useEffect(() => {
    const income = parseFloat(userIncome);
    onViewChange?.({ tab: activeTab, income: income > 0 ? income : null });
  }, [activeTab, userIncome, onViewChange]);

  // An answer from before the API took a year is for 2026.
  const year = data?.year || 2026;
  // A server that predates the year setting answers for 2026 whatever is asked.
  const requestedYear = formData?.year;
  const yearMismatch = Boolean(requestedYear) && requestedYear !== year;

  // The household at the earnings entered, calculated by the API.
  const income = parseFloat(userIncome) || 0;
  const tooHigh = income > MAX_EARNINGS;
  const atIncome = useHouseholdAtIncome(formData, income, storedAtIncome);
  const answer = atIncome.status === "ready" && atIncome.answer?.income === income ? atIncome.answer : null;

  const cards = answer
    ? (() => {
        const prior = answer.prior_year && cardValues(answer.prior_year);
        const current = cardValues(answer.current);
        const revived = answer.ira && cardValues(answer.ira);
        // A change only between two cards with amounts.
        const change = (values, from, label) =>
          from && !from.covered && !values.covered
            ? { monthly: monthlyNet(values) - monthlyNet(from), from: label }
            : null;
        return [
          prior && { key: "prior", title: `${year - 1}, current law`, values: prior },
          {
            key: "baseline",
            title: `${year}, current law`,
            values: current,
            change: change(current, prior, `from ${year - 1}`),
          },
          compareEnhanced &&
            revived && {
              key: "ira",
              title: `${year}, H.R. 1834`,
              values: revived,
              change: change(revived, current, "from current law"),
            },
        ].filter(Boolean);
      })()
    : [];

  const otherIncome = answer ? answer.current.magi - answer.income : 0;
  const everyone = answer ? describeMembers(answer.people.map((_, i) => i), answer.people) : "";

  return (
    <div className="calculator-results">
      {yearMismatch && (
        <p className="results-notice">
          These results are for {year}: the calculator's server doesn't support {requestedYear} yet.
        </p>
      )}
      <div className="results-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`results-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="results-content">
        <BasicHealthProgramNote state={formData?.state} />
        {(activeTab === "net" || activeTab === "credit") && data && (
          <>
            <div className="results-chart">
              <PremiumChart
                data={data}
                measure={activeTab}
                lines={compareEnhanced ? ["prior", "current", "revived"] : ["prior", "current"]}
                height={400}
                xLabel="Earnings"
                title={
                  activeTab === "net"
                    ? "What your household would pay for the benchmark plan"
                    : "Your household's premium tax credit"
                }
              />
            </div>
            <p className="results-caption">
              The benchmark plan is the second-lowest-cost silver plan in your area.
              {compareEnhanced &&
                " H.R. 1834 would revive the enhanced credits of 2021–2025 for 2026 through 2028; it passed the House on January 8, 2026 and has not been enacted."}
            </p>
          </>
        )}

        {activeTab === "impact" && (
          <div className="results-impact">
            <div className="impact-input-section">
              <label htmlFor="user-income">Enter your household's annual earnings:</label>
              <div className="income-input-wrapper">
                <span className="currency-prefix">$</span>
                <input
                  type="number"
                  id="user-income"
                  value={userIncome}
                  onChange={(e) => setUserIncome(e.target.value)}
                  placeholder="75,000"
                  min="0"
                  max={MAX_EARNINGS}
                  step="1000"
                />
              </div>
            </div>

            {tooHigh && (
              <p className="results-notice">The calculator covers earnings up to $1,000,000.</p>
            )}

            {atIncome.status === "error" && <p className="results-notice">{atIncome.error}</p>}

            {answer && (
              <div className="impact-results">
                <div className="impact-summary">
                  <p className="fpl-indicator">
                    {formatCurrency(answer.income)} of earnings
                    {otherIncome >= 1 && <>, with {formatCurrency(otherIncome)} of other income the credit counts,</>}{" "}
                    is approximately <strong>{fplText(answer.current)}% FPL</strong> for your household
                  </p>
                </div>

                <div className="impact-cards">
                  {cards.map((card) => (
                    <div key={card.key} className={`impact-card ${card.key}`}>
                      <h4>{card.title}</h4>
                      {card.values.covered ? (
                        <>
                          <p className="impact-value impact-value-text">{card.values.programs}</p>
                          <p className="impact-label">Covers {everyone}</p>
                        </>
                      ) : (
                        <>
                          <p className="impact-value">{formatCurrency(card.values.net / 12)}</p>
                          <p className="impact-label">
                            {card.values.gap ? "Full premium, per month" : "Benchmark plan after credit, per month"}
                          </p>
                          <dl className="impact-breakdown">
                            <div>
                              <dt>Benchmark plan</dt>
                              <dd>{formatCurrency(card.values.benchmark / 12)}</dd>
                            </div>
                            <div>
                              <dt>Premium tax credit</dt>
                              {/* The rounded premium less the rounded payment, so the card adds up. */}
                              <dd>
                                {formatCurrency(
                                  Math.round(card.values.benchmark / 12) - Math.round(card.values.net / 12)
                                )}
                              </dd>
                            </div>
                          </dl>
                          {card.values.gap && (
                            <p className="impact-note">A plan bought without a credit costs its full premium.</p>
                          )}
                        </>
                      )}
                      {card.change && (
                        <p className="impact-change">
                          {formatChange(card.change.monthly)} {card.change.from}
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                <div className="impact-explanation">
                  <h4>What this means</h4>
                  <Explanation
                    answer={answer}
                    state={formData?.state}
                    year={year}
                    compareEnhanced={compareEnhanced}
                  />
                </div>
              </div>
            )}

            {!answer && !tooHigh && atIncome.status !== "error" && (
              <div className="impact-placeholder" role={atIncome.status === "loading" ? "status" : undefined}>
                {atIncome.status === "loading" && <span className="loading-spinner small" aria-hidden="true" />}
                <p>
                  {atIncome.status === "loading"
                    ? `Calculating your household at ${formatCurrency(income)} of earnings…`
                    : "Enter your earnings above to see what your household would pay for the benchmark plan in each scenario."}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default CalculatorResults;
