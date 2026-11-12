import { useState, useMemo } from "react";
import PremiumChart from "./PremiumChart";
import "./Calculator.css";

const TABS = [
  { id: "net", label: "What You'd Pay" },
  { id: "credit", label: "Premium Tax Credits" },
  { id: "impact", label: "Your Household" },
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

// Linear interpolation of an array along the income axis.
const interpolate = (income, incomeArray, values) => {
  if (!incomeArray || !values || income <= 0) return 0;
  let i = 0;
  while (i < incomeArray.length - 1 && incomeArray[i + 1] < income) {
    i++;
  }
  if (i >= incomeArray.length - 1) {
    return values[values.length - 1];
  }
  const x0 = incomeArray[i];
  const x1 = incomeArray[i + 1];
  if (x1 === x0) return values[i];
  return values[i] + ((values[i + 1] - values[i]) * (income - x0)) / (x1 - x0);
};

const closestIndex = (income, incomeArray) => {
  let closest = 0;
  for (let i = 0; i < incomeArray.length; i++) {
    if (Math.abs(incomeArray[i] - income) < Math.abs(incomeArray[closest] - income)) {
      closest = i;
    }
  }
  return closest;
};

function CalculatorResults({ data, formData }) {
  const [activeTab, setActiveTab] = useState("net");
  const [userIncome, setUserIncome] = useState("");

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
    const at = (values) => interpolate(income, data.income, values);
    const scenario = (benchmark, credit) => ({
      benchmark,
      credit,
      net: Math.max(0, benchmark - credit),
    });
    const index = closestIndex(income, data.income);
    return {
      income,
      fplPct: (income / data.fpl) * 100,
      onMedicaid: data.medicaid?.[index] > 0,
      onChip: data.chip?.[index] > 0,
      prior: hasPrior ? scenario(at(data.slcsp_by_income_prior_year), at(data.ptc_prior_year)) : null,
      current: scenario(at(data.slcsp_by_income), at(data.ptc_baseline)),
      revived: scenario(at(data.slcsp_by_income), at(data.ptc_ira)),
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
            monthly: (userResults.current.net - userResults.prior.net) / 12,
            from: `from ${year - 1}`,
          },
        },
        {
          key: "ira",
          title: `${year}, H.R. 1834`,
          values: userResults.revived,
          change: {
            monthly: (userResults.revived.net - userResults.current.net) / 12,
            from: "from current law",
          },
        },
      ].filter(Boolean)
    : [];

  const explanation = () => {
    const { fplPct, onMedicaid, onChip, prior, current, revived } = userResults;
    const fpl = fplPct.toFixed(0);
    const monthly = (annual) => `${formatCurrency(annual / 12)}/month`;

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
          it gets no credit and pays the whole benchmark premium: {monthly(current.benchmark)} in {year}
          {prior && <>, against {monthly(prior.benchmark)} in {year - 1}</>}.{" "}
          {revived.credit > 0
            ? `H.R. 1834 would limit what it pays for the benchmark plan to 8.5% of income, a credit of ${monthly(revived.credit)}.`
            : "Under H.R. 1834 it would get no credit either: the benchmark plan costs less than 8.5% of its income."}
        </p>
      );
    }

    if (current.credit > 0) {
      return (
        <p>
          At {fpl}% FPL, current law limits what your household pays for the benchmark plan to a
          share of its income, and the credit pays the rest, so the credit grows when premiums do.
          Your household would pay {monthly(current.net)} in {year}
          {prior && <>, against {monthly(prior.net)} in {year - 1}</>}. H.R. 1834 would lower its
          share of income, to {monthly(revived.net)}.
        </p>
      );
    }

    return (
      <p>
        At {fpl}% FPL, the benchmark plan costs less than the share of income current law asks your
        household to pay, so it gets no credit.{" "}
        {revived.credit > 0
          ? `H.R. 1834 would lower that share, giving a credit of ${monthly(revived.credit)}.`
          : "H.R. 1834 wouldn't give it a credit either."}
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
                title={
                  activeTab === "net"
                    ? "What your household would pay for the benchmark plan"
                    : "Your household's premium tax credit"
                }
              />
            </div>
            <p className="results-caption">
              The benchmark plan is the second-lowest-cost silver plan in your area. H.R. 1834
              would revive the enhanced credits of 2021–2025 for 2026 through 2028; it passed the
              House on January 8, 2026 and has not been enacted.
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
                          <dd>{formatCurrency(card.values.credit / 12)}</dd>
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
