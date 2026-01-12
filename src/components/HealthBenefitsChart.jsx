import { useMemo } from "react";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import "./HealthBenefitsChart.css";

// Chart colors - PolicyEngine appv2 design tokens
const COLORS = {
  medicaid: "#319795",  // primary teal
  chip: "#38B2AC",      // teal-400
  baseline: "#9CA3AF",  // gray-400
  ira: "#0284C7",       // blue-600 from appv2
  bipartisan: "#7c3aed",
  additionalBracket: "#059669",  // emerald-600
  simplifiedBracket: "#d97706",  // amber-600
};

function HealthBenefitsChart({ data, chartState, householdInfo, visibleLines: externalVisibleLines }) {
  // Process data for the chart based on current state
  const chartData = useMemo(() => {
    if (!data) return [];

    const income = data.income || [];
    const fpl = data.fpl || 31200;

    // Find where all policies reach $0 - extend to that point
    // IRA extends furthest, so find where IRA hits 0
    let maxIncomeForPolicies = fpl * 8;
    if (data.ptc_ira) {
      for (let i = data.ptc_ira.length - 1; i >= 0; i--) {
        if (data.ptc_ira[i] > 0) {
          // Round up to nearest $20k
          maxIncomeForPolicies = Math.ceil(income[i] / 20000) * 20000 + 20000;
          break;
        }
      }
    }

    // Filter to reasonable income range
    const maxIncome = chartState === "cliff_focus" ? fpl * 5 : maxIncomeForPolicies;

    return income
      .map((inc, i) => ({
        income: inc,
        incomeFPL: (inc / fpl) * 100,
        medicaid: data.medicaid?.[i] || 0,
        chip: data.chip?.[i] || 0,
        ptcBaseline: data.ptc_baseline?.[i] || 0,
        ptcIRA: data.ptc_ira?.[i] || 0,
        ptc700FPL: data.ptc_700fpl?.[i] || 0,
        ptcAdditionalBracket: data.ptc_additional_bracket?.[i] || 0,
        ptcSimplifiedBracket: data.ptc_simplified_bracket?.[i] || 0,
        netIncomeBaseline: data.net_income_baseline?.[i] || 0,
        netIncomeIRA: data.net_income_ira?.[i] || 0,
        netIncome700FPL: data.net_income_700fpl?.[i] || 0,
      }))
      .filter((d) => d.income <= maxIncome && d.income >= 0);
  }, [data, chartState]);

  // Helper to check if a line should be shown
  const shouldShow = (lineKey) => {
    // When external toggle controls are provided, use them directly
    if (externalVisibleLines) {
      switch (lineKey) {
        case "ptcBaseline": return externalVisibleLines.baseline === true;
        case "ptcIRA": return externalVisibleLines.ira === true;
        case "ptc700FPL": return externalVisibleLines.fpl700 === true;
        case "ptcAdditionalBracket": return externalVisibleLines.additionalBracket === true;
        case "ptcSimplifiedBracket": return externalVisibleLines.simplifiedBracket === true;
        case "medicaid": return false; // Not togglable
        case "chip": return false; // Not togglable
        default: return false;
      }
    }

    // Fallback to chart state for AI explanation mode
    const stateLines = {
      "all_programs": ["medicaid", "chip", "ptcBaseline"],
      "medicaid_focus": ["medicaid", "ptcBaseline"],
      "chip_focus": ["chip", "medicaid", "ptcBaseline"],
      "ptc_baseline": ["ptcBaseline"],
      "cliff_focus": ["ptcBaseline"],
      "ira_reform": ["ptcBaseline", "ptcIRA"],
      "ira_impact": ["ptcIRA", "ptcBaseline"],
      "fpl700_focus": ["ptcBaseline", "ptc700FPL"],
      "additional_focus": ["ptcBaseline", "ptcAdditionalBracket"],
      "simplified_focus": ["ptcBaseline", "ptcSimplifiedBracket"],
      "both_reforms": ["ptcBaseline", "ptcIRA", "ptc700FPL"],
      "impact": ["deltaIRA", "delta700FPL"],
    };

    const lines = stateLines[chartState] || ["ptcBaseline"];
    return lines.includes(lineKey);
  };

  // For backward compatibility with existing code
  const visibleLines = externalVisibleLines
    ? Object.entries(externalVisibleLines)
        .filter(([_, v]) => v)
        .map(([k]) => {
          const mapping = {
            baseline: "ptcBaseline",
            ira: "ptcIRA",
            fpl700: "ptc700FPL",
            additionalBracket: "ptcAdditionalBracket",
            simplifiedBracket: "ptcSimplifiedBracket"
          };
          return mapping[k];
        })
        .filter(Boolean)
    : ["ptcBaseline"];
  const fpl = data?.fpl || 31200;

  // Find where baseline PTC actually drops to zero (the cliff)
  const baselineCliffIncome = useMemo(() => {
    if (!data?.ptc_baseline || !data?.income) return fpl * 4;
    for (let i = 1; i < data.ptc_baseline.length; i++) {
      if (data.ptc_baseline[i] === 0 && data.ptc_baseline[i - 1] > 0) {
        return data.income[i];
      }
    }
    return fpl * 4; // fallback
  }, [data, fpl]);

  // For impact/focus views, calculate deltas (gains over baseline)
  const deltaStates = ["impact", "ira_impact", "gain_view", "fpl700_focus", "additional_focus", "simplified_focus", "both_reforms"];
  const impactData = useMemo(() => {
    if (!deltaStates.includes(chartState)) return chartData;
    return chartData.map((d) => ({
      ...d,
      deltaIRA: Math.max(0, d.ptcIRA - d.ptcBaseline),
      delta700FPL: Math.max(0, d.ptc700FPL - d.ptcBaseline),
      delta700FPLFromIRA: Math.max(0, d.ptc700FPL - d.ptcIRA),
      // For both_reforms: IRA gain over 700% FPL (shows where IRA extends beyond 700% bill)
      deltaIRAOver700FPL: Math.max(0, d.ptcIRA - Math.max(d.ptcBaseline, d.ptc700FPL)),
      deltaAdditionalBracket: Math.max(0, d.ptcAdditionalBracket - d.ptcBaseline),
      deltaSimplifiedBracket: Math.max(0, d.ptcSimplifiedBracket - d.ptcBaseline),
    }));
  }, [chartData, chartState]);

  const displayData = deltaStates.includes(chartState) ? impactData : chartData;

  // Format currency for tooltip
  const formatCurrency = (value) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const income = payload[0]?.payload?.income || 0;
      const fplPct = ((income / fpl) * 100).toFixed(0);

      return (
        <div className="chart-tooltip">
          <p className="tooltip-income">
            {formatCurrency(income)} ({fplPct}% FPL)
          </p>
          {payload.map((entry, index) => (
            <p
              key={index}
              className="tooltip-item"
              style={{ color: entry.color }}
            >
              {entry.name}: {formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Get chart title based on state
  const getChartTitle = () => {
    switch (chartState) {
      case "impact":
        return "Change in annual benefits from reform";
      case "cliff_focus":
        return "The 400% FPL subsidy cliff";
      case "medicaid_focus":
        return "Medicaid coverage by income";
      case "chip_focus":
        return "CHIP coverage by income";
      case "ira_reform":
        return "Baseline vs IRA extension";
      case "ira_impact":
        return "IRA extension vs current law";
      case "fpl700_focus":
        return "700% FPL bill vs current law";
      case "additional_focus":
        return "Additional bracket vs current law";
      case "simplified_focus":
        return "Simplified bracket vs current law";
      case "gain_view":
        return "Gain from reform vs baseline";
      case "both_reforms":
        return "Comparing all policy options";
      case "all_programs":
        return "Health coverage programs by income";
      default:
        return "Annual health benefits by income (2026)";
    }
  };

  // Determine Y-axis domain
  const getYDomain = () => {
    if (chartState === "impact") {
      return [0, "auto"];
    }
    return [0, "auto"];
  };

  // Get line opacity based on focus
  const getLineOpacity = (lineKey) => {
    if (chartState === "medicaid_focus" && lineKey !== "medicaid") return 0.3;
    if (chartState === "chip_focus" && lineKey !== "chip") return 0.3;
    return 1;
  };

  return (
    <div className="chart-container">
      <h3 className="chart-title">{getChartTitle()}</h3>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={displayData}
          margin={{ top: 20, right: 30, left: 45, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="income"
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            stroke="#6b7280"
            fontSize={12}
            ticks={(() => {
              const maxIncome = chartData.length > 0 ? chartData[chartData.length - 1].income : 200000;
              const ticks = [];
              for (let i = 0; i <= maxIncome; i += 20000) {
                ticks.push(i);
              }
              return ticks;
            })()}
            label={{
              value: "Household income",
              position: "bottom",
              offset: 40,
              fill: "#6b7280",
            }}
          />
          <YAxis
            tickFormatter={(v) => v === 0 ? "$0" : `$${(v / 1000).toFixed(0)}k`}
            stroke="#6b7280"
            fontSize={12}
            domain={getYDomain()}
            ticks={(() => {
              const maxY = Math.max(...chartData.map(d => Math.max(d.ptcBaseline || 0, d.ptcIRA || 0, d.ptc700FPL || 0)));
              const ticks = [];
              for (let i = 0; i <= maxY + 4000; i += 4000) {
                ticks.push(i);
              }
              return ticks;
            })()}
            label={{
              value: (chartState === "impact" || chartState === "gain_view") ? "Gain over baseline" : "Annual value",
              angle: -90,
              position: "insideLeft",
              offset: 10,
              fill: "#6b7280",
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="top"
            height={36}
            wrapperStyle={{ fontSize: "12px" }}
          />

          {/* FPL Reference Lines */}
          <ReferenceLine
            x={fpl * 1}
            stroke="#d1d5db"
            strokeDasharray="5 5"
            label={{ value: "100%", position: "top", fill: "#9ca3af", fontSize: 10 }}
          />
          <ReferenceLine
            x={baselineCliffIncome}
            stroke={chartState === "cliff_focus" ? "#ef4444" : "#d1d5db"}
            strokeDasharray={chartState === "cliff_focus" ? "8 4" : "5 5"}
            strokeWidth={chartState === "cliff_focus" ? 2 : 1}
            label={{
              value: chartState === "cliff_focus" ? "400% FPL Cliff" : "400%",
              position: "top",
              fill: chartState === "cliff_focus" ? "#ef4444" : "#9ca3af",
              fontSize: chartState === "cliff_focus" ? 12 : 10,
              fontWeight: chartState === "cliff_focus" ? 600 : 400,
            }}
          />
          {chartState === "both_reforms" && (
            <ReferenceLine
              x={fpl * 7}
              stroke="#d1d5db"
              strokeDasharray="5 5"
              label={{ value: "700%", position: "top", fill: "#9ca3af", fontSize: 10 }}
            />
          )}

          {/* IRA EXTENSION vs CURRENT LAW - stacked area showing baseline + IRA gain */}
          {chartState === "ira_impact" && (
            <>
              {/* Baseline area in gray */}
              <Area
                type="monotone"
                dataKey="ptcBaseline"
                name="Baseline (Current Law)"
                fill={COLORS.baseline}
                fillOpacity={0.4}
                stroke={COLORS.baseline}
                strokeWidth={2}
                stackId="ira_stack"
              />
              {/* IRA gain stacked on top in blue */}
              <Area
                type="monotone"
                dataKey="deltaIRA"
                name="Additional from IRA"
                fill={COLORS.ira}
                fillOpacity={0.5}
                stroke={COLORS.ira}
                strokeWidth={2}
                stackId="ira_stack"
              />
            </>
          )}

          {/* 700% FPL FOCUS - baseline + 700% FPL bill only */}
          {chartState === "fpl700_focus" && (
            <>
              <Area
                type="monotone"
                dataKey="ptcBaseline"
                name="Baseline (Current Law)"
                fill={COLORS.baseline}
                fillOpacity={0.4}
                stroke={COLORS.baseline}
                strokeWidth={2}
                stackId="fpl700_stack"
              />
              <Area
                type="monotone"
                dataKey="delta700FPL"
                name="Additional from 700% FPL Bill"
                fill={COLORS.bipartisan}
                fillOpacity={0.5}
                stroke={COLORS.bipartisan}
                strokeWidth={2}
                stackId="fpl700_stack"
              />
            </>
          )}

          {/* ADDITIONAL BRACKET FOCUS - baseline + additional bracket only */}
          {chartState === "additional_focus" && (
            <>
              <Area
                type="monotone"
                dataKey="ptcBaseline"
                name="Baseline (Current Law)"
                fill={COLORS.baseline}
                fillOpacity={0.4}
                stroke={COLORS.baseline}
                strokeWidth={2}
                stackId="additional_stack"
              />
              <Area
                type="monotone"
                dataKey="deltaAdditionalBracket"
                name="Additional from CRFB Bracket"
                fill={COLORS.additionalBracket}
                fillOpacity={0.5}
                stroke={COLORS.additionalBracket}
                strokeWidth={2}
                stackId="additional_stack"
              />
            </>
          )}

          {/* SIMPLIFIED BRACKET FOCUS - baseline + simplified bracket only */}
          {chartState === "simplified_focus" && (
            <>
              <Area
                type="monotone"
                dataKey="ptcBaseline"
                name="Baseline (Current Law)"
                fill={COLORS.baseline}
                fillOpacity={0.4}
                stroke={COLORS.baseline}
                strokeWidth={2}
                stackId="simplified_stack"
              />
              <Area
                type="monotone"
                dataKey="deltaSimplifiedBracket"
                name="Additional from Simplified Bracket"
                fill={COLORS.simplifiedBracket}
                fillOpacity={0.5}
                stroke={COLORS.simplifiedBracket}
                strokeWidth={2}
                stackId="simplified_stack"
              />
            </>
          )}

          {/* GAIN VIEW - lines only showing gains over baseline */}
          {chartState === "gain_view" && (
            <>
              {shouldShow("ptcIRA") && (
                <Line
                  type="monotone"
                  dataKey="deltaIRA"
                  name="Gain from IRA Extension"
                  stroke={COLORS.ira}
                  strokeWidth={2.5}
                  dot={false}
                />
              )}
              {shouldShow("ptc700FPL") && (
                <Line
                  type="monotone"
                  dataKey="delta700FPL"
                  name="Gain from 700% FPL Bill"
                  stroke={COLORS.bipartisan}
                  strokeWidth={2.5}
                  dot={false}
                />
              )}
              {shouldShow("ptcAdditionalBracket") && (
                <Line
                  type="monotone"
                  dataKey="deltaAdditionalBracket"
                  name="Gain from Additional Bracket"
                  stroke={COLORS.additionalBracket}
                  strokeWidth={2.5}
                  dot={false}
                />
              )}
              {shouldShow("ptcSimplifiedBracket") && (
                <Line
                  type="monotone"
                  dataKey="deltaSimplifiedBracket"
                  name="Gain from Simplified Bracket"
                  stroke={COLORS.simplifiedBracket}
                  strokeWidth={2.5}
                  dot={false}
                />
              )}
            </>
          )}

          {/* COMPARISON VIEW - for "Baseline vs Extension" tab (both_reforms) */}
          {chartState === "both_reforms" && (
            <>
              {/* Stacked areas: baseline (grey) + 700% FPL gain (purple) + IRA gain beyond 700% (blue) */}
              {shouldShow("ptcBaseline") && (
                <Area
                  type="monotone"
                  dataKey="ptcBaseline"
                  name="PTC (Baseline)"
                  fill={COLORS.baseline}
                  fillOpacity={0.4}
                  stroke={COLORS.baseline}
                  strokeWidth={2}
                  stackId="comparison_stack"
                />
              )}

              {shouldShow("ptc700FPL") && (
                <Area
                  type="monotone"
                  dataKey="delta700FPL"
                  name="PTC (700% FPL Bill)"
                  fill={COLORS.bipartisan}
                  fillOpacity={0.5}
                  stroke={COLORS.bipartisan}
                  strokeWidth={2}
                  stackId="comparison_stack"
                />
              )}

              {shouldShow("ptcIRA") && (
                <Area
                  type="monotone"
                  dataKey="deltaIRAOver700FPL"
                  name="PTC (IRA Extension)"
                  fill={COLORS.ira}
                  fillOpacity={0.5}
                  stroke={COLORS.ira}
                  strokeWidth={2}
                  stackId="comparison_stack"
                />
              )}

              {shouldShow("ptcAdditionalBracket") && (
                <Area
                  type="monotone"
                  dataKey="deltaAdditionalBracket"
                  name="PTC (Additional Bracket)"
                  fill={COLORS.additionalBracket}
                  fillOpacity={0.15}
                  stroke={COLORS.additionalBracket}
                  strokeWidth={2.5}
                />
              )}

              {shouldShow("ptcSimplifiedBracket") && (
                <Area
                  type="monotone"
                  dataKey="deltaSimplifiedBracket"
                  name="PTC (Simplified Bracket)"
                  fill={COLORS.simplifiedBracket}
                  fillOpacity={0.15}
                  stroke={COLORS.simplifiedBracket}
                  strokeWidth={2.5}
                />
              )}
            </>
          )}

          {/* AI EXPLANATION MODE - for scrollytelling */}
          {!externalVisibleLines && chartState !== "ira_impact" && chartState !== "both_reforms" && chartState !== "fpl700_focus" && chartState !== "additional_focus" && chartState !== "simplified_focus" && (
            <>
              {shouldShow("ptcBaseline") && (
                <Area
                  type="monotone"
                  dataKey="ptcBaseline"
                  name="PTC (Baseline)"
                  fill={COLORS.baseline}
                  fillOpacity={0.15}
                  stroke={COLORS.baseline}
                  strokeWidth={2.5}
                />
              )}

              {shouldShow("ptcIRA") && (
                <Area
                  type="monotone"
                  dataKey="ptcIRA"
                  name="PTC (IRA Extension)"
                  fill={COLORS.ira}
                  fillOpacity={0.15}
                  stroke={COLORS.ira}
                  strokeWidth={2.5}
                />
              )}

              {/* Medicaid */}
              {shouldShow("medicaid") && (
                <Line
                  type="monotone"
                  dataKey="medicaid"
                  name="Medicaid"
                  stroke={COLORS.medicaid}
                  strokeWidth={2.5}
                  dot={false}
                  opacity={getLineOpacity("medicaid")}
                />
              )}

              {/* CHIP */}
              {shouldShow("chip") && data?.chip?.some((v) => v > 0) && (
                <Line
                  type="monotone"
                  dataKey="chip"
                  name="CHIP"
                  stroke={COLORS.chip}
                  strokeWidth={2.5}
                  dot={false}
                  opacity={getLineOpacity("chip")}
                />
              )}
            </>
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export default HealthBenefitsChart;
