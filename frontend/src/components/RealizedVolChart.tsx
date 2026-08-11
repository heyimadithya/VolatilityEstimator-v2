import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import type { AnalyzeResponse } from "../lib/api";

type Props = {
  data: NonNullable<AnalyzeResponse["realized"]>;
};

export function RealizedVolChart({ data }: Props) {
  const rows = data.dates.map((date, i) => ({
    date,
    rv: data.realized_vol[i],
    bv: data.bipower_vol[i],
    pk: data.parkinson_vol[i],
  }));

  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(24,32,28,0.08)" vertical={false} />
          <XAxis
            dataKey="date"
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
          />
          <Legend />
          <Line type="monotone" dataKey="rv" name="Realized" stroke="#1f6f5b" dot={false} strokeWidth={1.7} />
          <Line type="monotone" dataKey="bv" name="Bipower" stroke="#5b6e66" dot={false} strokeWidth={1.4} />
          <Line type="monotone" dataKey="pk" name="Parkinson" stroke="#b8860b" dot={false} strokeWidth={1.4} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
