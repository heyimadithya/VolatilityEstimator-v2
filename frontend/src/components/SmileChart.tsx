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
  smile: NonNullable<AnalyzeResponse["iv_surface"]>["smiles"][number];
};

export function SmileChart({ smile }: Props) {
  const rows = smile.moneyness.map((m, i) => ({
    m: Number(m.toFixed(3)),
    iv: smile.iv[i],
  }));

  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(24,32,28,0.08)" vertical={false} />
          <XAxis
            dataKey="m"
            tick={{ fill: "#3d4a43", fontSize: 11, fontFamily: "IBM Plex Mono" }}
            axisLine={{ stroke: "rgba(24,32,28,0.15)" }}
            tickLine={false}
            label={{
              value: "Moneyness K/S",
              position: "insideBottom",
              offset: -2,
              fill: "#3d4a43",
              fontSize: 11,
            }}
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
          />
          <Line
            type="monotone"
            dataKey="iv"
            stroke="#1f6f5b"
            strokeWidth={2}
            dot={{ r: 2.5, fill: "#b8860b", strokeWidth: 0 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
