import { useMemo } from "react";
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
import "./PremiumChart.css";

// The three scenarios the calculator and the Overview compare, in
// PolicyEngine's chart colors (src/index.css). Current law a year earlier is
// dashed, so the two current-law lines read as one law in two years.
export const SCENARIO_STYLES = {
  prior: { color: "var(--pe-prior)", dash: "6 4" },
  current: { color: "var(--pe-current)", dash: undefined },
  revived: { color: "var(--pe-reform)", dash: undefined },
};

// Axis and grid styling shared by the app's charts.
export const AXIS = {
  stroke: "var(--border)",
  tick: { fill: "var(--muted-foreground)", fontSize: 12, fontFamily: "var(--font-sans)" },
};
export const AXIS_LABEL = { fill: "var(--muted-foreground)", fontSize: 12, fontFamily: "var(--font-sans)" };
export const GRID = { stroke: "var(--border)", strokeDasharray: "3 3" };

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

// What the benchmark plan costs after the credit, never below zero.
const net = (benchmark, credit) => Math.max(0, (benchmark || 0) - (credit || 0));

/**
 * Monthly amounts by income for 2026 and 2027 current law and 2027 under H.R.
 * 1834: what the household pays for the benchmark plan after the credit
 * (measure "net") or the credit itself (measure "credit").
 *
 * `data` has the calculator API's fields: income, ptc_prior_year, ptc_baseline,
 * ptc_ira, slcsp_by_income_prior_year, slcsp_by_income, fpl and year. `lines`
 * picks the scenarios to draw. The chart is `height` pixels tall and as wide
 * as its container.
 */
function PremiumChart({
  data,
  measure = "net",
  title,
  lines: shown = ["prior", "current", "revived"],
  height = 380,
}) {
  const year = data?.year || 2027;
  const hasPrior = Boolean(data?.ptc_prior_year?.length);
  const fpl = data?.fpl || 0;

  const points = useMemo(() => {
    if (!data?.income) return [];
    // Show incomes up to a little past where H.R. 1834's credit ends.
    let maxIncome = fpl * 8;
    for (let i = data.ptc_ira.length - 1; i >= 0; i--) {
      if (data.ptc_ira[i] > 0) {
        maxIncome = Math.ceil(data.income[i] / 20000) * 20000 + 20000;
        break;
      }
    }
    return data.income
      .map((income, i) => {
        const point = { income };
        if (measure === "net") {
          point.current = net(data.slcsp_by_income?.[i], data.ptc_baseline[i]) / 12;
          point.revived = net(data.slcsp_by_income?.[i], data.ptc_ira[i]) / 12;
          if (hasPrior) {
            point.prior = net(data.slcsp_by_income_prior_year?.[i], data.ptc_prior_year[i]) / 12;
          }
        } else {
          point.current = data.ptc_baseline[i] / 12;
          point.revived = data.ptc_ira[i] / 12;
          if (hasPrior) point.prior = data.ptc_prior_year[i] / 12;
        }
        return point;
      })
      .filter((point) => point.income <= maxIncome);
  }, [data, measure, hasPrior, fpl]);

  const lines = [
    hasPrior && { key: "prior", name: `${year - 1}, current law` },
    { key: "current", name: `${year}, current law` },
    { key: "revived", name: `${year}, H.R. 1834` },
  ].filter((line) => line && shown.includes(line.key));

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const income = payload[0]?.payload?.income || 0;
    return (
      <div className="premium-chart-tooltip">
        <p className="premium-chart-tooltip-income">
          {formatCurrency(income)}
          {fpl > 0 && ` (${Math.round((100 * income) / fpl)}% FPL)`}
        </p>
        {payload.map((entry) => (
          <p key={entry.dataKey}>
            <span className="premium-chart-swatch" style={{ background: entry.color }} />
            {entry.name}: {formatCurrency(entry.value)}/month
          </p>
        ))}
      </div>
    );
  };

  const maxIncome = points.length ? points[points.length - 1].income : 0;
  const step = maxIncome > 160000 ? 40000 : 20000;
  const xTicks = [];
  for (let tick = 0; tick <= maxIncome; tick += step) xTicks.push(tick);

  return (
    <div className="premium-chart">
      {title && <h3 className="premium-chart-title">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid {...GRID} vertical={false} />
          <XAxis
            dataKey="income"
            type="number"
            domain={[0, maxIncome]}
            ticks={xTicks}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            {...AXIS}
            height={44}
            label={{ value: "Household income", position: "insideBottom", offset: 0, ...AXIS_LABEL }}
          />
          <YAxis tickFormatter={(v) => formatCurrency(v)} {...AXIS} width={64} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="top"
            align="left"
            height={36}
            iconType="plainline"
            wrapperStyle={{ fontSize: "13px", fontFamily: "var(--font-sans)" }}
          />
          {fpl > 0 && (
            <ReferenceLine
              x={fpl * 4}
              stroke="var(--color-gray-400)"
              strokeDasharray="4 4"
              label={{ value: "400% FPL", position: "insideTopRight", ...AXIS_LABEL, fontSize: 11 }}
            />
          )}
          {lines.map(({ key, name }) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={name}
              stroke={SCENARIO_STYLES[key].color}
              strokeDasharray={SCENARIO_STYLES[key].dash}
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default PremiumChart;
