export type AnalyzeResponse = {
  ticker: string;
  spot: number;
  asof: string;
  dates: string[];
  closes: number[];
  returns: number[];
  models: {
    sample: { volatility: number; n_returns: number };
    rolling: { window: number; series: (number | null)[]; latest: number | null };
    ewma: { lambda: number; series: (number | null)[]; latest: number | null };
    garch:
      | {
          params: {
            omega: number;
            alpha: number;
            beta: number;
            persistence: number;
            unconditional_vol: number | null;
            log_likelihood: number;
            converged: boolean;
            message: string;
          };
          series: (number | null)[];
          latest: number | null;
          forecast: { horizon_days: number[]; volatility: (number | null)[] };
        }
      | { error: string };
  };
  realized: {
    dates: string[];
    realized_vol: number[];
    bipower_vol: number[];
    parkinson_vol: number[];
    average_rv: number;
    n_days: number;
    bars_per_day_median: number;
    note: string;
  } | null;
  iv_surface: {
    spot: number;
    smiles: {
      expiry: string;
      t_years: number;
      strikes: number[];
      moneyness: number[];
      iv: number[];
    }[];
    points: { expiry: string; t_years: number; strike: number; moneyness: number; iv: number }[];
    grid: {
      moneyness: number[];
      maturities: number[];
      iv: (number | null)[][];
    };
    n_points: number;
    method: string;
  } | null;
  notes: string[];
};

function demoUrl(): string {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}demo-spy.json`;
}

async function loadDemo(): Promise<AnalyzeResponse> {
  const res = await fetch(demoUrl());
  if (!res.ok) {
    throw new Error("Demo dataset missing. Run the API locally for live estimates.");
  }
  const data = (await res.json()) as AnalyzeResponse;
  data.notes = [
    ...(data.notes ?? []),
    "GitHub Pages hosts the static UI only (no Python API). Showing a cached SPY demo. Clone the repo and run the FastAPI backend for live tickers.",
  ];
  return data;
}

export async function analyzeTicker(payload: {
  ticker: string;
  period: string;
  rolling_window: number;
  ewma_lambda: number;
  include_realized: boolean;
  include_iv: boolean;
  risk_free_rate: number;
}): Promise<AnalyzeResponse> {
  // Optional override for a hosted API; empty on GitHub Pages.
  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

  try {
    const res = await fetch(`${apiBase}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail ?? JSON.stringify(body);
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return res.json();
  } catch {
    // Pages / offline: fall back to bundled SPY demo so the site still demos charts.
    return loadDemo();
  }
}

export function pct(x: number | null | undefined, digits = 1): string {
  if (x == null || Number.isNaN(x)) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

export function num(x: number | null | undefined, digits = 4): string {
  if (x == null || Number.isNaN(x)) return "—";
  return x.toFixed(digits);
}
