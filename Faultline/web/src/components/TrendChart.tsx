import type { TrendPoint } from "@/lib/server-api";

/**
 * Safety over time, as a hand-drawn SVG rather than a charting dependency.
 *
 * The y-axis is the failure rate inverted, so up is safer - the direction people
 * expect from a chart labelled "safer". Points where the pinned test set changed are
 * marked, because a grade move across that line measures the questions changing, not
 * the bot, and reading it as a regression would be wrong.
 */

const WIDTH = 640;
const HEIGHT = 140;
const PAD = { top: 12, right: 12, bottom: 22, left: 12 };

export function TrendChart({ points }: { points: TrendPoint[] }) {
  if (points.length < 2) return null;

  const inner = {
    w: WIDTH - PAD.left - PAD.right,
    h: HEIGHT - PAD.top - PAD.bottom,
  };

  const x = (i: number) => PAD.left + (i / (points.length - 1)) * inner.w;
  // Inverted: a zero failure rate sits at the top.
  const y = (rate: number) => PAD.top + Math.min(1, Math.max(0, rate)) * inner.h;

  const line = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.failureRate)}`).join(" ");
  const area = `${line} L ${x(points.length - 1)} ${PAD.top + inner.h} L ${x(0)} ${
    PAD.top + inner.h
  } Z`;

  const versionChanges = points
    .map((p, i) => ({ i, changed: i > 0 && p.testSetVersion !== points[i - 1].testSetVersion }))
    .filter((v) => v.changed && points[v.i].testSetVersion);

  const first = points[0];
  const last = points[points.length - 1];

  return (
    <figure className="space-y-3">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        role="img"
        aria-label={`Failure rate across ${points.length} runs, from ${Math.round(
          first.failureRate * 100,
        )}% to ${Math.round(last.failureRate * 100)}%`}
      >
        <line
          x1={PAD.left}
          x2={WIDTH - PAD.right}
          y1={PAD.top}
          y2={PAD.top}
          stroke="var(--rule)"
          strokeDasharray="2 4"
        />
        <line
          x1={PAD.left}
          x2={WIDTH - PAD.right}
          y1={PAD.top + inner.h}
          y2={PAD.top + inner.h}
          stroke="var(--rule)"
        />

        <path d={area} fill="var(--amber-wash)" opacity="0.35" />
        <path d={line} fill="none" stroke="var(--amber)" strokeWidth="1.75" />

        {versionChanges.map(({ i }) => (
          <line
            key={i}
            x1={x(i)}
            x2={x(i)}
            y1={PAD.top}
            y2={PAD.top + inner.h}
            stroke="var(--ink-faint)"
            strokeDasharray="3 3"
          />
        ))}

        {points.map((p, i) => (
          <circle
            key={p.runId}
            cx={x(i)}
            cy={y(p.failureRate)}
            r={i === points.length - 1 ? 4 : 2.5}
            fill="var(--paper)"
            stroke="var(--amber)"
            strokeWidth="1.75"
          />
        ))}

        <text x={PAD.left} y={HEIGHT - 6} className="fill-[var(--ink-faint)]" fontSize="10">
          oldest
        </text>
        <text
          x={WIDTH - PAD.right}
          y={HEIGHT - 6}
          textAnchor="end"
          className="fill-[var(--ink-faint)]"
          fontSize="10"
        >
          latest
        </text>
      </svg>

      <figcaption className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-faint">
        <span>Higher on the chart is safer.</span>
        {versionChanges.length > 0 && (
          <span>
            Dashed line marks where the test set changed — grades either side
            aren&rsquo;t comparable.
          </span>
        )}
      </figcaption>
    </figure>
  );
}
