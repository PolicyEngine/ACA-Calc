import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import "./ContributionScheduleChart.css";

// The schedules as policyengine-us computes them: the percent of income a
// household pays for the benchmark plan at each percent of the poverty
// guideline, null where the credit isn't available. Regenerate with
// precompute_contribution_schedules.py.
import schedules from "../data/contribution_schedules.json";

const SERIES = {
  current2026: "current_2026",
  current2027: "current_2027",
  enhanced: "enhanced",
  bill700: "bill700",
};

const data = schedules.fpl_percent.map((fpl, i) => {
  const point = { fpl };
  for (const [policy, key] of Object.entries(SERIES)) {
    point[policy] = schedules.schedules[key][i];
  }
  return point;
});

// Chart colors - PolicyEngine appv2 design tokens
const COLORS = {
  current2026: "#9CA3AF", // gray-400
  current2027: "#4B5563", // gray-600
  enhanced: "#0284C7",    // blue-600 from appv2
  bill700: "#7c3aed",     // purple
};

const LABELS = {
  current2026: "Current law (2026)",
  current2027: "Current law (2027)",
  enhanced: "Enhanced credits (2021–2025; H.R. 1834)",
  bill700: "700% FPL bill",
};

const CURRENT_LAW = ["current2026", "current2027"];

function ContributionScheduleChart({ showPolicies = ["current2027", "enhanced"] }) {
  const formatPercent = (value) => `${value}%`;
  const formatFPL = (value) => `${value}%`;
  const showsCurrentLaw = showPolicies.some((policy) => CURRENT_LAW.includes(policy));

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
            type="number"
            domain={[0, 800]}
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
              return [`${value.toFixed(2)}%`, LABELS[name]];
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
          {showsCurrentLaw && (
            <ReferenceLine
              x={400}
              stroke="#ef4444"
              strokeDasharray="5 5"
              strokeWidth={1}
            />
          )}

          {showPolicies.map((policy) => (
            <Line
              key={policy}
              type="linear"
              dataKey={policy}
              name={policy}
              stroke={COLORS[policy]}
              strokeWidth={2.5}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      <div className="chart-axis-labels">
        <div className="x-axis-label">Income (% of Federal Poverty Level)</div>
      </div>

      {showsCurrentLaw && (
        <div className="chart-note">
          <span className="note-marker">|</span>
          Red dashed line marks 400% FPL, where current-law credits end
        </div>
      )}
    </div>
  );
}

export default ContributionScheduleChart;
