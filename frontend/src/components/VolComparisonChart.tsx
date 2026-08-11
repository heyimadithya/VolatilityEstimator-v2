import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { AnalyzeResponse } from "../lib/api";

type Props = {
  data: AnalyzeResponse;
};

function formatTick(date: string) {
  return date.slice(2, 7);
}

export function VolComparisonChart({ data }: Props) {
  const garchSeries =
    data.models.garch && "series" in data.models.garch ? data.models.garch.series : [];

  const rows = data.dates.map((date, i) => ({
    date,
    rolling: data.models.rolling.series[i],
    ewma: data.models.ewma.series[i],
    garch: garchSeries[i] ?? null,
  }));

  // Downsample for readability on long histories
  const step = Math.max(1, Math.floor(rows.length / 520));
  const sampled = rows.filter((_, i) => i % step === 0 || i === rows.length - 1);

  return (
    <div className="chart-frame">
      <div className="legend">
        <span>
          <i style={{ background: "var(--chart-rolling)" }} /> Rolling σ
        </span>
        <span>
          <i style={{ background: "var(--chart-ewma)" }} /> EWMA
        </span>
        <span>
          <i style={{ background: "var(--chart-garch)" }} /> GARCH(1,1)
        </span>
      </div>
      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={sampled} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(24,32,28,0.08)" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatTick}
            minTickGap={40}
            tick={{ fill: "#3d4a43", fontSize: 11, fontFamily: "IBM Plex Mono" }}
            axisLine={{ stroke: "rgba(24,32,28,0.15)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            width={48}
            tick={{ fill: "#3d4a43", fontSize: 11, fontFamily: "IBM Plex Mono" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "#f7f8f6",
              border: "1px solid rgba(24,32,28,0.12)",
              borderRadius: 2,
              fontFamily: "IBM Plex Mono",
              fontSize: 12,
            }}
            formatter={(value) =>
              typeof value === "number" ? `${(value * 100).toFixed(2)}%` : "—"
            }
            labelFormatter={(label) => String(label)}
          />
          <Line
            type="monotone"
            dataKey="rolling"
            stroke="#5b6e66"
            dot={false}
            strokeWidth={1.4}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="ewma"
            stroke="#1f6f5b"
            dot={false}
            strokeWidth={1.6}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="garch"
            stroke="#b8860b"
            dot={false}
            strokeWidth={1.8}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
