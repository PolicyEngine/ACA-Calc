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
import { ACTIVE_DOT, AXIS, AXIS_LABEL, CURSOR, GRID, SCENARIO_STYLES } from "./PremiumChart";
import { DirectLabels, labelPlan } from "./DirectLabels";
import "./PremiumChart.css";

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);

// The axis stops at 100%; the cliff's rate runs off the top. Incomes start
// above the Medicaid limit: net income counts the credit but not Medicaid, so
// the move from one to the other shows as a large negative rate.
const MAX_RATE = 100;
const MIN_INCOME = 40000;

/**
 * The household's marginal tax rate across incomes in 2027 under current law
 * and under H.R. 1834: the share of each extra $1,000 of earnings it loses to
 * taxes and to a smaller premium tax credit (precompute_cliff_household.py's
 * mtr_baseline and mtr_ira).
 */
function MarginalRateChart({ data, title, height = 360 }) {
  const fpl = data.fpl;
  const year = data.year;

  const points = useMemo(() => {
    // Up to a little past where H.R. 1834's credit ends, as the premium chart.
    let maxIncome = fpl * 8;
    for (let i = data.ptc_ira.length - 1; i >= 0; i--) {
      if (data.ptc_ira[i] > 0) {
        maxIncome = Math.ceil(data.income[i] / 20000) * 20000 + 20000;
        break;
      }
    }
    return data.income
      .map((income, i) => ({
        income,
        current: 100 * data.mtr_baseline[i],
        revived: 100 * data.mtr_ira[i],
      }))
      .filter((point) => point.income >= MIN_INCOME && point.income <= maxIncome);
  }, [data, fpl]);

  const maxIncome = points.length ? points[points.length - 1].income : 0;
  const step = maxIncome > 160000 ? 40000 : 20000;
  const xTicks = [];
  for (let tick = Math.ceil(MIN_INCOME / step) * step; tick <= maxIncome; tick += step) xTicks.push(tick);

  const lines = [
    { key: "current", name: `${year}, current law` },
    { key: "revived", name: `${year}, H.R. 1834` },
  ];
  const plan = labelPlan(points, ["current", "revived"], { yDomain: [0, MAX_RATE], plotHeight: height - 52 });
  const [labelsFit, setLabelsFit] = useState(true);
  const showLegend = plan.crowded || !labelsFit;
  // The cliff, which the line labels keep off, with its name.
  const cliff = { x: fpl * 4, label: "Cliff at 400% FPL", position: "insideTopLeft", offset: 8 };

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const income = payload[0]?.payload?.income || 0;
    return (
      <div className="premium-chart-tooltip">
        <p className="premium-chart-tooltip-income">
          {formatCurrency(income)} to {formatCurrency(income + 1000)} ({Math.round((100 * income) / fpl)}% FPL)
        </p>
        {payload.map((entry) => (
          <p key={entry.dataKey}>
            <span className="premium-chart-swatch" style={{ background: entry.color }} />
            {entry.name}: {entry.value.toFixed(1)}%
          </p>
        ))}
      </div>
    );
  };

  return (
    <div className="premium-chart">
      {title && <h3 className="premium-chart-title">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid {...GRID} vertical={false} />
          <XAxis
            dataKey="income"
            type="number"
            domain={[MIN_INCOME, maxIncome]}
            ticks={xTicks}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            {...AXIS}
            height={44}
            label={{ value: "Household income", position: "insideBottom", offset: 0, ...AXIS_LABEL }}
          />
          <YAxis
            domain={[0, MAX_RATE]}
            allowDataOverflow
            ticks={[0, 20, 40, 60, 80, 100]}
            tickFormatter={(v) => `${v}%`}
            {...AXIS}
            width={48}
          />
          <Tooltip content={<CustomTooltip />} cursor={CURSOR} />
          {showLegend && (
            <Legend
              verticalAlign="top"
              align="left"
              iconType="plainline"
              wrapperStyle={{ fontSize: "13px", fontFamily: "var(--font-sans)", paddingBottom: "8px" }}
            />
          )}
          <ReferenceLine
            x={cliff.x}
            stroke="var(--color-gray-400)"
            strokeDasharray="4 4"
            label={{ value: cliff.label, position: cliff.position, offset: cliff.offset, ...AXIS_LABEL, fontSize: 11 }}
          />
          {lines.map(({ key, name }) => (
            <Line
              key={key}
              type="linear"
              dataKey={key}
              name={name}
              stroke={SCENARIO_STYLES[key].color}
              strokeWidth={2.5}
              dot={false}
              activeDot={ACTIVE_DOT}
              isAnimationActive={false}
            />
          ))}
          {!plan.crowded && (
            <Customized
              component={(props) => (
                <DirectLabels {...props} index={plan.index} references={[cliff]} onFit={setLabelsFit} hidden={!labelsFit} />
              )}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default MarginalRateChart;
