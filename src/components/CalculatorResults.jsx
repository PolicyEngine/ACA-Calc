import { useState, useMemo } from "react";
import HealthBenefitsChart from "./HealthBenefitsChart";
import "./Calculator.css";

function CalculatorResults({ data }) {
  const [activeTab, setActiveTab] = useState("gain");
  const [userIncome, setUserIncome] = useState("");
  const [visibleLines, setVisibleLines] = useState({
    baseline: true,
    ira: true,
    fpl700: true,
    additionalBracket: true,
    simplifiedBracket: true,
  });

  const toggleLine = (line) => {
    setVisibleLines(prev => ({ ...prev, [line]: !prev[line] }));
  };

  // Format data for HealthBenefitsChart
  const chartData = useMemo(() => {
    if (!data) return null;
    return {
      income: data.income,
      ptc_baseline: data.ptc_baseline,
      ptc_ira: data.ptc_ira,
      ptc_700fpl: data.ptc_700fpl,
      ptc_additional_bracket: data.ptc_additional_bracket,
      ptc_simplified_bracket: data.ptc_simplified_bracket,
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
    if (!data) return null;

    // Find closest index for medicaid/chip lookup
    const findClosestIndex = (targetIncome, incomeArray) => {
      if (!incomeArray || targetIncome <= 0) return 0;
      let closest = 0;
      let minDiff = Infinity;
      for (let i = 0; i < incomeArray.length; i++) {
        const diff = Math.abs(incomeArray[i] - targetIncome);
        if (diff < minDiff) {
          minDiff = diff;
          closest = i;
        }
      }
      return closest;
    };

    const closestIdx = findClosestIndex(income, data.income);
    const onMedicaid = data.medicaid?.[closestIdx] > 0;
    const onChip = data.chip?.[closestIdx] > 0;

    // At 0 income, check actual medicaid status
    if (income <= 0) {
      return {
        income: 0,
        baseline: 0,
        ira: 0,
        fpl700: 0,
        additionalBracket: 0,
        simplifiedBracket: 0,
        iraGain: 0,
        fpl700Gain: 0,
        additionalBracketGain: 0,
        simplifiedBracketGain: 0,
        fplPct: 0,
        onMedicaid: data.medicaid?.[0] > 0,
        onChip: data.chip?.[0] > 0,
      };
    }

    const baseline = interpolatePTC(income, data.income, data.ptc_baseline);
    const ira = interpolatePTC(income, data.income, data.ptc_ira);
    const fpl700 = interpolatePTC(income, data.income, data.ptc_700fpl);
    const additionalBracket = interpolatePTC(income, data.income, data.ptc_additional_bracket);
    const simplifiedBracket = interpolatePTC(income, data.income, data.ptc_simplified_bracket);
    const fplPct = (income / data.fpl) * 100;

    return {
      income,
      baseline,
      ira,
      fpl700,
      additionalBracket,
      simplifiedBracket,
      iraGain: ira - baseline,
      fpl700Gain: fpl700 - baseline,
      additionalBracketGain: additionalBracket - baseline,
      simplifiedBracketGain: simplifiedBracket - baseline,
      fplPct,
      onMedicaid,
      onChip,
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
    { id: "gain", label: "Gain from Reform" },
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
        {/* GAIN FROM REFORM TAB - shows gains over baseline, lines only, no shading */}
        {activeTab === "gain" && chartData && (
          <>
            <div className="chart-toggles">
              <span className="toggle-label">Show gain from:</span>
              <label className={`toggle-item ${visibleLines.ira ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.ira}
                  onChange={() => toggleLine('ira')}
                />
                <span className="toggle-color ira"></span>
                IRA Extension
              </label>
              <label className={`toggle-item ${visibleLines.fpl700 ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.fpl700}
                  onChange={() => toggleLine('fpl700')}
                />
                <span className="toggle-color fpl700"></span>
                700% FPL Bill
              </label>
              <label className={`toggle-item ${visibleLines.additionalBracket ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.additionalBracket}
                  onChange={() => toggleLine('additionalBracket')}
                />
                <span className="toggle-color additional"></span>
                Additional Bracket
              </label>
              <label className={`toggle-item ${visibleLines.simplifiedBracket ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.simplifiedBracket}
                  onChange={() => toggleLine('simplifiedBracket')}
                />
                <span className="toggle-color simplified"></span>
                Simplified Bracket
              </label>
            </div>
            <div className="results-chart">
              <HealthBenefitsChart
                data={chartData}
                chartState="gain_view"
                householdInfo={{}}
                visibleLines={visibleLines}
              />
            </div>
          </>
        )}

        {/* COMPARISON TAB - all reforms with shading */}
        {activeTab === "comparison" && chartData && (
          <>
            <div className="chart-toggles">
              <span className="toggle-label">Show:</span>
              <label className={`toggle-item ${visibleLines.baseline ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.baseline}
                  onChange={() => toggleLine('baseline')}
                />
                <span className="toggle-color baseline"></span>
                Baseline
              </label>
              <label className={`toggle-item ${visibleLines.ira ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.ira}
                  onChange={() => toggleLine('ira')}
                />
                <span className="toggle-color ira"></span>
                IRA Extension
              </label>
              <label className={`toggle-item ${visibleLines.fpl700 ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.fpl700}
                  onChange={() => toggleLine('fpl700')}
                />
                <span className="toggle-color fpl700"></span>
                700% FPL Bill
              </label>
              <label className={`toggle-item ${visibleLines.additionalBracket ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.additionalBracket}
                  onChange={() => toggleLine('additionalBracket')}
                />
                <span className="toggle-color additional"></span>
                Additional Bracket
              </label>
              <label className={`toggle-item ${visibleLines.simplifiedBracket ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={visibleLines.simplifiedBracket}
                  onChange={() => toggleLine('simplifiedBracket')}
                />
                <span className="toggle-color simplified"></span>
                Simplified Bracket
              </label>
            </div>
            <div className="results-chart">
              <HealthBenefitsChart
                data={chartData}
                chartState="both_reforms"
                householdInfo={{}}
                visibleLines={visibleLines}
              />
            </div>
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

                  {userResults.additionalBracket > 0 && (
                    <div className="impact-card additional-bracket">
                      <h4>Additional Bracket</h4>
                      <p className="impact-value">{formatCurrency(userResults.additionalBracket)}</p>
                      <p className="impact-label">Annual PTC</p>
                      <p className="impact-monthly">{formatCurrency(userResults.additionalBracket / 12)}/month</p>
                      {userResults.additionalBracketGain > 0 && (
                        <p className="impact-gain">+{formatCurrency(userResults.additionalBracketGain)}/year</p>
                      )}
                    </div>
                  )}

                  {userResults.simplifiedBracket > 0 && (
                    <div className="impact-card simplified-bracket">
                      <h4>Simplified Bracket</h4>
                      <p className="impact-value">{formatCurrency(userResults.simplifiedBracket)}</p>
                      <p className="impact-label">Annual PTC</p>
                      <p className="impact-monthly">{formatCurrency(userResults.simplifiedBracket / 12)}/month</p>
                      {userResults.simplifiedBracketGain > 0 && (
                        <p className="impact-gain">+{formatCurrency(userResults.simplifiedBracketGain)}/year</p>
                      )}
                    </div>
                  )}
                </div>

                <div className="impact-explanation">
                  <h4>What this means</h4>
                  {(() => {
                    const hasBaseline = userResults.baseline > 0;
                    const hasIra = userResults.ira > 0;
                    const hasFpl700 = userResults.fpl700 > 0;
                    const fpl = userResults.fplPct.toFixed(0);

                    // Check if on Medicaid or CHIP based on actual calculations
                    if (userResults.onMedicaid || userResults.onChip) {
                      const programs = [];
                      if (userResults.onMedicaid) programs.push("Medicaid");
                      if (userResults.onChip) programs.push("CHIP");
                      const programList = programs.join(" and ");
                      return (
                        <p>
                          At {fpl}% FPL, your household would be covered by <strong>{programList}</strong>.
                          Premium tax credits are not available when eligible for these programs.
                        </p>
                      );
                    }

                    // Below 100% FPL with no Medicaid - coverage gap
                    if (userResults.fplPct < 100 && !hasBaseline && !hasIra && !hasFpl700) {
                      return (
                        <p>
                          At {fpl}% FPL, you fall into the <strong>coverage gap</strong>.
                          Your state has not expanded Medicaid, so adults at this income level don't qualify.
                          Marketplace subsidies are only available starting at 100% FPL,
                          leaving a gap in coverage for those below 100% FPL in non-expansion states.
                        </p>
                      );
                    }

                    // Above 700% FPL - only IRA could help
                    if (userResults.fplPct > 700) {
                      return (
                        <p>
                          At {fpl}% FPL, you are <strong>above the 700% FPL threshold</strong>.
                          {hasIra
                            ? " The IRA Extension would provide subsidies, but the 700% FPL Bill only extends eligibility to 700% FPL."
                            : " Your required contribution under the IRA Extension (8.5% of income) exceeds the benchmark premium cost, so you would not receive subsidies under either reform option."}
                        </p>
                      );
                    }

                    // Above 400% FPL but under 700%
                    if (userResults.fplPct > 400) {
                      if (hasIra && hasFpl700) {
                        return (
                          <p>
                            At {fpl}% FPL, you are <strong>above the 400% FPL cliff</strong> but within range of both reform options.
                            Under baseline 2026 law, you would receive no premium tax credits.
                            Both reform options would provide you with subsidies.
                          </p>
                        );
                      } else if (hasIra && !hasFpl700) {
                        return (
                          <p>
                            At {fpl}% FPL, you are <strong>above the 400% FPL cliff</strong>.
                            The IRA Extension would provide subsidies. The 700% FPL Bill would not provide subsidies because
                            your required contribution (9.25% of income) would exceed the benchmark premium cost.
                          </p>
                        );
                      } else {
                        return (
                          <p>
                            At {fpl}% FPL, you are <strong>above the 400% FPL cliff</strong>.
                            Your income is high enough that your required contribution would exceed the benchmark premium cost,
                            so neither reform option would provide subsidies at this income level.
                          </p>
                        );
                      }
                    }

                    // Between 138% and 400% FPL
                    if (hasBaseline) {
                      return (
                        <p>
                          At {fpl}% FPL, you are <strong>in the marketplace subsidy range</strong>.
                          You would receive subsidies under baseline law, but the reform options
                          would increase your credits by lowering your required contribution percentage.
                        </p>
                      );
                    } else {
                      return (
                        <p>
                          At {fpl}% FPL, you are <strong>in the marketplace subsidy range</strong>.
                          Your required contribution under baseline law would exceed the benchmark premium cost,
                          so you would not receive subsidies. The reform options lower required contributions and may provide credits.
                        </p>
                      );
                    }
                  })()}
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
