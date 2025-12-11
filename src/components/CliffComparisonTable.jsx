import "./CliffComparisonTable.css";

function CliffComparisonTable({ data, showReforms = false, showSlcsp = false, showBaseline2026 = true }) {
  const { at_650_fpl, household_info } = data;

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

  // Calculate net premiums
  const netPremium2025 = Math.max(0, at_650_fpl.slcsp_2025 - at_650_fpl.ptc_2025_ira);
  const netPremium2026Baseline = at_650_fpl.slcsp_2026; // No PTC in baseline
  const netPremium2026IRA = Math.max(0, at_650_fpl.slcsp_2026 - at_650_fpl.ptc_2026_ira);
  const netPremium2026_700 = Math.max(0, at_650_fpl.slcsp_2026 - at_650_fpl.ptc_2026_700fpl);

  // Calculate breakdown of premium change
  const slcspIncrease = at_650_fpl.slcsp_2026 - at_650_fpl.slcsp_2025;
  const subsidyLoss = at_650_fpl.ptc_2025_ira; // Lost subsidy (was getting this, now getting 0)
  const totalIncrease = netPremium2026Baseline - netPremium2025;

  return (
    <div className="cliff-table">
      <div className="table-header">
        <h3>Single Adult, Age {household_info?.age || 45}</h3>
        <p>{household_info?.location || "Lebanon County, PA"} · Income: {formatCurrency(at_650_fpl.income_2026)} ({household_info?.fpl_percent || 650}% FPL)</p>
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
          <tr className="row-2025">
            <td>2025</td>
            <td>IRA in effect</td>
            {showSlcsp && <td>{formatCurrencyMonthly(at_650_fpl.slcsp_2025)}</td>}
            <td className="ptc-cell positive">{formatCurrencyMonthly(at_650_fpl.ptc_2025_ira)}</td>
            <td>{formatCurrencyMonthly(netPremium2025)}</td>
          </tr>
          {showBaseline2026 && (
            <tr className="row-baseline">
              <td>2026</td>
              <td>Baseline (IRA expires)</td>
              {showSlcsp && <td>{formatCurrencyMonthly(at_650_fpl.slcsp_2026)}</td>}
              <td className="ptc-cell zero">$0/mo</td>
              <td className="premium-increase">{formatCurrencyMonthly(netPremium2026Baseline)}</td>
            </tr>
          )}
          {showReforms && (
            <>
              <tr className="row-ira">
                <td>2026</td>
                <td>IRA Extended</td>
                {showSlcsp && <td>{formatCurrencyMonthly(at_650_fpl.slcsp_2026)}</td>}
                <td className="ptc-cell positive">{formatCurrencyMonthly(at_650_fpl.ptc_2026_ira)}</td>
                <td>{formatCurrencyMonthly(netPremium2026IRA)}</td>
              </tr>
              <tr className="row-700fpl">
                <td>2026</td>
                <td>700% FPL Proposal</td>
                {showSlcsp && <td>{formatCurrencyMonthly(at_650_fpl.slcsp_2026)}</td>}
                <td className="ptc-cell positive">{formatCurrencyMonthly(at_650_fpl.ptc_2026_700fpl)}</td>
                <td>{formatCurrencyMonthly(netPremium2026_700)}</td>
              </tr>
            </>
          )}
        </tbody>
      </table>

      {!showReforms && (
        <div className="cliff-breakdown">
          <div className="breakdown-title">Net premium change breakdown (2025 → 2026 baseline)</div>
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
