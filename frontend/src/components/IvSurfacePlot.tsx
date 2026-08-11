import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-dist-min";
import type { AnalyzeResponse } from "../lib/api";

const Plot = createPlotlyComponent(Plotly);

type Props = {
  data: NonNullable<AnalyzeResponse["iv_surface"]>;
};

export function IvSurfacePlot({ data }: Props) {
  const z = data.grid.iv.map((row) =>
    row.map((v) => (v == null ? null : Number((v * 100).toFixed(3)))),
  );

  return (
    <div className="chart-frame">
      <Plot
        data={[
          {
            type: "heatmap",
            x: data.grid.moneyness.map((m) => Number(m.toFixed(3))),
            y: data.grid.maturities.map((t) => Number(t.toFixed(3))),
            z,
            colorscale: [
              [0, "#eef1ed"],
              [0.35, "#7fa896"],
              [0.7, "#1f6f5b"],
              [1, "#b8860b"],
            ],
            hovertemplate:
              "K/S=%{x}<br>T=%{y}y<br>IV=%{z:.2f}%<extra></extra>",
            colorbar: {
              title: { text: "IV %", font: { family: "IBM Plex Mono", size: 11 } },
              tickfont: { family: "IBM Plex Mono", size: 10 },
            },
          },
        ]}
        layout={{
          autosize: true,
          height: 380,
          margin: { l: 55, r: 20, t: 12, b: 50 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(255,255,255,0.35)",
          xaxis: {
            title: { text: "Moneyness K/S", font: { size: 12 } },
            tickfont: { family: "IBM Plex Mono", size: 10 },
            gridcolor: "rgba(24,32,28,0.06)",
          },
          yaxis: {
            title: { text: "Maturity (years)", font: { size: 12 } },
            tickfont: { family: "IBM Plex Mono", size: 10 },
            gridcolor: "rgba(24,32,28,0.06)",
          },
          font: { family: "Schibsted Grotesk, sans-serif", color: "#18201c" },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
        useResizeHandler
      />
      <p className="metric hint" style={{ marginTop: "0.75rem" }}>
        {data.method} · {data.n_points} quotes inverted · heat map of the σ(K, T) surface
      </p>
    </div>
  );
}
