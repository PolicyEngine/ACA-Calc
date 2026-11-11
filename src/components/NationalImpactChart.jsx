import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import "./NationalImpactChart.css";

// National figures from precompute_national.py (policyengine-us over its
// default microdata).
import national from "../data/national_impacts.json";

const COLORS = {
  prior: "#9CA3AF", // gray-400
  current: "#4B5563", // gray-600
  revived: "#0284C7", // blue-600
  deep: "#0c4a6e", // sky-900
};

// policyengine.py's winners-and-losers bands.
const WINNER_BANDS = [
  { key: "gain_more_than_5pct", label: "Gain more than 5%", color: "#0284C7" },
  { key: "gain_less_than_5pct", label: "Gain less than 5%", color: "#7dd3fc" },
  { key: "no_change", label: "No change", color: "#e5e7eb" },
  { key: "lose_less_than_5pct", label: "Lose less than 5%", color: "#fca5a5" },
  { key: "lose_more_than_5pct", label: "Lose more than 5%", color: "#dc2626" },
];

const POVERTY_GROUPS = [
  ["all", "Everyone"],
  ["child", "Children"],
  ["adult", "Adults 18–64"],
  ["senior", "Seniors 65+"],
];

const billions = (value) => `$${(value / 1e9).toFixed(1)}B`;
const millions = (value) => `${(value / 1e6).toFixed(1)}M`;
const dollars = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
const signedPercent = (value, digits = 1) => `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(digits)}%`;
const relativeChange = (from, to) => (from === 0 ? 0 : (100 * (to - from)) / from);

const tooltipStyle = {
  backgroundColor: "white",
  border: "1px solid #e5e7eb",
  borderRadius: "8px",
  fontSize: "13px",
};

function Header({ title, subtitle }) {
  return (
    <div className="national-chart-header">
      <h3>{title}</h3>
      {subtitle && <p>{subtitle}</p>}
    </div>
  );
}

function SpendingChart() {
  const year = national.year;
  const priorYear = String(year - 1);
  const scenarios = [
    { name: `${priorYear}, current law`, values: national.current_law[priorYear], color: COLORS.prior },
    { name: `${year}, current law`, values: national.current_law[String(year)], color: COLORS.current },
    { name: `${year}, H.R. 1834`, values: national.enhanced, color: COLORS.revived },
  ];
  const panels = [
    { title: "Federal spending on premium tax credits", key: "total_ptc", format: billions },
    { title: "People receiving a credit", key: "people_receiving", format: millions },
  ];
  return (
    <div className="national-chart">
      <Header title="Premium tax credits nationwide" subtitle="PolicyEngine estimates, static" />
      {panels.map((panel) => (
        <div key={panel.key} className="national-chart-panel">
          <h4>{panel.title}</h4>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={scenarios.map((s) => ({ name: s.name, value: s.values[panel.key], color: s.color }))}
              margin={{ top: 20, right: 20, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={panel.format} tick={{ fontSize: 11 }} width={60} />
              <Tooltip formatter={(value) => [panel.format(value), panel.title]} contentStyle={tooltipStyle} />
              <Bar dataKey="value" isAnimationActive={false}>
                {scenarios.map((s) => (
                  <Cell key={s.name} fill={s.color} />
                ))}
                <LabelList dataKey="value" position="top" formatter={panel.format} fontSize={11} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );
}

function DecileChart() {
  const data = national.deciles.map((row) => ({
    decile: row.decile,
    change: row.absolute_change,
    relative: row.relative_change,
  }));
  return (
    <div className="national-chart">
      <Header
        title={`Average change in household net income, ${national.year}`}
        subtitle="H.R. 1834 against current law, by income decile (each decile holds a tenth of people)"
      />
      <div className="national-chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 20, left: 10, bottom: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis
              dataKey="decile"
              tick={{ fontSize: 11 }}
              label={{ value: "Income decile", position: "bottom", offset: 10, fill: "#6b7280", fontSize: 12 }}
            />
            <YAxis tickFormatter={dollars} tick={{ fontSize: 11 }} width={60} />
            <Tooltip
              formatter={(value, name, item) => [
                `${dollars(value)} a year (${signedPercent(item.payload.relative, 2)} of net income)`,
                "Average change",
              ]}
              labelFormatter={(decile) => `Decile ${decile}`}
              contentStyle={tooltipStyle}
            />
            <Bar dataKey="change" fill={COLORS.revived} isAnimationActive={false}>
              <LabelList dataKey="change" position="top" formatter={dollars} fontSize={10} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function WinnersChart() {
  const bands = WINNER_BANDS.filter((band) =>
    [national.winners_losers.all, ...national.winners_losers.deciles].some((row) => row[band.key] > 0)
  );
  const toRow = (label, row) => ({
    label,
    ...Object.fromEntries(bands.map((band) => [band.key, 100 * row[band.key]])),
  });
  const data = [
    toRow("All", national.winners_losers.all),
    ...national.winners_losers.deciles.map((row) => toRow(String(row.decile), row)),
  ];
  return (
    <div className="national-chart">
      <Header
        title="Share of people by change in household net income"
        subtitle="H.R. 1834 against current law, overall and by income decile"
      />
      <div className="national-chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={40} />
            <Tooltip formatter={(value, name) => [`${value.toFixed(1)}%`, name]} contentStyle={tooltipStyle} />
            <Legend verticalAlign="top" height={30} wrapperStyle={{ fontSize: "12px" }} />
            {bands.map((band) => (
              <Bar
                key={band.key}
                dataKey={band.key}
                name={band.label}
                stackId="people"
                fill={band.color}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function PovertyChart() {
  const data = POVERTY_GROUPS.map(([key, label]) => {
    const spm = national.poverty.spm[key];
    const deep = national.poverty.deep[key];
    return {
      label,
      spm: relativeChange(spm.baseline_rate, spm.reform_rate),
      deep: relativeChange(deep.baseline_rate, deep.reform_rate),
      spmRates: [spm.baseline_rate, spm.reform_rate],
      deepRates: [deep.baseline_rate, deep.reform_rate],
    };
  });
  const rates = ([from, to]) => `${(100 * from).toFixed(2)}% to ${(100 * to).toFixed(2)}%`;
  return (
    <div className="national-chart">
      <Header
        title="Change in poverty rates (Supplemental Poverty Measure)"
        subtitle="H.R. 1834 against current law, relative change in each group's rate"
      />
      <div className="national-chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 20, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => signedPercent(v)} tick={{ fontSize: 11 }} width={60} />
            <Tooltip
              formatter={(value, name, item) => [
                `${signedPercent(value, 2)} (${rates(name === "Poverty" ? item.payload.spmRates : item.payload.deepRates)})`,
                name,
              ]}
              contentStyle={tooltipStyle}
            />
            <Legend verticalAlign="top" height={30} wrapperStyle={{ fontSize: "12px" }} />
            <Bar dataKey="spm" name="Poverty" fill={COLORS.revived} isAnimationActive={false}>
              <LabelList dataKey="spm" position="bottom" formatter={(v) => signedPercent(v)} fontSize={10} />
            </Bar>
            <Bar dataKey="deep" name="Deep poverty" fill={COLORS.deep} isAnimationActive={false}>
              <LabelList dataKey="deep" position="bottom" formatter={(v) => signedPercent(v)} fontSize={10} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function InequalityChart() {
  const { baseline, reform } = national.inequality;
  const measures = [
    ["gini", "Gini index", (v) => v.toFixed(4)],
    ["top_10_share", "Top 10% share", (v) => `${(100 * v).toFixed(2)}%`],
    ["top_1_share", "Top 1% share", (v) => `${(100 * v).toFixed(2)}%`],
  ];
  const data = measures.map(([key, label, format]) => ({
    label,
    change: relativeChange(baseline[key], reform[key]),
    detail: `${format(baseline[key])} to ${format(reform[key])}`,
  }));
  return (
    <div className="national-chart">
      <Header
        title="Change in inequality of household net income"
        subtitle="H.R. 1834 against current law, relative change"
      />
      <div className="national-chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 20, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => signedPercent(v, 2)} tick={{ fontSize: 11 }} width={60} />
            <Tooltip
              formatter={(value, name, item) => [`${signedPercent(value, 2)} (${item.payload.detail})`, "Change"]}
              contentStyle={tooltipStyle}
            />
            <Bar dataKey="change" fill={COLORS.revived} isAnimationActive={false}>
              <LabelList dataKey="change" position="bottom" formatter={(v) => signedPercent(v, 2)} fontSize={10} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

const CHARTS = {
  spending: SpendingChart,
  deciles: DecileChart,
  winners: WinnersChart,
  poverty: PovertyChart,
  inequality: InequalityChart,
};

function NationalImpactChart({ mode }) {
  const Chart = CHARTS[mode] || SpendingChart;
  return <Chart />;
}

export default NationalImpactChart;
