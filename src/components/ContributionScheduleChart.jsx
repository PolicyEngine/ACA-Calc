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
  Customized,
} from "recharts";
import { ACTIVE_DOT, AXIS, AXIS_LABEL, CURSOR, GRID } from "./PremiumChart";
import { DirectLabels, labelPlan } from "./DirectLabels";
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
};

const data = schedules.fpl_percent.map((fpl, i) => {
  const point = { fpl };
  for (const [policy, key] of Object.entries(SERIES)) {
    point[policy] = schedules.schedules[key][i];
  }
  return point;
});

// The same scenario colors as the premium charts (src/index.css).
const STYLES = {
  current2026: { color: "var(--pe-prior)", dash: "6 4" },
  current2027: { color: "var(--pe-current)", dash: undefined },
  enhanced: { color: "var(--pe-reform)", dash: undefined },
};

const LABELS = {
  current2026: "2026, current law",
  current2027: "2027, current law",
  enhanced: "Enhanced credits (H.R. 1834)",
};

const CURRENT_LAW = ["current2026", "current2027"];

function ContributionScheduleChart({ showPolicies = ["current2027", "enhanced"] }) {
  const showsCurrentLaw = showPolicies.some((policy) => CURRENT_LAW.includes(policy));
  // Name each line beside it, or fall back to a legend when they run too
  // close together (DirectLabels.jsx).
  const plan = labelPlan(data, showPolicies, { yDomain: [0, 12], plotHeight: 340 - 52 });

  return (
    <div className="contribution-chart">
      <h3 className="chart-title">Share of income paid for the benchmark plan</h3>
      <p className="chart-subtitle">
        The most a household pays for the benchmark plan, as a percent of its income
      </p>

      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid {...GRID} vertical={false} />
          <XAxis
            dataKey="fpl"
            type="number"
            domain={[0, 800]}
            ticks={[0, 100, 200, 300, 400, 500, 600, 700, 800]}
            tickFormatter={(value) => `${value}%`}
            {...AXIS}
            height={44}
            label={{ value: "Income, percent of the poverty guideline", position: "insideBottom", offset: 0, ...AXIS_LABEL }}
          />
          <YAxis domain={[0, 12]} tickFormatter={(value) => `${value}%`} {...AXIS} width={44} />
          <Tooltip
            formatter={(value, name) =>
              value === null ? ["No credit", name] : [`${value.toFixed(2)}%`, name]
            }
            cursor={CURSOR}
            labelFormatter={(fpl) => `Income at ${fpl}% of the poverty guideline`}
            contentStyle={{
              backgroundColor: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-container)",
              fontSize: "13px",
              fontFamily: "var(--font-sans)",
            }}
          />
          {plan.crowded && (
            <Legend
              verticalAlign="top"
              align="left"
              height={36}
              iconType="plainline"
              wrapperStyle={{ fontSize: "13px", fontFamily: "var(--font-sans)" }}
            />
          )}
          {showsCurrentLaw && (
            <ReferenceLine
              x={400}
              stroke="var(--color-gray-400)"
              strokeDasharray="4 4"
              label={{ value: "400% FPL", position: "insideTopRight", ...AXIS_LABEL, fontSize: 11 }}
            />
          )}
          {showPolicies.map((policy) => (
            <Line
              key={policy}
              type="linear"
              dataKey={policy}
              name={LABELS[policy]}
              stroke={STYLES[policy].color}
              strokeDasharray={STYLES[policy].dash}
              strokeWidth={2.5}
              dot={false}
              activeDot={ACTIVE_DOT}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
          {!plan.crowded && (
            <Customized component={(props) => <DirectLabels {...props} index={plan.index} />} />
          )}
        </LineChart>
      </ResponsiveContainer>

      {showsCurrentLaw && (
        <p className="chart-note">Current law gives no credit above 400% FPL, where its lines end.</p>
      )}
    </div>
  );
}

export default ContributionScheduleChart;
