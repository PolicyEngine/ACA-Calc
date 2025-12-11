import { useState, useMemo } from "react";
import HealthBenefitsChart from "./HealthBenefitsChart";
import "./Calculator.css";

function CalculatorResults({ data }) {
  const [activeTab, setActiveTab] = useState("gain");
  const [userIncome, setUserIncome] = useState("");

  // Format data for HealthBenefitsChart
  const chartData = useMemo(() => {
    if (!data) return null;
    return {
      income: data.income,
      ptc_baseline: data.ptc_baseline,
      ptc_ira: data.ptc_ira,
      ptc_700fpl: data.ptc_700fpl,
      medicaid: data.medicaid,
      chip: data.chip,
      fpl: data.fpl,
    };
  }, [data]);

  // Interpolate PTC value at user's income
  const interpolatePTC = (income, incomeArray, ptcArray) => {
    if (!incomeArray || !ptcArray || income <= 0) return 0;

    // Find surrounding points
    let i = 0;
    while (i < incomeArray.length - 1 && incomeArray[i + 1] < income) {
      i++;
    }

    if (i >= incomeArray.length - 1) {
      return ptcArray[ptcArray.length - 1];
    }

    // Linear interpolation
    const x0 = incomeArray[i];
    const x1 = incomeArray[i + 1];
    const y0 = ptcArray[i];
    const y1 = ptcArray[i + 1];

    if (x1 === x0) return y0;
    return y0 + (y1 - y0) * (income - x0) / (x1 - x0);
  };

  // Calculate values at user's income
  const userResults = useMemo(() => {
    const income = parseFloat(userIncome) || 0;
    if (income <= 0 || !data) return null;

    const baseline = interpolatePTC(income, data.income, data.ptc_baseline);
    const ira = interpolatePTC(income, data.income, data.ptc_ira);
    const fpl700 = interpolatePTC(income, data.income, data.ptc_700fpl);
    const fplPct = (income / data.fpl) * 100;

    return {
      income,
      baseline,
      ira,
      fpl700,
      iraGain: ira - baseline,
      fpl700Gain: fpl700 - baseline,
      fplPct,
    };
  }, [userIncome, data]);

  // Format currency
  const formatCurrency = (value) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  };

  const tabs = [
    { id: "gain", label: "Gain from Extension" },
    { id: "comparison", label: "Baseline vs Extension" },
    { id: "impact", label: "Your Impact" },
  ];

  return (
    <div className="calculator-results">
      <div className="results-tabs">
        {tabs.map(tab => (
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
        {activeTab === "gain" && chartData && (
          <div className="results-chart">
            <HealthBenefitsChart
              data={chartData}
              chartState="ira_impact"
              householdInfo={{}}
            />
          </div>
        )}

        {activeTab === "comparison" && chartData && (
          <div className="results-chart">
            <HealthBenefitsChart
              data={chartData}
              chartState="both_reforms"
              householdInfo={{}}
            />
          </div>
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
                    {formatCurrency(userResults.income)} is approximately <strong>{userResults.fplPct.toFixed(0)}% FPL</strong> for your household
                  </p>
                </div>

                <div className="impact-cards">
                  <div className="impact-card baseline">
                    <h4>Baseline (2026)</h4>
                    <p className="impact-value">{formatCurrency(userResults.baseline)}</p>
                    <p className="impact-label">Annual PTC</p>
                    <p className="impact-monthly">{formatCurrency(userResults.baseline / 12)}/month</p>
                  </div>

                  <div className="impact-card ira">
                    <h4>IRA Extension</h4>
                    <p className="impact-value">{formatCurrency(userResults.ira)}</p>
                    <p className="impact-label">Annual PTC</p>
                    <p className="impact-monthly">{formatCurrency(userResults.ira / 12)}/month</p>
                    {userResults.iraGain > 0 && (
                      <p className="impact-gain">+{formatCurrency(userResults.iraGain)}/year</p>
                    )}
                  </div>

                  <div className="impact-card fpl700">
                    <h4>700% FPL Bill</h4>
                    <p className="impact-value">{formatCurrency(userResults.fpl700)}</p>
                    <p className="impact-label">Annual PTC</p>
                    <p className="impact-monthly">{formatCurrency(userResults.fpl700 / 12)}/month</p>
                    {userResults.fpl700Gain > 0 && (
                      <p className="impact-gain">+{formatCurrency(userResults.fpl700Gain)}/year</p>
                    )}
                  </div>
                </div>

                <div className="impact-explanation">
                  <h4>What this means</h4>
                  {userResults.fplPct > 400 ? (
                    <p>
                      At {userResults.fplPct.toFixed(0)}% FPL, you are <strong>above the 400% FPL cliff</strong>.
                      Under baseline 2026 law, you would receive no premium tax credits.
                      Both reform options would provide you with subsidies.
                    </p>
                  ) : (
                    <p>
                      At {userResults.fplPct.toFixed(0)}% FPL, you are <strong>below the 400% FPL cliff</strong>.
                      You would receive some subsidies under baseline law, but the reform options
                      would increase your credits by lowering your required contribution percentage.
                    </p>
                  )}
                </div>
              </div>
            )}

            {!userResults && (
              <div className="impact-placeholder">
                <p>Enter your income above to see how each policy would affect your premium tax credits.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default CalculatorResults;
