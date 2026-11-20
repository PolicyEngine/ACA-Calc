// Direct labels for line charts, in place of a legend (after the story charts
// in PolicyEngine/uk-growth-with-ai): each line's name sits just above it, at
// the income where the lines are furthest apart. When no point keeps them at
// least MIN_GAP_PX apart, the chart shows its legend instead.

export const MIN_GAP_PX = 18;
const LINE_HEIGHT = 16;

/**
 * Where to label the lines `keys` of `data`: the index, between the `from` and
 * `to` shares of the points, where the closest two lines are furthest apart,
 * and whether even there they're too close to label (`crowded`). The gap is
 * converted to pixels with the y domain and the plot's height.
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
  let best = { index: -1, gap: -Infinity };
  for (let i = lo; i < hi && i < n; i++) {
    const ys = keys.map((key) => data[i]?.[key]);
    if (!ys.every(onAxis)) continue;
    const sorted = [...ys].sort((a, b) => a - b);
    let gap = Infinity;
    for (let j = 1; j < sorted.length; j++) gap = Math.min(gap, sorted[j] - sorted[j - 1]);
    if (gap > best.gap) best = { index: i, gap };
  }
  const span = yDomain[1] - yDomain[0];
  const gapPx = best.index < 0 || !(span > 0) ? 0 : (best.gap / span) * plotHeight;
  return { index: best.index, crowded: gapPx < MIN_GAP_PX };
}

/**
 * Drawn inside a Recharts chart through <Customized>, which passes the lines'
 * pixel positions (formattedGraphicalItems) and the plot's bounds (offset).
 */
export function DirectLabels({ formattedGraphicalItems, offset, index }) {
  if (index < 0 || !formattedGraphicalItems?.length || !offset) return null;
  const items = formattedGraphicalItems
    .map((item) => {
      const point = item.props?.points?.[index];
      const props = item.item?.props;
      if (!props || !point || !Number.isFinite(point.y)) return null;
      return { key: String(props.dataKey), name: props.name, color: props.stroke, x: point.x, y: point.y };
    })
    .filter(Boolean)
    .sort((a, b) => a.y - b.y);
  if (!items.length) return null;

  // Baselines 6px above each line, at least a line apart, inside the plot.
  const top = offset.top + 12;
  const bottom = offset.top + offset.height - 4;
  items.forEach((item, i) => {
    item.t = item.y - 6;
    if (i && item.t < items[i - 1].t + LINE_HEIGHT) item.t = items[i - 1].t + LINE_HEIGHT;
  });
  for (let i = items.length - 1; i >= 0; i--) {
    const limit = i === items.length - 1 ? bottom : items[i + 1].t - LINE_HEIGHT;
    if (items[i].t > limit) items[i].t = limit;
  }
  items.forEach((item) => {
    item.t = Math.max(top, item.t);
  });

  // Toward the right of the plot, the names end at the point.
  const x = items[0].x;
  const alignEnd = x > offset.left + offset.width * 0.6;
  return (
    <g className="direct-labels" aria-hidden="true">
      {items.map((item) => (
        <text
          key={item.key}
          x={alignEnd ? x - 6 : x + 6}
          y={item.t}
          textAnchor={alignEnd ? "end" : "start"}
          fill={item.color}
          stroke="var(--card)"
          strokeWidth={4}
          paintOrder="stroke"
          fontSize={12}
          fontWeight={600}
          fontFamily="var(--font-sans)"
        >
          {item.name}
        </text>
      ))}
    </g>
  );
}
