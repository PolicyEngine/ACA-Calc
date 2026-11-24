import { useMemo, useState } from "react";
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
import { DirectLabels, labelPlan } from "./DirectLabels";
import { fplPercentText } from "./fpl";
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
// The crosshair: a dashed line at the hovered income, and a dot on each line.
export const CURSOR = { stroke: "var(--color-gray-400)", strokeDasharray: "3 3" };
export const ACTIVE_DOT = { r: 4, stroke: "var(--card)", strokeWidth: 2 };

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

// What the benchmark plan costs after the credit, never below zero.
const net = (benchmark, credit) => Math.max(0, (benchmark || 0) - (credit || 0));

// A month's payment, or none where the model prices no plan: Medicaid, CHIP or
// a Basic Health Program covers everyone, or, in the coverage gap, the model
// assumes no one buys one. The line breaks there instead of showing $0.
const monthlyPayment = (benchmark, credit) => (benchmark > 0 ? net(benchmark, credit) / 12 : null);

// A month's credit as the calculator's cards show it: the rounded premium less
// the rounded payment, so the chart and the cards agree to the dollar.
const monthlyCredit = (benchmark, credit) =>
  benchmark > 0 ? Math.round(benchmark / 12) - Math.round(net(benchmark, credit) / 12) : (credit || 0) / 12;

// The earnings at which the credit's income (magi) reaches an amount. The
// credit's income adds other income to the earnings, such as Alaska's Permanent
// Fund Dividend; without it, the earnings are the credit's income.
function earningsAt(amount, incomes, magi) {
  if (!magi?.length) return amount;
  const i = magi.findIndex((value) => value >= amount);
  if (i <= 0) return i === 0 ? incomes[0] : amount;
  const share = (amount - magi[i - 1]) / (magi[i] - magi[i - 1]);
  return incomes[i - 1] + share * (incomes[i] - incomes[i - 1]);
}

/**
 * Monthly amounts by income for 2026 and 2027 current law and 2027 under H.R.
 * 1834: what the household pays for the benchmark plan after the credit
 * (measure "net") or the credit itself (measure "credit").
 *
 * `data` has the calculator API's fields: income, ptc_prior_year, ptc_baseline,
 * ptc_ira, slcsp_by_income_prior_year, slcsp_by_income, fpl, year and, if the
 * API sent it, magi. `lines` picks the scenarios to draw, and `xLabel` names
 * the income axis. The chart is `height` pixels tall, or with `fill` as tall
 * as its parent leaves (the Overview's pinned card), and as wide as its
 * container.
 */
function PremiumChart({
  data,
  measure = "net",
  title,
  lines: shown = ["prior", "current", "revived"],
  height = 380,
  fill = false,
  xLabel = "Household income",
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
        const point = { income, magi: data.magi?.[i] ?? income };
        const value = measure === "net" ? monthlyPayment : monthlyCredit;
        point.current = value(data.slcsp_by_income?.[i], data.ptc_baseline[i]);
        point.revived = value(data.slcsp_by_income?.[i], data.ptc_ira[i]);
        if (hasPrior) point.prior = value(data.slcsp_by_income_prior_year?.[i], data.ptc_prior_year[i]);
        return point;
      })
      .filter((point) => point.income <= maxIncome);
  }, [data, measure, hasPrior, fpl]);

  const lines = [
    hasPrior && { key: "prior", name: `${year - 1}, current law` },
    { key: "current", name: `${year}, current law` },
    { key: "revived", name: `${year}, H.R. 1834` },
  ].filter((line) => line && shown.includes(line.key));

  // Name each line beside it, or fall back to a legend when they run too
  // close together (DirectLabels.jsx).
  const keys = lines.map((line) => line.key);
  const yMax = Math.max(0, ...points.flatMap((point) => keys.map((key) => point[key] ?? 0)));
  const plan = labelPlan(points, keys, { yDomain: [0, yMax * 1.1], plotHeight: height - 52 });
  const [labelsFit, setLabelsFit] = useState(true);
  const showLegend = plan.crowded || !labelsFit;

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const income = payload[0]?.payload?.income || 0;
    const magi = payload[0]?.payload?.magi ?? income;
    return (
      <div className="premium-chart-tooltip">
        <p className="premium-chart-tooltip-income">
          {formatCurrency(income)}
          {fpl > 0 && ` (${fplPercentText(magi, fpl)}% FPL)`}
        </p>
        {payload.filter((entry) => entry.value != null).map((entry) => (
          <p key={entry.dataKey}>
            <span className="premium-chart-swatch" style={{ background: entry.color }} />
            {entry.name}: {formatCurrency(entry.value)}/month
          </p>
        ))}
      </div>
    );
  };

  const maxIncome = points.length ? points[points.length - 1].income : 0;
  // 400% FPL on the earnings axis.
  const limit400 = fpl > 0 ? earningsAt(4 * fpl, data.income, data.magi) : 0;
  // The same line as the labels see it: they keep off it and its name.
  const limit = fpl > 0 ? { x: limit400, label: "400% FPL", position: "insideTopRight" } : null;
  const step = maxIncome > 160000 ? 40000 : 20000;
  const xTicks = [];
  for (let tick = 0; tick <= maxIncome; tick += step) xTicks.push(tick);

  return (
    <div className={fill ? "premium-chart chart-fill" : "premium-chart"}>
      {title && <h3 className="premium-chart-title">{title}</h3>}
      <div className={fill ? "chart-plot fill" : "chart-plot"}>
      <ResponsiveContainer width="100%" height={fill ? "100%" : height}>
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
            label={{ value: xLabel, position: "insideBottom", offset: 0, ...AXIS_LABEL }}
          />
          <YAxis tickFormatter={(v) => formatCurrency(v)} {...AXIS} width={64} />
          <Tooltip content={<CustomTooltip />} cursor={CURSOR} />
          {showLegend && (
            <Legend
              verticalAlign="top"
              align="left"
              iconType="plainline"
              wrapperStyle={{ fontSize: "13px", fontFamily: "var(--font-sans)", paddingBottom: "8px" }}
            />
          )}
          {limit && (
            <ReferenceLine
              x={limit.x}
              stroke="var(--color-gray-400)"
              strokeDasharray="4 4"
              label={{ value: limit.label, position: limit.position, ...AXIS_LABEL, fontSize: 11 }}
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
              activeDot={ACTIVE_DOT}
              isAnimationActive={false}
            />
          ))}
          {!plan.crowded && (
            <Customized
              component={(props) => (
                <DirectLabels
                  {...props}
                  index={plan.index}
                  references={limit ? [limit] : []}
                  onFit={setLabelsFit}
                  hidden={!labelsFit}
                />
              )}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}

export default PremiumChart;
