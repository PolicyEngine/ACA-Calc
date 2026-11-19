import { useState, useMemo, useEffect } from "react";
import PremiumChart from "./PremiumChart";
import { closestIndex, scenarioAtIncome } from "./householdAtIncome";
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

// What the household pays each month, as its card shows it.
const monthlyNet = (values) => Math.round(values.net / 12);

function CalculatorResults({
  data,
  formData,
  compareEnhanced = false,
  initialTab = "net",
  initialIncome = null,
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
  const hasPrior = Boolean(data?.ptc_prior_year?.length);

  // Annual amounts at the income entered, for each scenario.
  const userResults = useMemo(() => {
    const income = parseFloat(userIncome) || 0;
    if (!data || income <= 0) return null;
    const at = (benchmark, credit, fpl, creditEndsAt400 = true) =>
      scenarioAtIncome(income, data.income, {
        benchmark,
        credit,
        lowerLimit: fpl,
        upperLimit: creditEndsAt400 ? 4 * fpl : undefined,
      });
    const index = closestIndex(income, data.income);
    const prior = hasPrior
      ? at(data.slcsp_by_income_prior_year, data.ptc_prior_year, data.fpl_prior_year)
      : null;
    const current = at(data.slcsp_by_income, data.ptc_baseline, data.fpl);
    // H.R. 1834 has no limit at 400% FPL.
    const revived = at(data.slcsp_by_income, data.ptc_ira, data.fpl, false);
    return {
      income,
      fplPct: (income / data.fpl) * 100,
      onMedicaid: data.medicaid?.[index] > 0,
      onChip: data.chip?.[index] > 0,
      prior,
      current,
      revived,
      edge: [current, revived, prior].find((scenario) => scenario?.edge)?.edge ?? null,
    };
  }, [userIncome, data, hasPrior]);

  const cards = userResults
    ? [
        userResults.prior && {
          key: "prior",
          title: `${year - 1}, current law`,
          values: userResults.prior,
        },
        {
          key: "baseline",
          title: `${year}, current law`,
          values: userResults.current,
          change: userResults.prior && {
            monthly: monthlyNet(userResults.current) - monthlyNet(userResults.prior),
            from: `from ${year - 1}`,
          },
        },
        compareEnhanced && {
          key: "ira",
          title: `${year}, H.R. 1834`,
          values: userResults.revived,
          change: {
            monthly: monthlyNet(userResults.revived) - monthlyNet(userResults.current),
            from: "from current law",
          },
        },
      ].filter(Boolean)
    : [];

  const explanation = () => {
    const { fplPct, onMedicaid, onChip, prior, current, revived } = userResults;
    // Rounding shouldn't put a household on the wrong side of a limit.
    const fpl =
      fplPct > 400 && fplPct < 400.5
        ? "just over 400"
        : fplPct < 100 && fplPct >= 99.5
          ? "just under 100"
          : fplPct.toFixed(0);
    const monthly = (annual) => `${formatCurrency(annual / 12)}/month`;
    // The credit as the cards show it: the rounded premium less the rounded payment.
    const monthlyCredit = (values) =>
      `${formatCurrency(Math.round(values.benchmark / 12) - Math.round(values.net / 12))}/month`;

    if (onMedicaid || onChip) {
      const programs = [onMedicaid && "Medicaid", onChip && "CHIP"].filter(Boolean).join(" and ");
      return (
        <p>
          At {fpl}% FPL, your household would be covered by <strong>{programs}</strong>.
          Premium tax credits are not available to people eligible for these programs.
        </p>
      );
    }

    if (fplPct < 100 && current.credit <= 0 && revived.credit <= 0) {
      return (
        <p>
          At {fpl}% FPL, you fall into the <strong>coverage gap</strong>. Your state has not
          expanded Medicaid, so adults at this income don't qualify, and premium tax credits
          start at 100% FPL.
        </p>
      );
    }

    if (current.credit <= 0 && fplPct > 400) {
      return (
        <p>
          At {fpl}% FPL, your household is <strong>above current law's 400% FPL limit</strong>, so
          it receives no credit and pays the whole benchmark premium: {monthly(current.benchmark)} in {year}
          {prior && <>, against {monthly(prior.benchmark)} in {year - 1}</>}.{" "}
          {compareEnhanced &&
            (revived.credit > 0
              ? `H.R. 1834 would limit what it pays for the benchmark plan to 8.5% of income, a credit of ${monthlyCredit(revived)}.`
              : "Under H.R. 1834 it would receive no credit either: the benchmark plan costs less than 8.5% of its income.")}
        </p>
      );
    }

    if (current.credit > 0) {
      return (
        <p>
          At {fpl}% FPL, current law limits what your household pays for the benchmark plan to a
          share of its income, and the credit pays the rest, so the credit grows when premiums do.
          Your household would pay {monthly(current.net)} in {year}
          {prior && <>, against {monthly(prior.net)} in {year - 1}</>}.
          {compareEnhanced && <> H.R. 1834 would lower its share of income, to {monthly(revived.net)}.</>}
        </p>
      );
    }

    return (
      <p>
        At {fpl}% FPL, the benchmark plan costs less than the share of income current law asks your
        household to pay, so it receives no credit.{" "}
        {compareEnhanced &&
          (revived.credit > 0
            ? `H.R. 1834 would lower that share, giving a credit of ${monthlyCredit(revived)}.`
            : "H.R. 1834 wouldn't give it a credit either.")}
      </p>
    );
  };

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
        {(activeTab === "net" || activeTab === "credit") && data && (
          <>
            <div className="results-chart">
              <PremiumChart
                data={data}
                measure={activeTab}
                lines={compareEnhanced ? ["prior", "current", "revived"] : ["prior", "current"]}
                height={400}
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
              <label htmlFor="user-income">Enter your annual household income:</label>
              <div className="income-input-wrapper">
                <span className="currency-prefix">$</span>
                <input
                  type="number"
                  id="user-income"
                  value={userIncome}
                  onChange={(e) => setUserIncome(e.target.value)}
                  placeholder="75,000"
                  min="0"
                  step="1000"
                />
              </div>
            </div>

            {userResults && (
              <div className="impact-results">
                <div className="impact-summary">
                  <p className="fpl-indicator">
                    {formatCurrency(userResults.income)} is approximately{" "}
                    <strong>{userResults.fplPct.toFixed(0)}% FPL</strong> for your household
                  </p>
                  {userResults.edge && (
                    <p className="results-notice">
                      This household's eligibility changes somewhere between{" "}
                      {formatCurrency(userResults.edge.from)} and {formatCurrency(userResults.edge.to)}.
                      Amounts affected by that change are for {formatCurrency(userResults.edge.shownAt)},
                      the closest income calculated.
                    </p>
                  )}
                </div>

                <div className="impact-cards">
                  {cards.map((card) => (
                    <div key={card.key} className={`impact-card ${card.key}`}>
                      <h4>{card.title}</h4>
                      <p className="impact-value">{formatCurrency(card.values.net / 12)}</p>
                      <p className="impact-label">Benchmark plan after credit, per month</p>
                      <dl className="impact-breakdown">
                        <div>
                          <dt>Benchmark plan</dt>
                          <dd>{formatCurrency(card.values.benchmark / 12)}</dd>
                        </div>
                        <div>
                          <dt>Premium tax credit</dt>
                          {/* The rounded premium less the rounded payment, so the card adds up. */}
                          <dd>
                            {formatCurrency(Math.round(card.values.benchmark / 12) - Math.round(card.values.net / 12))}
                          </dd>
                        </div>
                      </dl>
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
                  {explanation()}
                </div>
              </div>
            )}

            {!userResults && (
              <div className="impact-placeholder">
                <p>
                  Enter your income above to see what your household would pay for the benchmark
                  plan in each scenario.
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
