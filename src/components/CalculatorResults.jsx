import { useState, useMemo, useEffect } from "react";
import HealthBenefitsChart from "./HealthBenefitsChart";
import "./Calculator.css";

function CalculatorResults({ data, formData }) {
  const [activeTab, setActiveTab] = useState("gain");
  const [userIncome, setUserIncome] = useState("");

  // Determine which reforms were actually calculated
  const selectedReforms = useMemo(() => ({
    ira: formData?.show_ira ?? true,
    fpl700: formData?.show_700fpl ?? false,
    additionalBracket: formData?.show_additional_bracket ?? false,
    simplifiedBracket: formData?.show_simplified_bracket ?? false,
    cap700: formData?.show_700fpl_cap ?? false,
    minPremium: formData?.show_min_premium ?? false,
  }), [formData]);

  // An answer from before the API took a year is for 2026.
  const year = data?.year || 2026;
  // A server that predates the year setting answers for 2026 whatever is asked.
  const requestedYear = formData?.year;
  const yearMismatch = Boolean(requestedYear) && requestedYear !== year;

  const [visibleLines, setVisibleLines] = useState({
    baseline: true,
    ira: true,
    fpl700: false,
    additionalBracket: false,
    simplifiedBracket: false,
    cap700: false,
    minPremium: false,
  });

  // Sync visibleLines with selectedReforms when formData changes
  useEffect(() => {
    setVisibleLines({
      baseline: true,
      ira: selectedReforms.ira,
      fpl700: selectedReforms.fpl700,
      additionalBracket: selectedReforms.additionalBracket,
      simplifiedBracket: selectedReforms.simplifiedBracket,
      cap700: selectedReforms.cap700,
      minPremium: selectedReforms.minPremium,
    });
  }, [selectedReforms]);

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
      ptc_700fpl_cap: data.ptc_700fpl_cap,
      ptc_min_premium: data.ptc_min_premium,
      medicaid: data.medicaid,
      chip: data.chip,
      fpl: data.fpl,
      year: data.year,
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
        cap700: 0,
        minPremium: 0,
        iraGain: 0,
        fpl700Gain: 0,
        additionalBracketGain: 0,
        simplifiedBracketGain: 0,
        cap700Gain: 0,
        minPremiumGain: 0,
        benchmark: 0,
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
    const cap700 = interpolatePTC(income, data.income, data.ptc_700fpl_cap);
    const minPremium = interpolatePTC(income, data.income, data.ptc_min_premium);
    // The annual benchmark premium for the members eligible for the credit at
    // this income; an answer from before the API reported it by income has
    // only the maximum.
    const benchmark = data.slcsp_by_income?.length
      ? interpolatePTC(income, data.income, data.slcsp_by_income)
      : data.slcsp;
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
      cap700,
      minPremium,
      cap700Gain: cap700 - baseline,
      minPremiumGain: minPremium - baseline,
      benchmark,
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

  // What the benchmark plan costs after a credit, per month.
  const netPremium = (credit) => Math.max(0, (userResults?.benchmark || 0) - credit) / 12;

  const tabs = [
    { id: "gain", label: "Gain over Current Law" },
    { id: "comparison", label: "Current Law vs Proposals" },
    { id: "impact", label: "Your Impact" },
  ];

  return (
    <div className="calculator-results">
      {yearMismatch && (
        <p className="results-notice">
          These results are for {year}: the calculator's server doesn't support {requestedYear} yet.
        </p>
      )}
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
              {selectedReforms.ira && (
                <label className={`toggle-item ${visibleLines.ira ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.ira}
                    onChange={() => toggleLine('ira')}
                  />
                  <span className="toggle-color ira"></span>
                  H.R. 1834
                </label>
              )}
              {selectedReforms.cap700 && (
                <label className={`toggle-item ${visibleLines.cap700 ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.cap700}
                    onChange={() => toggleLine('cap700')}
                  />
                  <span className="toggle-color cap700"></span>
                  700% FPL cap (draft)
                </label>
              )}
              {selectedReforms.minPremium && (
                <label className={`toggle-item ${visibleLines.minPremium ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.minPremium}
                    onChange={() => toggleLine('minPremium')}
                  />
                  <span className="toggle-color min-premium"></span>
                  $5 minimum premium (draft)
                </label>
              )}
              {selectedReforms.fpl700 && (
                <label className={`toggle-item ${visibleLines.fpl700 ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.fpl700}
                    onChange={() => toggleLine('fpl700')}
                  />
                  <span className="toggle-color fpl700"></span>
                  700% FPL Bill
                </label>
              )}
              {selectedReforms.additionalBracket && (
                <label className={`toggle-item ${visibleLines.additionalBracket ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.additionalBracket}
                    onChange={() => toggleLine('additionalBracket')}
                  />
                  <span className="toggle-color additional"></span>
                  Additional Bracket
                </label>
              )}
              {selectedReforms.simplifiedBracket && (
                <label className={`toggle-item ${visibleLines.simplifiedBracket ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.simplifiedBracket}
                    onChange={() => toggleLine('simplifiedBracket')}
                  />
                  <span className="toggle-color simplified"></span>
                  Simplified Bracket
                </label>
              )}
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
                Current law
              </label>
              {selectedReforms.ira && (
                <label className={`toggle-item ${visibleLines.ira ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.ira}
                    onChange={() => toggleLine('ira')}
                  />
                  <span className="toggle-color ira"></span>
                  H.R. 1834
                </label>
              )}
              {selectedReforms.cap700 && (
                <label className={`toggle-item ${visibleLines.cap700 ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.cap700}
                    onChange={() => toggleLine('cap700')}
                  />
                  <span className="toggle-color cap700"></span>
                  700% FPL cap (draft)
                </label>
              )}
              {selectedReforms.minPremium && (
                <label className={`toggle-item ${visibleLines.minPremium ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.minPremium}
                    onChange={() => toggleLine('minPremium')}
                  />
                  <span className="toggle-color min-premium"></span>
                  $5 minimum premium (draft)
                </label>
              )}
              {selectedReforms.fpl700 && (
                <label className={`toggle-item ${visibleLines.fpl700 ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.fpl700}
                    onChange={() => toggleLine('fpl700')}
                  />
                  <span className="toggle-color fpl700"></span>
                  700% FPL Bill
                </label>
              )}
              {selectedReforms.additionalBracket && (
                <label className={`toggle-item ${visibleLines.additionalBracket ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.additionalBracket}
                    onChange={() => toggleLine('additionalBracket')}
                  />
                  <span className="toggle-color additional"></span>
                  Additional Bracket
                </label>
              )}
              {selectedReforms.simplifiedBracket && (
                <label className={`toggle-item ${visibleLines.simplifiedBracket ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={visibleLines.simplifiedBracket}
                    onChange={() => toggleLine('simplifiedBracket')}
                  />
                  <span className="toggle-color simplified"></span>
                  Simplified Bracket
                </label>
              )}
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

            {userResults && (() => {
              // Only members who'd buy a marketplace plan count toward the benchmark,
              // so it is zero where everyone has Medicaid or CHIP.
              const showNetPremium = userResults.benchmark > 0;
              return (
              <div className="impact-results">
                <div className="impact-summary">
                  <p className="fpl-indicator">
                    {formatCurrency(userResults.income)} is approximately <strong>{userResults.fplPct.toFixed(0)}% FPL</strong> for your household
                  </p>
                </div>

                <div className="impact-cards">
                  <div className="impact-card baseline">
                    <h4>Current law ({year})</h4>
                    <p className="impact-value">{formatCurrency(userResults.baseline)}</p>
                    <p className="impact-label">Annual PTC</p>
                    <p className="impact-monthly">{formatCurrency(userResults.baseline / 12)}/month</p>
                    {showNetPremium && (
                      <p className="impact-net">Benchmark plan after credit: {formatCurrency(netPremium(userResults.baseline))}/month</p>
                    )}
                  </div>

                  {selectedReforms.ira && (
                    <div className="impact-card ira">
                      <h4>H.R. 1834</h4>
                      <p className="impact-value">{formatCurrency(userResults.ira)}</p>
                      <p className="impact-label">Annual PTC</p>
                      <p className="impact-monthly">{formatCurrency(userResults.ira / 12)}/month</p>
                      {userResults.iraGain > 0 && (
                        <p className="impact-gain">+{formatCurrency(userResults.iraGain)}/year</p>
                      )}
                      {showNetPremium && (
                        <p className="impact-net">Benchmark plan after credit: {formatCurrency(netPremium(userResults.ira))}/month</p>
                      )}
                    </div>
                  )}

                  {selectedReforms.cap700 && (
                    <div className="impact-card cap700" title="The enhanced credits with eligibility ending at 700% FPL, as in a January 2026 draft of the CARE Act, which was not introduced">
                      <h4>700% FPL cap (draft)</h4>
                      <p className="impact-value">{formatCurrency(userResults.cap700)}</p>
                      <p className="impact-label">Annual PTC</p>
                      <p className="impact-monthly">{formatCurrency(userResults.cap700 / 12)}/month</p>
                      {userResults.cap700Gain > 0 && (
                        <p className="impact-gain">+{formatCurrency(userResults.cap700Gain)}/year</p>
                      )}
                      {showNetPremium && (
                        <p className="impact-net">Benchmark plan after credit: {formatCurrency(netPremium(userResults.cap700))}/month</p>
                      )}
                    </div>
                  )}

                  {selectedReforms.minPremium && (
                    <div className="impact-card min-premium" title="The enhanced credits, except that the credit can't cover the last $5 a month, as in a January 2026 draft of the CARE Act, which was not introduced">
                      <h4>$5 minimum premium (draft)</h4>
                      <p className="impact-value">{formatCurrency(userResults.minPremium)}</p>
                      <p className="impact-label">Annual PTC</p>
                      <p className="impact-monthly">{formatCurrency(userResults.minPremium / 12)}/month</p>
                      {userResults.minPremiumGain > 0 && (
                        <p className="impact-gain">+{formatCurrency(userResults.minPremiumGain)}/year</p>
                      )}
                      {showNetPremium && (
                        <p className="impact-net">Benchmark plan after credit: {formatCurrency(netPremium(userResults.minPremium))}/month</p>
                      )}
                    </div>
                  )}

                  {selectedReforms.fpl700 && (
                    <div className="impact-card fpl700">
                      <h4>700% FPL Bill</h4>
                      <p className="impact-value">{formatCurrency(userResults.fpl700)}</p>
                      <p className="impact-label">Annual PTC</p>
                      <p className="impact-monthly">{formatCurrency(userResults.fpl700 / 12)}/month</p>
                      {userResults.fpl700Gain > 0 && (
                        <p className="impact-gain">+{formatCurrency(userResults.fpl700Gain)}/year</p>
                      )}
                      {showNetPremium && (
                        <p className="impact-net">Benchmark plan after credit: {formatCurrency(netPremium(userResults.fpl700))}/month</p>
                      )}
                    </div>
                  )}

                  {selectedReforms.additionalBracket && (
                    <div className="impact-card additional-bracket" title="CRFB 'Progressive Alternative': extends enhanced subsidies below 300% FPL with linear phase-up above">
                      <h4>
                        <a href="https://www.crfb.org/blogs/understanding-aca-subsidy-discussion" target="_blank" rel="noopener noreferrer" className="reform-link">
                          Additional Bracket
                        </a>
                      </h4>
                      <p className="impact-value">{formatCurrency(userResults.additionalBracket)}</p>
                      <p className="impact-label">Annual PTC</p>
                      <p className="impact-monthly">{formatCurrency(userResults.additionalBracket / 12)}/month</p>
                      {userResults.additionalBracketGain > 0 && (
                        <p className="impact-gain">+{formatCurrency(userResults.additionalBracketGain)}/year</p>
                      )}
                      {showNetPremium && (
                        <p className="impact-net">Benchmark plan after credit: {formatCurrency(netPremium(userResults.additionalBracket))}/month</p>
                      )}
                    </div>
                  )}

                  {selectedReforms.simplifiedBracket && (
                    <div className="impact-card simplified-bracket" title="CRFB 'Smaller Alternative': subsidies set halfway between baseline and enhanced rates">
                      <h4>
                        <a href="https://www.crfb.org/blogs/understanding-aca-subsidy-discussion" target="_blank" rel="noopener noreferrer" className="reform-link">
                          Simplified Bracket
                        </a>
                      </h4>
                      <p className="impact-value">{formatCurrency(userResults.simplifiedBracket)}</p>
                      <p className="impact-label">Annual PTC</p>
                      <p className="impact-monthly">{formatCurrency(userResults.simplifiedBracket / 12)}/month</p>
                      {userResults.simplifiedBracketGain > 0 && (
                        <p className="impact-gain">+{formatCurrency(userResults.simplifiedBracketGain)}/year</p>
                      )}
                      {showNetPremium && (
                        <p className="impact-net">Benchmark plan after credit: {formatCurrency(netPremium(userResults.simplifiedBracket))}/month</p>
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
                            ? " H.R. 1834 would provide subsidies, but the 700% FPL Bill only extends eligibility to 700% FPL."
                            : " Your required contribution under H.R. 1834 (8.5% of income) exceeds the benchmark premium cost, so you would not receive subsidies under either reform option."}
                        </p>
                      );
                    }

                    // Above 400% FPL but under 700%
                    if (userResults.fplPct > 400) {
                      if (hasIra && hasFpl700) {
                        return (
                          <p>
                            At {fpl}% FPL, you are <strong>above the 400% FPL cliff</strong> but within range of both reform options.
                            Under {year} current law, you would receive no premium tax credits.
                            Both reform options would provide you with subsidies.
                          </p>
                        );
                      } else if (hasIra && !hasFpl700) {
                        return (
                          <p>
                            At {fpl}% FPL, you are <strong>above the 400% FPL cliff</strong>.
                            H.R. 1834 would provide subsidies. The 700% FPL Bill would not provide subsidies because
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
                          You would receive subsidies under current law, and the reform options
                          would increase your credits by lowering your required contribution percentage.
                        </p>
                      );
                    } else {
                      return (
                        <p>
                          At {fpl}% FPL, you are <strong>in the marketplace subsidy range</strong>.
                          Your required contribution under current law would exceed the benchmark premium cost,
                          so you would not receive subsidies. The reform options lower required contributions and may provide credits.
                        </p>
                      );
                    }
                  })()}
                </div>
              </div>
              );
            })()}

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
