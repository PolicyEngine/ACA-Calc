import "./CliffComparisonTable.css";

// Rows the Overview can show: a year under the law in effect, or a proposal
// for the chart year. Values come from precompute_cliff_household.py.
const ROW_CLASSES = { "2025": "row-2025", hr1834: "row-ira", bill700: "row-700fpl" };

function CliffComparisonTable({ data, rows = ["2025"], showSlcsp = false, showBreakdown = false }) {
  const { household_info, years, proposals, year, example_income } = data;

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatCurrencyMonthly = (value) => {
    return formatCurrency(value / 12) + "/mo";
  };

  const netPremium = (row) => Math.max(0, row.slcsp - row.ptc);
  const describe = (key) => {
    if (years[key]) return { label: key, scenario: years[key].law, values: years[key] };
    return { label: String(year), scenario: proposals[key].name, values: proposals[key] };
  };

  // The change in net premium from 2025, under the enhanced credits, to the
  // chart year under current law: the lost credit plus the premium increase.
  const first = years["2025"];
  const last = years[String(year)];
  const subsidyLoss = first.ptc - last.ptc;
  const slcspIncrease = last.slcsp - first.slcsp;
  const totalIncrease = netPremium(last) - netPremium(first);

  return (
    <div className="cliff-table">
      <div className="table-header">
        <h3>Single Adult, Age {household_info?.age}</h3>
        <p>
          {household_info?.location} · Income: {formatCurrency(example_income)} ({last.fpl_percent}% FPL in {year})
        </p>
      </div>
      <table>
        <thead>
          <tr>
            <th>Year</th>
            <th>Scenario</th>
            {showSlcsp && <th>Benchmark (SLCSP)</th>}
            <th>Tax Credit</th>
            <th>Net Premium</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((key) => {
            const { label, scenario, values } = describe(key);
            const noCredit = values.ptc <= 0;
            return (
              <tr key={key} className={ROW_CLASSES[key] || "row-baseline"}>
                <td>{label}</td>
                <td>{scenario}</td>
                {showSlcsp && <td>{formatCurrencyMonthly(values.slcsp)}</td>}
                <td className={`ptc-cell ${noCredit ? "zero" : "positive"}`}>{formatCurrencyMonthly(values.ptc)}</td>
                <td className={noCredit && key !== "2025" ? "premium-increase" : undefined}>
                  {formatCurrencyMonthly(netPremium(values))}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {showBreakdown && (
        <div className="cliff-breakdown">
          <div className="breakdown-title">Net premium change breakdown (2025 → {year} current law)</div>
          <div className="breakdown-items">
            <div className="breakdown-item">
              <span className="breakdown-label">Subsidy expiration</span>
              <span className="breakdown-value">+{formatCurrencyMonthly(subsidyLoss)}</span>
            </div>
            <div className="breakdown-item">
              <span className="breakdown-label">Premium increase (SLCSP)</span>
              <span className="breakdown-value">+{formatCurrencyMonthly(slcspIncrease)}</span>
            </div>
            <div className="breakdown-item total">
              <span className="breakdown-label">Total net premium change</span>
              <span className="breakdown-value">+{formatCurrencyMonthly(totalIncrease)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CliffComparisonTable;
