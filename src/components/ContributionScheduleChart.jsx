import { useState } from "react";
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

// Where current law's credit ends; the line labels keep off it and its name.
const LIMIT_400 = { x: 400, label: "400% FPL", position: "insideTopRight" };

// `fill`: the plot takes the height its parent leaves (the Overview's pinned
// card) instead of 340px.
function ContributionScheduleChart({ showPolicies = ["current2027", "enhanced"], fill = false }) {
  const showsCurrentLaw = showPolicies.some((policy) => CURRENT_LAW.includes(policy));
  // Name each line beside it, or fall back to a legend when they run too
  // close together (DirectLabels.jsx).
  const plan = labelPlan(data, showPolicies, { yDomain: [0, 12], plotHeight: 340 - 60 });
  const [labelsFit, setLabelsFit] = useState(true);
  const showLegend = plan.crowded || !labelsFit;

  return (
    <div className={fill ? "contribution-chart chart-fill" : "contribution-chart"}>
      <h3 className="chart-title">Share of income paid for the benchmark plan</h3>
      <p className="chart-subtitle">
        The most a household pays for the benchmark plan, as a percent of its income
      </p>

      <div className={fill ? "chart-plot fill" : "chart-plot"}>
      <ResponsiveContainer width="100%" height={fill ? "100%" : 340}>
        <LineChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
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
          {showLegend && (
            <Legend
              verticalAlign="top"
              align="left"
              iconType="plainline"
              wrapperStyle={{ fontSize: "13px", fontFamily: "var(--font-sans)", paddingBottom: "8px" }}
            />
          )}
          {showsCurrentLaw && (
            <ReferenceLine
              x={LIMIT_400.x}
              stroke="var(--color-gray-400)"
              strokeDasharray="4 4"
              label={{ value: LIMIT_400.label, position: LIMIT_400.position, ...AXIS_LABEL, fontSize: 11 }}
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
            <Customized
              component={(props) => (
                <DirectLabels
                  {...props}
                  index={plan.index}
                  references={showsCurrentLaw ? [LIMIT_400] : []}
                  onFit={setLabelsFit}
                  hidden={!labelsFit}
                />
              )}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      </div>

      {showsCurrentLaw && (
        <p className="chart-note">No credit is available below 100% FPL, where the lines start, and current law gives none above 400% FPL, where its lines end.</p>
      )}
    </div>
  );
}

export default ContributionScheduleChart;
