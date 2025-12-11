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
};

function HealthBenefitsChart({ data, chartState, householdInfo }) {
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
        netIncomeBaseline: data.net_income_baseline?.[i] || 0,
        netIncomeIRA: data.net_income_ira?.[i] || 0,
        netIncome700FPL: data.net_income_700fpl?.[i] || 0,
      }))
      .filter((d) => d.income <= maxIncome && d.income >= 0);
  }, [data, chartState]);

  // Determine which lines to show based on chart state
  const getVisibleLines = () => {
    switch (chartState) {
      case "all_programs":
        return ["medicaid", "chip", "ptcBaseline"];
      case "medicaid_focus":
        return ["medicaid", "ptcBaseline"];
      case "chip_focus":
        return ["chip", "medicaid", "ptcBaseline"];
      case "ptc_baseline":
      case "cliff_focus":
        return ["ptcBaseline"];
      case "ira_reform":
        return ["ptcBaseline", "ptcIRA"];
      case "ira_impact":
        return ["ptcIRA", "ptcBaseline", "iraGain"];
      case "both_reforms":
        return ["ptcBaseline", "ptcIRA", "ptc700FPL"];
      case "impact":
        return ["deltaIRA", "delta700FPL"];
      default:
        return ["ptcBaseline"];
    }
  };

  const visibleLines = getVisibleLines();
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

  // For impact view, calculate deltas
  const impactData = useMemo(() => {
    if (chartState !== "impact") return chartData;
    return chartData.map((d) => ({
      ...d,
      deltaIRA: d.ptcIRA - d.ptcBaseline,
      delta700FPL: d.ptc700FPL - d.ptcBaseline,
    }));
  }, [chartData, chartState]);

  const displayData = chartState === "impact" ? impactData : chartData;

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
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
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

          {/* IRA Impact Area - shaded region showing benefit of IRA extension over baseline */}
          {chartState === "ira_impact" && (
            <>
              {/* First draw IRA as filled area */}
              <Area
                type="monotone"
                dataKey="ptcIRA"
                name="IRA Extension"
                fill={COLORS.ira}
                fillOpacity={0.3}
                stroke={COLORS.ira}
                strokeWidth={2}
              />
              {/* Then draw baseline on top to "cut out" the overlap, showing only the difference */}
              <Area
                type="monotone"
                dataKey="ptcBaseline"
                name="Baseline (Current Law)"
                fill="#ffffff"
                fillOpacity={1}
                stroke={COLORS.baseline}
                strokeWidth={2}
              />
            </>
          )}

          {/* Medicaid */}
          {visibleLines.includes("medicaid") && (
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
          {visibleLines.includes("chip") && data?.chip?.some((v) => v > 0) && (
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

          {/* PTC Baseline - skip if ira_impact since Area handles it */}
          {visibleLines.includes("ptcBaseline") && chartState !== "ira_impact" && (
            <Line
              type="monotone"
              dataKey="ptcBaseline"
              name="PTC (Baseline)"
              stroke={COLORS.baseline}
              strokeWidth={2.5}
              dot={false}
            />
          )}

          {/* PTC IRA Reform - skip if ira_impact since Area handles it */}
          {visibleLines.includes("ptcIRA") && chartState !== "ira_impact" && (
            <Line
              type="monotone"
              dataKey="ptcIRA"
              name="PTC (IRA Extension)"
              stroke={COLORS.ira}
              strokeWidth={2.5}
              dot={false}
            />
          )}

          {/* PTC 700% FPL Reform */}
          {visibleLines.includes("ptc700FPL") && (
            <Line
              type="monotone"
              dataKey="ptc700FPL"
              name="PTC (700% FPL Bill)"
              stroke={COLORS.bipartisan}
              strokeWidth={2.5}
              dot={false}
            />
          )}

          {/* Delta IRA (for impact view) */}
          {visibleLines.includes("deltaIRA") && (
            <Line
              type="monotone"
              dataKey="deltaIRA"
              name="Gain from IRA Extension"
              stroke={COLORS.ira}
              strokeWidth={2.5}
              dot={false}
              fillOpacity={0.2}
            />
          )}

          {/* Delta 700% FPL (for impact view) */}
          {visibleLines.includes("delta700FPL") && (
            <Line
              type="monotone"
              dataKey="delta700FPL"
              name="Gain from 700% FPL Bill"
              stroke={COLORS.bipartisan}
              strokeWidth={2.5}
              dot={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export default HealthBenefitsChart;
