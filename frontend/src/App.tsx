import { useMemo, useState, type FormEvent, lazy, Suspense } from "react";
import { analyzeTicker, pct, num, type AnalyzeResponse } from "./lib/api";
import { VolComparisonChart } from "./components/VolComparisonChart";
import { RealizedVolChart } from "./components/RealizedVolChart";
import { SmileChart } from "./components/SmileChart";

const IvSurfacePlot = lazy(() =>
  import("./components/IvSurfacePlot").then((m) => ({ default: m.IvSurfacePlot })),
);

const PERIODS = [
  { value: "1y", label: "1Y" },
  { value: "2y", label: "2Y" },
  { value: "5y", label: "5Y" },
  { value: "10y", label: "10Y" },
];

export default function App() {
  const [ticker, setTicker] = useState("SPY");
  const [period, setPeriod] = useState("5y");
  const [window, setWindow] = useState(21);
  const [lam, setLam] = useState(0.94);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [smileIdx, setSmileIdx] = useState(0);

  const garch = data?.models.garch && "params" in data.models.garch ? data.models.garch : null;

  const selectedSmile = useMemo(() => {
    if (!data?.iv_surface?.smiles.length) return null;
    return data.iv_surface.smiles[Math.min(smileIdx, data.iv_surface.smiles.length - 1)];
  }, [data, smileIdx]);

  async function onAnalyze(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeTicker({
        ticker: ticker.trim().toUpperCase(),
        period,
        rolling_window: window,
        ewma_lambda: lam,
        include_realized: true,
        include_iv: true,
        risk_free_rate: 0.045,
      });
      setData(result);
      setSmileIdx(0);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <div className="brand-mark">
          <svg width="18" height="18" viewBox="0 0 32 32" aria-hidden>
            <rect width="32" height="32" fill="#18201c" />
            <path
              d="M4 22 L10 14 L16 18 L22 8 L28 12"
              stroke="#c4a35a"
              strokeWidth="2.4"
              fill="none"
            />
          </svg>
          Volatility Estimator
        </div>
        <h1>Measure how markets move.</h1>
        <p className="lede">
          From-scratch rolling, EWMA, and GARCH(1,1) MLE on daily returns — plus
          intraday realized volatility and a Black–Scholes implied-vol surface
          inverted with Newton–Raphson.
        </p>

        <form className="controls" onSubmit={onAnalyze}>
          <div className="field">
            <label htmlFor="ticker">Ticker</label>
            <input
              id="ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="SPY"
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="field">
            <label htmlFor="period">History</label>
            <select id="period" value={period} onChange={(e) => setPeriod(e.target.value)}>
              {PERIODS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="window">Rolling window</label>
            <input
              id="window"
              type="number"
              min={5}
              max={120}
              value={window}
              onChange={(e) => setWindow(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="lam">EWMA λ</label>
            <input
              id="lam"
              type="number"
              min={0.8}
              max={0.99}
              step={0.01}
              value={lam}
              onChange={(e) => setLam(Number(e.target.value))}
            />
          </div>
          <button className="btn" type="submit" disabled={loading || !ticker.trim()}>
            {loading ? "Estimating…" : "Estimate"}
          </button>
        </form>
        <div className={`status-line${error ? " error" : ""}`}>
          {error
            ? error
            : loading
              ? "Fitting models and fetching options / 1-minute bars…"
              : data
                ? `${data.ticker} · spot ${data.spot.toFixed(2)} · ${data.asof.slice(0, 19)}Z`
                : "Ready — try SPY, QQQ, AAPL, or TSLA."}
        </div>
      </header>

      {data && (
        <>
          <section className="section">
            <div className="section-head">
              <h2>Conditional volatility</h2>
              <span>annualized · √252</span>
            </div>
            <div className="metric-row">
              <div className="metric">
                <div className="label">Sample σ</div>
                <div className="value">{pct(data.models.sample.volatility)}</div>
                <div className="hint">{data.models.sample.n_returns} returns</div>
              </div>
              <div className="metric">
                <div className="label">Rolling</div>
                <div className="value">{pct(data.models.rolling.latest)}</div>
                <div className="hint">{data.models.rolling.window}d window</div>
              </div>
              <div className="metric">
                <div className="label">EWMA</div>
                <div className="value">{pct(data.models.ewma.latest)}</div>
                <div className="hint">λ = {data.models.ewma.lambda}</div>
              </div>
              <div className="metric">
                <div className="label">GARCH(1,1)</div>
                <div className="value">{pct(garch?.latest ?? null)}</div>
                <div className="hint">
                  {garch ? `α+β = ${num(garch.params.persistence, 3)}` : "fit failed"}
                </div>
              </div>
            </div>
            <VolComparisonChart data={data} />
          </section>

          {garch && (
            <section className="section">
              <div className="section-head">
                <h2>GARCH(1,1) MLE</h2>
                <span>{garch.params.converged ? "converged" : "check diagnostics"}</span>
              </div>
              <dl className="params">
                <div>
                  <dt>ω</dt>
                  <dd>{num(garch.params.omega, 8)}</dd>
                </div>
                <div>
                  <dt>α (ARCH)</dt>
                  <dd>{num(garch.params.alpha, 4)}</dd>
                </div>
                <div>
                  <dt>β (GARCH)</dt>
                  <dd>{num(garch.params.beta, 4)}</dd>
                </div>
                <div>
                  <dt>Persistence α+β</dt>
                  <dd>{num(garch.params.persistence, 4)}</dd>
                </div>
                <div>
                  <dt>Unconditional σ</dt>
                  <dd>{pct(garch.params.unconditional_vol)}</dd>
                </div>
                <div>
                  <dt>Log-likelihood</dt>
                  <dd>{num(garch.params.log_likelihood, 2)}</dd>
                </div>
              </dl>
              {garch.forecast && (
                <div className="chart-frame" style={{ marginTop: "1.25rem" }}>
                  <div className="legend">
                    <span>Forward conditional volatility (trading days)</span>
                  </div>
                  <pre
                    style={{
                      margin: 0,
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.82rem",
                      lineHeight: 1.7,
                      color: "var(--ink-soft)",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {garch.forecast.horizon_days
                      .map(
                        (d, i) =>
                          `t+${String(d).padStart(2, " ")}  ${pct(garch.forecast.volatility[i], 2)}`,
                      )
                      .join("\n")}
                  </pre>
                </div>
              )}
            </section>
          )}

          {data.realized && (
            <section className="section">
              <div className="section-head">
                <h2>Intraday realized volatility</h2>
                <span>
                  {data.realized.n_days} sessions · ~
                  {Math.round(data.realized.bars_per_day_median)} bars/day
                </span>
              </div>
              <div className="metric-row" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
                <div className="metric">
                  <div className="label">Avg realized σ</div>
                  <div className="value">{pct(data.realized.average_rv)}</div>
                  <div className="hint">Σ r² annualized</div>
                </div>
                <div className="metric">
                  <div className="label">Latest RV</div>
                  <div className="value">
                    {pct(data.realized.realized_vol[data.realized.realized_vol.length - 1])}
                  </div>
                  <div className="hint">{data.realized.dates.at(-1)}</div>
                </div>
                <div className="metric">
                  <div className="label">Latest bipower</div>
                  <div className="value">
                    {pct(data.realized.bipower_vol[data.realized.bipower_vol.length - 1])}
                  </div>
                  <div className="hint">jump-robust</div>
                </div>
              </div>
              <RealizedVolChart data={data.realized} />
              <p className="metric hint" style={{ marginTop: "0.75rem" }}>
                {data.realized.note}
              </p>
            </section>
          )}

          {data.iv_surface && (
            <section className="section">
              <div className="section-head">
                <h2>Implied volatility surface</h2>
                <span>Black–Scholes · Newton–Raphson</span>
              </div>
              <Suspense
                fallback={
                  <p className="metric hint" style={{ marginTop: "1rem" }}>
                    Loading surface renderer…
                  </p>
                }
              >
                <IvSurfacePlot data={data.iv_surface} />
              </Suspense>
              {selectedSmile && (
                <>
                  <div className="field" style={{ maxWidth: 280, marginTop: "1.25rem" }}>
                    <label htmlFor="expiry">Smile expiry</label>
                    <select
                      id="expiry"
                      value={smileIdx}
                      onChange={(e) => setSmileIdx(Number(e.target.value))}
                    >
                      {data.iv_surface.smiles.map((s, i) => (
                        <option key={s.expiry} value={i}>
                          {s.expiry} · {s.t_years.toFixed(2)}y
                        </option>
                      ))}
                    </select>
                  </div>
                  <SmileChart smile={selectedSmile} />
                </>
              )}
            </section>
          )}

          {data.notes.length > 0 && (
            <section className="section">
              <div className="section-head">
                <h2>Notes</h2>
                <span>data caveats</span>
              </div>
              <ul className="notes">
                {data.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <footer className="footer">
        <span>Volatility Estimatorv2 - Created by Adithya Kannan · estimators in NumPy/SciPy — no arch/arch-python wrappers.</span>
        <span>Market data via Yahoo Finance.</span>
      </footer>
    </div>
  );
}
