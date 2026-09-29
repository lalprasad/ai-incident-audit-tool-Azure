import { barColor } from "../utils/format";

export function HorizontalBars({
  items,
  max,
}: {
  items: { label: string; value: number; color?: string }[];
  max?: number;
}) {
  const ceiling = max ?? Math.max(...items.map((item) => item.value), 1);
  return (
    <div>
      {items.map((item) => (
        <div className="bar-row" key={item.label}>
          <span>{item.label}</span>
          <div className="bar-track" aria-hidden="true">
            <div
              className="bar-fill"
              style={{
                width: `${Math.min(100, (item.value / ceiling) * 100)}%`,
                background: item.color ?? barColor(item.label),
              }}
            />
          </div>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function ScoreBars({ items }: { items: { score: number; count: number }[] }) {
  const max = Math.max(...items.map((item) => item.count), 1);
  if (!items.length) return <p className="muted">No scored tickets yet.</p>;
  return (
    <div className="vbars" aria-label="Score distribution">
      {items.map((item) => (
        <div className="vbar" key={item.score}>
          <span>{item.count}</span>
          <div className="stem" style={{ height: `${(item.count / max) * 100}px` }} />
          <span>{item.score}</span>
        </div>
      ))}
    </div>
  );
}

export function TrendChart({ points }: { points: { date: string; average_percentage: number }[] }) {
  if (points.length < 2) {
    return <p className="muted">A trend appears when audits have more than one open date.</p>;
  }
  const width = 320;
  const height = 110;
  const values = points.map((point) => point.average_percentage);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 100);
  const step = width / (points.length - 1);
  const coords = points.map((point, index) => {
    const x = index * step;
    const y = height - ((point.average_percentage - min) / (max - min || 1)) * (height - 12) - 6;
    return `${x},${y}`;
  });
  return (
    <svg className="trend" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Score trend by open date">
      <polyline fill="none" stroke="#0f6cbd" strokeWidth="2" points={coords.join(" ")} />
      {points.map((point, index) => (
        <text key={point.date} x={index * step} y={height} fontSize="9" fill="#5b7082">
          {point.date.slice(5)}
        </text>
      ))}
    </svg>
  );
}
