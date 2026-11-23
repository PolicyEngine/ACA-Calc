// Direct labels for line charts, in place of a legend (after the story charts
// in PolicyEngine/uk-growth-with-ai): each line's name sits beside it, as close
// as it can get to the income where the lines are furthest apart without
// touching a line, a reference line, a reference line's name or another
// label. The chart shows its legend instead when no point keeps the lines at
// least MIN_GAP_PX apart (labelPlan), or when a name finds no clear spot, as
// on a phone (DirectLabels' onFit).

import { useEffect } from "react";

export const MIN_GAP_PX = 18;
const FONT_SIZE = 12;
// A label's box around its baseline, for 12px text.
const ASCENT = 10;
const DESCENT = 3;
// From the line to the label's box, across.
const OFFSET_X = 6;
// From the line to the label's box, up or down.
const OFFSET_Y = 6;
// Kept free of lines around each label's box: the text's 2px outline (in the
// card's color, which would cut a line it crossed) and half a line's width,
// with a pixel to spare.
const CLEARANCE = 4;

/**
 * Where to label the lines `keys` of `data`: the index, between the `from` and
 * `to` shares of the points, where the closest two lines are furthest apart
 * across the neighboring 2% of points (so not in the moment between two
 * lines' drops), and whether even there they're too close to label
 * (`crowded`). The gap is converted to pixels with the y domain and the plot's
 * height.
 */
export function labelPlan(data, keys, { yDomain, plotHeight, from = 0.35, to = 0.95 }) {
  const n = data.length;
  if (!n || !keys.length) return { index: -1, crowded: true };
  const lo = Math.floor(n * from);
  const hi = Math.max(lo + 1, Math.floor(n * to));
  if (keys.length === 1) {
    for (let i = Math.floor(n * 0.7); i >= lo; i--) {
      if (Number.isFinite(data[i]?.[keys[0]])) return { index: i, crowded: false };
    }
    return { index: -1, crowded: true };
  }
  // A point off the axis (a value the chart clips) can't hold a label.
  const onAxis = (y) => Number.isFinite(y) && y >= yDomain[0] && y <= yDomain[1];
  const gapAt = (i) => {
    const ys = keys.map((key) => data[i]?.[key]);
    if (!ys.every(onAxis)) return 0;
    const sorted = [...ys].sort((a, b) => a - b);
    let gap = Infinity;
    for (let j = 1; j < sorted.length; j++) gap = Math.min(gap, sorted[j] - sorted[j - 1]);
    return gap;
  };
  const gaps = data.map((_, i) => gapAt(i));
  const window = Math.max(1, Math.round(n * 0.02));
  let best = { index: -1, gap: -Infinity };
  for (let i = lo; i < hi && i < n; i++) {
    if (!gaps[i]) continue;
    let gap = Infinity;
    for (let j = Math.max(0, i - window); j <= Math.min(n - 1, i + window); j++) gap = Math.min(gap, gaps[j]);
    if (gap > best.gap) best = { index: i, gap };
  }
  const span = yDomain[1] - yDomain[0];
  const gapPx = best.index < 0 || !(span > 0) ? 0 : (best.gap / span) * plotHeight;
  return { index: best.index, crowded: gapPx < MIN_GAP_PX };
}

let probe;
const widths = new Map();

/**
 * The width of `text` as an SVG text in the page's sans-serif font with
 * tabular figures, as the charts draw it, measured on a hidden SVG. Kept once
 * the page's fonts have loaded.
 */
function textWidth(text, size = FONT_SIZE, weight = 600) {
  if (typeof document === "undefined") return text.length * size * 0.65;
  const key = `${weight} ${size} ${text}`;
  if (widths.has(key)) return widths.get(key);
  if (!probe) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("aria-hidden", "true");
    svg.style.cssText = "position: absolute; width: 0; height: 0; overflow: hidden; visibility: hidden";
    probe = document.createElementNS("http://www.w3.org/2000/svg", "text");
    probe.style.fontFamily = "var(--font-sans)";
    probe.style.fontVariantNumeric = "tabular-nums";
    svg.appendChild(probe);
    document.body.appendChild(svg);
  }
  probe.style.fontSize = `${size}px`;
  probe.style.fontWeight = String(weight);
  probe.textContent = text;
  const width = probe.getComputedTextLength();
  if (document.fonts?.status === "loaded") widths.set(key, width);
  return width;
}

const overlaps = (a, b) => a.x1 < b.x2 && b.x1 < a.x2 && a.y1 < b.y2 && b.y1 < a.y2;
const grow = (box, by) => ({ x1: box.x1 - by, y1: box.y1 - by, x2: box.x2 + by, y2: box.y2 + by });
const finite = (point) => point && Number.isFinite(point.x) && Number.isFinite(point.y);

/** Whether the segment from p to q passes through `box` (Liang–Barsky). */
function crosses(p, q, box) {
  const dx = q.x - p.x;
  const dy = q.y - p.y;
  let t0 = 0;
  let t1 = 1;
  const edges = [
    [-dx, p.x - box.x1],
    [dx, box.x2 - p.x],
    [-dy, p.y - box.y1],
    [dy, box.y2 - p.y],
  ];
  for (const [step, room] of edges) {
    if (step === 0) {
      if (room < 0) return false;
      continue;
    }
    const t = room / step;
    if (step < 0) {
      if (t > t1) return false;
      t0 = Math.max(t0, t);
    } else {
      if (t < t0) return false;
      t1 = Math.min(t1, t);
    }
  }
  return true;
}

/**
 * The box a reference line's name takes at the top of the plot, for the
 * positions the charts use (Recharts' Label on a vertical line).
 */
function referenceLabelBox(x, top, { label, position = "insideTopRight", offset = 5, fontSize = 11 }) {
  const width = textWidth(label, fontSize, 400);
  const x1 = position === "insideTopLeft" ? x + offset : x - offset - width;
  return { x1, y1: top + offset, x2: x1 + width, y2: top + offset + fontSize + 2 };
}

/**
 * Drawn inside a Recharts chart through <Customized>, which passes the lines'
 * pixel positions (formattedGraphicalItems), the plot's bounds (offset) and
 * the x axis's scale (xAxisMap). `references` are the chart's vertical
 * reference lines: { x, label, position, offset }, as given to ReferenceLine.
 * `onFit` hears whether every name found a clear spot; with `hidden` (the
 * chart showing its legend instead) the labels are placed but not drawn, so
 * they come back when there's room again.
 */
export function DirectLabels({ formattedGraphicalItems, offset, xAxisMap, index, references = [], onFit, hidden = false }) {
  const labels = placeLabels({ formattedGraphicalItems, offset, xAxisMap, index, references });
  const fits = labels.length > 0 && labels.every((label) => label.clear);
  useEffect(() => {
    onFit?.(fits);
  }, [onFit, fits]);
  if (hidden || !labels.length || (onFit && !fits)) return null;
  return (
    <g className="direct-labels" aria-hidden="true">
      {labels.map((label) => (
        <text
          key={label.key}
          x={label.align === "start" ? label.box.x1 : label.box.x2}
          y={label.box.y2 - DESCENT}
          textAnchor={label.align}
          fill={label.color}
          stroke="var(--card)"
          strokeWidth={4}
          paintOrder="stroke"
          fontSize={FONT_SIZE}
          fontWeight={600}
          fontFamily="var(--font-sans)"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {label.name}
        </text>
      ))}
    </g>
  );
}

/**
 * Each line's label: its box, which end of the text sits at the line
 * (`align`), and whether the spot is `clear`. A label with no clear spot sits
 * just above its line at the target income.
 */
function placeLabels({ formattedGraphicalItems, offset, xAxisMap, index, references }) {
  if (index < 0 || !formattedGraphicalItems?.length || !offset) return [];
  const series = formattedGraphicalItems
    .map((item) => {
      const props = item.item?.props;
      const points = item.props?.points;
      if (!props || !points?.length) return null;
      return { key: String(props.dataKey), name: props.name, color: props.stroke, points };
    })
    .filter(Boolean);
  if (!series.length) return [];

  const plot = { x1: offset.left, y1: offset.top, x2: offset.left + offset.width, y2: offset.top + offset.height };

  // What a label must stay off: each line's segments, the reference lines,
  // their names, and the labels already placed.
  const segments = [];
  const addSegment = (p, q) =>
    segments.push({ p, q, bounds: { x1: Math.min(p.x, q.x), y1: Math.min(p.y, q.y), x2: Math.max(p.x, q.x), y2: Math.max(p.y, q.y) } });
  series.forEach(({ points }) => {
    for (let i = 1; i < points.length; i++) {
      if (finite(points[i - 1]) && finite(points[i])) addSegment(points[i - 1], points[i]);
    }
  });
  const blocked = [];
  const scale = xAxisMap && Object.values(xAxisMap)[0]?.scale;
  references.forEach((reference) => {
    const x = scale?.(reference.x);
    if (!Number.isFinite(x)) return;
    addSegment({ x, y: plot.y1 }, { x, y: plot.y2 });
    if (reference.label) blocked.push(referenceLabelBox(x, plot.y1, reference));
  });

  const clear = (box) => {
    if (box.x1 < plot.x1 || box.x2 > plot.x2 || box.y1 < plot.y1 || box.y2 > plot.y2) return false;
    const padded = grow(box, CLEARANCE);
    if (blocked.some((other) => overlaps(padded, other))) return false;
    return !segments.some(({ p, q, bounds }) => overlaps(padded, grow(bounds, 0.5)) && crosses(p, q, padded));
  };

  // The income to label at; the top line is labeled first.
  const anchor = series.map((s) => s.points[index]).find(finite);
  const targetX = anchor ? anchor.x : (plot.x1 + plot.x2) / 2;
  const order = [...series].sort((a, b) => (a.points[index]?.y ?? Infinity) - (b.points[index]?.y ?? Infinity));

  // Every point of the line, with the label above or below it, starting or
  // ending there, in order of distance from the target income, above before
  // below. Not where another line runs on top of it, which would leave the
  // name ambiguous.
  const optionsFor = (s, width) => {
    const options = [];
    s.points.forEach((point, i) => {
      if (!finite(point)) return;
      if (series.some((other) => other !== s && finite(other.points[i]) && Math.abs(other.points[i].y - point.y) < 3)) return;
      const distance = Math.abs(point.x - targetX);
      for (const side of ["above", "below"]) {
        for (const align of ["start", "end"]) {
          const y1 = side === "above" ? point.y - OFFSET_Y - ASCENT - DESCENT : point.y + OFFSET_Y;
          const x1 = align === "start" ? point.x + OFFSET_X : point.x - OFFSET_X - width;
          options.push({
            cost: distance + (side === "below" ? 12 : 0) + (align === "end" ? 2 : 0),
            align,
            box: { x1, y1, x2: x1 + width, y2: y1 + ASCENT + DESCENT },
          });
        }
      }
    });
    return options.sort((a, b) => a.cost - b.cost);
  };

  return order
    .map((s) => {
      const width = textWidth(s.name);
      let choice = optionsFor(s, width).find((option) => clear(option.box));
      if (choice) {
        choice = { ...choice, clear: true };
      } else {
        const point = finite(s.points[index]) ? s.points[index] : s.points.find(finite);
        if (!point) return null;
        const y1 = point.y - OFFSET_Y - ASCENT - DESCENT;
        choice = { align: "start", clear: false, box: { x1: point.x + OFFSET_X, y1, x2: point.x + OFFSET_X + width, y2: y1 + ASCENT + DESCENT } };
      }
      blocked.push(grow(choice.box, 2));
      return { ...s, ...choice };
    })
    .filter(Boolean);
}
