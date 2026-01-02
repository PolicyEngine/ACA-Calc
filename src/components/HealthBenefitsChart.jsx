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

    // Filter to reasonable income range
    const maxIncome = chartState === "cliff_focus" ? fpl * 5 : fpl * 8;

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
      "both_reforms": ["ptcBaseline", "ptcIRA", "ptc700FPL", "ptcAdditionalBracket", "ptcSimplifiedBracket"],
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

  // For impact view and ira_impact, calculate deltas (gains over baseline)
  const impactData = useMemo(() => {
    if (chartState !== "impact" && chartState !== "ira_impact") return chartData;
    return chartData.map((d) => ({
      ...d,
      deltaIRA: Math.max(0, d.ptcIRA - d.ptcBaseline),
      delta700FPL: Math.max(0, d.ptc700FPL - d.ptcBaseline),
      deltaAdditionalBracket: Math.max(0, d.ptcAdditionalBracket - d.ptcBaseline),
      deltaSimplifiedBracket: Math.max(0, d.ptcSimplifiedBracket - d.ptcBaseline),
    }));
  }, [chartData, chartState]);

  const displayData = (chartState === "impact" || chartState === "ira_impact") ? impactData : chartData;

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
        return "Change in Annual Benefits from Reform";
      case "cliff_focus":
        return "The 400% FPL Subsidy Cliff";
      case "medicaid_focus":
        return "Medicaid Coverage by Income";
      case "chip_focus":
        return "CHIP Coverage by Income";
      case "ira_reform":
        return "Baseline vs IRA Extension";
      case "ira_impact":
        return "IRA Extension vs Current Law";
      case "both_reforms":
        return "Comparing All Policy Options";
      case "all_programs":
        return "Health Coverage Programs by Income";
      default:
        return "Annual Health Benefits by Income (2026)";
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
            label={{
              value: "Household Income",
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
            label={{
              value: chartState === "impact" ? "Benefit Gain" : "Annual Value",
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

          {/* STACKED GAIN VIEW - for "Gain from Extension" tab (ira_impact) */}
          {chartState === "ira_impact" && (
            <>
              {/* Baseline area in gray - always show as the base */}
              {shouldShow("ptcBaseline") && (
                <Area
                  type="monotone"
                  dataKey="ptcBaseline"
                  name="Baseline (Current Law)"
                  fill={COLORS.baseline}
                  fillOpacity={0.4}
                  stroke={COLORS.baseline}
                  strokeWidth={2}
                  stackId="gain_stack"
                />
              )}
              {/* IRA gain stacked on top */}
              {shouldShow("ptcIRA") && (
                <Area
                  type="monotone"
                  dataKey="deltaIRA"
                  name="+ IRA Extension"
                  fill={COLORS.ira}
                  fillOpacity={0.5}
                  stroke={COLORS.ira}
                  strokeWidth={2}
                  stackId="gain_stack"
                />
              )}
              {/* 700% FPL gain stacked */}
              {shouldShow("ptc700FPL") && (
                <Area
                  type="monotone"
                  dataKey="delta700FPL"
                  name="+ 700% FPL Bill"
                  fill={COLORS.bipartisan}
                  fillOpacity={0.5}
                  stroke={COLORS.bipartisan}
                  strokeWidth={2}
                  stackId="gain_stack"
                />
              )}
              {/* Additional Bracket gain stacked */}
              {shouldShow("ptcAdditionalBracket") && (
                <Area
                  type="monotone"
                  dataKey="deltaAdditionalBracket"
                  name="+ Additional Bracket"
                  fill={COLORS.additionalBracket}
                  fillOpacity={0.5}
                  stroke={COLORS.additionalBracket}
                  strokeWidth={2}
                  stackId="gain_stack"
                />
              )}
              {/* Simplified Bracket gain stacked */}
              {shouldShow("ptcSimplifiedBracket") && (
                <Area
                  type="monotone"
                  dataKey="deltaSimplifiedBracket"
                  name="+ Simplified Bracket"
                  fill={COLORS.simplifiedBracket}
                  fillOpacity={0.5}
                  stroke={COLORS.simplifiedBracket}
                  strokeWidth={2}
                  stackId="gain_stack"
                />
              )}
            </>
          )}

          {/* COMPARISON VIEW - for "Baseline vs Extension" tab (both_reforms) */}
          {chartState === "both_reforms" && (
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

              {shouldShow("ptc700FPL") && (
                <Area
                  type="monotone"
                  dataKey="ptc700FPL"
                  name="PTC (700% FPL Bill)"
                  fill={COLORS.bipartisan}
                  fillOpacity={0.15}
                  stroke={COLORS.bipartisan}
                  strokeWidth={2.5}
                />
              )}

              {shouldShow("ptcAdditionalBracket") && (
                <Area
                  type="monotone"
                  dataKey="ptcAdditionalBracket"
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
                  dataKey="ptcSimplifiedBracket"
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
          {!externalVisibleLines && chartState !== "ira_impact" && chartState !== "both_reforms" && (
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
