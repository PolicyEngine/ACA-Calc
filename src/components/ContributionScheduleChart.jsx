import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import "./ContributionScheduleChart.css";

// Generate data points for each policy
const generateContributionData = () => {
  const data = [];

  // FPL points from 0% to 800%
  for (let fpl = 0; fpl <= 800; fpl += 10) {
    const point = { fpl };

    // Original ACA / 2026 baseline (IRS Rev Proc 2025-25)
    // Jump at 133% is real - that's the Medicaid expansion threshold
    if (fpl < 100) {
      point.baseline = 0;
    } else if (fpl < 133) {
      // Below 133%: flat at 2.1%
      point.baseline = 2.1;
    } else if (fpl <= 150) {
      // 133-150%: 3.14% to 4.19%
      point.baseline = 3.14 + (fpl - 133) / (150 - 133) * (4.19 - 3.14);
    } else if (fpl <= 200) {
      // 150-200%: 4.19% to 6.6%
      point.baseline = 4.19 + (fpl - 150) / (200 - 150) * (6.6 - 4.19);
    } else if (fpl <= 250) {
      // 200-250%: 6.6% to 8.44%
      point.baseline = 6.6 + (fpl - 200) / (250 - 200) * (8.44 - 6.6);
    } else if (fpl <= 300) {
      // 250-300%: 8.44% to 9.96%
      point.baseline = 8.44 + (fpl - 250) / (300 - 250) * (9.96 - 8.44);
    } else if (fpl <= 400) {
      point.baseline = 9.96;
    } else {
      point.baseline = null; // No subsidy above 400%
    }

    // ARPA/IRA (2021-2025) - from IRS Revenue Procedure 2023-29
    // 0% contribution up to 150% FPL, then gradual increase
    if (fpl <= 150) {
      point.ira = 0;
    } else if (fpl <= 200) {
      // 0% to 2%
      point.ira = (fpl - 150) / (200 - 150) * 2.0;
    } else if (fpl <= 250) {
      // 2% to 4%
      point.ira = 2.0 + (fpl - 200) / (250 - 200) * (4.0 - 2.0);
    } else if (fpl <= 300) {
      // 4% to 6%
      point.ira = 4.0 + (fpl - 250) / (300 - 250) * (6.0 - 4.0);
    } else {
      // 6% to 8.5% (capped at 8.5% for all incomes above 300%)
      point.ira = 6.0 + Math.min((fpl - 300) / (400 - 300) * (8.5 - 6.0), 2.5);
    }

    // 700% FPL Proposal
    // Below 100% FPL: 0% contribution
    if (fpl < 100) {
      point.bill700 = 0;
    } else if (fpl <= 150) {
      point.bill700 = (fpl - 100) / (150 - 100) * 2.0;
    } else if (fpl <= 200) {
      point.bill700 = 2.0 + (fpl - 150) / (200 - 150) * (4.0 - 2.0);
    } else if (fpl <= 250) {
      point.bill700 = 4.0 + (fpl - 200) / (250 - 200) * (6.0 - 4.0);
    } else if (fpl <= 300) {
      point.bill700 = 6.0 + (fpl - 250) / (300 - 250) * (8.5 - 6.0);
    } else if (fpl <= 400) {
      point.bill700 = 8.5 + (fpl - 300) / (400 - 300) * (9.0 - 8.5);
    } else if (fpl <= 500) {
      point.bill700 = 9.0 + (fpl - 400) / (500 - 400) * (9.25 - 9.0);
    } else if (fpl <= 700) {
      point.bill700 = 9.25;
    } else {
      point.bill700 = null; // No subsidy above 700%
    }

    data.push(point);
  }

  return data;
};

const data = generateContributionData();

// Chart colors - PolicyEngine appv2 design tokens
const COLORS = {
  baseline: "#9CA3AF", // gray-400
  ira: "#0284C7",      // blue-600 from appv2
  bill700: "#7c3aed",  // purple
};

const LABELS = {
  baseline: "Original ACA / 2026+",
  ira: "Current Policy (2021-2025)",
  bill700: "700% FPL Proposal",
};

function ContributionScheduleChart({ showPolicies = ["baseline", "ira"] }) {
  const formatPercent = (value) => `${value}%`;
  const formatFPL = (value) => `${value}%`;

  return (
    <div className="contribution-chart">
      <div className="chart-header">
        <h3>Required Contribution by Income</h3>
        <p>Maximum percentage of income required to pay for the benchmark plan</p>
      </div>

      <div className="chart-legend">
        {showPolicies.map((policy) => (
          <div key={policy} className="legend-item">
            <span className="legend-color" style={{ backgroundColor: COLORS[policy] }}></span>
            <span className="legend-label">{LABELS[policy]}</span>
          </div>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={350}>
        <LineChart
          data={data}
          margin={{ top: 10, right: 20, left: 10, bottom: 40 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="fpl"
            tickFormatter={formatFPL}
            tick={{ fontSize: 11 }}
            ticks={[0, 100, 200, 300, 400, 500, 600, 700, 800]}
          />
          <YAxis
            tickFormatter={formatPercent}
            domain={[0, 12]}
            tick={{ fontSize: 11 }}
            width={40}
          />
          <Tooltip
            formatter={(value, name) => {
              if (value === null) return ["No subsidy", LABELS[name]];
              return [`${value.toFixed(1)}%`, LABELS[name]];
            }}
            labelFormatter={(fpl) => `Income: ${fpl}% FPL`}
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          />

          {/* Reference line for 400% FPL */}
          {showPolicies.includes("baseline") && (
            <ReferenceLine
              x={400}
              stroke="#ef4444"
              strokeDasharray="5 5"
              strokeWidth={1}
            />
          )}

          {showPolicies.includes("baseline") && (
            <Line
              type="monotone"
              dataKey="baseline"
              stroke={COLORS.baseline}
              strokeWidth={2.5}
              dot={false}
              connectNulls={false}
            />
          )}
          {showPolicies.includes("ira") && (
            <Line
              type="monotone"
              dataKey="ira"
              stroke={COLORS.ira}
              strokeWidth={2.5}
              dot={false}
            />
          )}
          {showPolicies.includes("bill700") && (
            <Line
              type="monotone"
              dataKey="bill700"
              stroke={COLORS.bill700}
              strokeWidth={2.5}
              dot={false}
              connectNulls={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      <div className="chart-axis-labels">
        <div className="x-axis-label">Income (% of Federal Poverty Level)</div>
      </div>

      {showPolicies.includes("baseline") && (
        <div className="chart-note">
          <span className="note-marker">|</span>
          Red dashed line marks 400% FPL where baseline subsidies end
        </div>
      )}
    </div>
  );
}

export default ContributionScheduleChart;
