"""Station 3 - Optimal portfolios and the walk-forward out-of-sample backtest.

Backtest rules (stated assumptions):
- estimation window: 252 rows on the panel's own trading calendar
- rebalancing: monthly, on the LAST trading day of each month
- weights use past data only: the estimation slice is ``panel[p-252:p]`` for a
  rebalance at position ``p``, so the rebalance day itself is EXCLUDED
- long-only fully invested: every weight >= 0 and weights sum to 1
- risk-free rate: 0 (stated); transaction costs: 0 (stated)
- annualisation: 252 for any fund containing equities, 365 for the
  pure-crypto fund (it trades 7 days a week on its own calendar)

Solver stability: daily-return covariances are tiny (~1e-4), which can stall
SLSQP below its tolerance. Covariance and mean inputs are therefore scaled by
COV_SCALE before optimisation (the optima are invariant to uniform scaling).
Covariances are shrunk toward a scaled-identity target with a manually
implemented Ledoit-Wolf intensity (no sklearn dependency). Every optimiser
falls back to equal weights if the solver fails to converge, and the run
script sanity-checks that weights genuinely differ across methods.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

WINDOW = 252
COV_SCALE = 1e4
ANN_EQUITY = 252
ANN_CRYPTO = 365

# Fund matrix: (asset family, method) pairs, each one investable fund.
# Full symmetry: every method across every family, so the shelf isolates
# what the METHOD changes (down a column) from what the FAMILY changes
# (across a row).
FUND_METHODS = {
    "Combined Equal-Weight": ("combined", "equal_weight"),
    "Combined Min-Variance": ("combined", "min_variance"),
    "Combined Max-Sharpe": ("combined", "max_sharpe"),
    "Combined Risk-Parity": ("combined", "risk_parity"),
    "Equity Equal-Weight": ("equity", "equal_weight"),
    "Equity Min-Variance": ("equity", "min_variance"),
    "Equity Max-Sharpe": ("equity", "max_sharpe"),
    "Equity Risk-Parity": ("equity", "risk_parity"),
    "Crypto Equal-Weight": ("crypto", "equal_weight"),
    "Crypto Min-Variance": ("crypto", "min_variance"),
    "Crypto Max-Sharpe": ("crypto", "max_sharpe"),
    "Crypto Risk-Parity": ("crypto", "risk_parity"),
}


# --------------------------------------------------------------------------
# Covariance estimation: manual Ledoit-Wolf-style shrinkage
# --------------------------------------------------------------------------

def shrink_covariance(x: np.ndarray) -> np.ndarray:
    """Sample covariance shrunk toward a scaled-identity target.

    Manual Ledoit-Wolf (2004, 'Honey, I Shrunk the Sample Covariance Matrix'),
    implemented with numpy only: target F = m*I with m = trace(S)/N, and the
    shrinkage intensity estimated as min(1, b2/d2). Shrinking stabilises the
    50-60 asset covariance estimated from only 252 observations.
    """
    t, n = x.shape
    s = (x.T @ x) / t
    m = np.trace(s) / n
    f = m * np.eye(n)
    d2 = ((s - f) ** 2).sum() / n
    row_norm2 = (x ** 2).sum(axis=1)
    term1 = (row_norm2 ** 2).sum()
    xsx = np.einsum("ti,ij,tj->", x, s, x)
    b2 = (term1 - 2.0 * xsx + t * (s ** 2).sum()) / (t ** 2 * n)
    delta = float(np.clip(b2 / d2, 0.0, 1.0)) if d2 > 0 else 1.0
    return delta * f + (1.0 - delta) * s


def _estimate(est: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Demeaned estimation matrix -> (scaled mean vector, shrunk scaled cov)."""
    x = est.to_numpy(dtype=float)
    mu = x.mean(axis=0)
    cov = shrink_covariance(x - mu)
    return mu * COV_SCALE, cov * COV_SCALE


# --------------------------------------------------------------------------
# Optimisers (all long-only, fully invested; inputs already COV_SCALE-scaled)
# --------------------------------------------------------------------------

def _clean_weights(w: np.ndarray, n: int) -> np.ndarray:
    w = np.asarray(w, dtype=float)
    if not np.all(np.isfinite(w)) or w.sum() <= 0:
        return np.full(n, 1.0 / n)
    w = np.clip(w, 0.0, None)
    return w / w.sum()


def equal_weight(n: int, mu=None, cov=None) -> np.ndarray:
    return np.full(n, 1.0 / n)


def min_variance(n: int, mu, cov) -> np.ndarray:
    res = minimize(
        lambda w: w @ cov @ w, np.full(n, 1.0 / n), method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not res.success:
        print(f"      [warn] min_variance solver stalled ({res.message}); "
              f"falling back to equal weights")
        return np.full(n, 1.0 / n)
    return _clean_weights(res.x, n)


def max_sharpe(n: int, mu, cov) -> np.ndarray:
    if not np.any(mu > 0):  # no positive expected return: tangency degenerate
        print("      [warn] max_sharpe: no positive mean returns in window; "
              "falling back to min-variance weights")
        return min_variance(n, mu, cov)

    # Convex QP reformulation of the long-only tangency portfolio (rf = 0):
    #   min y'Cov y  s.t.  mu'y = 1, y >= 0,  then  w = y / sum(y).
    # Solving the raw Sharpe ratio directly makes SLSQP stall on the
    # non-concave objective (observed: 'Positive directional derivative for
    # linesearch' on every window); the QP is convex and solves reliably.
    y0 = np.zeros(n)
    j = int(np.argmax(mu))
    y0[j] = 1.0 / mu[j]  # feasible start: mu'y0 = 1, y0 >= 0
    res = minimize(
        lambda y: y @ cov @ y, y0, method="SLSQP",
        bounds=[(0.0, None)] * n,
        constraints=[{"type": "eq", "fun": lambda y: y @ mu - 1.0}],
        options={"maxiter": 500, "ftol": 1e-14},
    )
    if not res.success or not np.all(np.isfinite(res.x)) or res.x.sum() <= 0:
        print(f"      [warn] max_sharpe QP stalled ({res.message}); "
              f"falling back to min-variance weights")
        return min_variance(n, mu, cov)
    return _clean_weights(res.x / res.x.sum(), n)


def risk_parity(n: int, mu, cov) -> np.ndarray:
    def objective(w):
        port_var = max(w @ cov @ w, 1e-18)
        rc = w * (cov @ w) / port_var  # risk contributions, sum to 1
        return ((rc - 1.0 / n) ** 2).sum()

    res = minimize(
        objective, np.full(n, 1.0 / n), method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 500, "ftol": 1e-14},
    )
    if not res.success:
        print(f"      [warn] risk_parity solver stalled ({res.message}); "
              f"falling back to equal weights")
        return np.full(n, 1.0 / n)
    return _clean_weights(res.x, n)


OPTIMISERS = {
    "equal_weight": equal_weight,
    "min_variance": min_variance,
    "max_sharpe": max_sharpe,
    "risk_parity": risk_parity,
}


# --------------------------------------------------------------------------
# Walk-forward backtest
# --------------------------------------------------------------------------

def month_end_rebalance_dates(
    index: pd.DatetimeIndex, window: int = WINDOW
) -> pd.DatetimeIndex:
    """Last trading day of each month whose position allows a full window."""
    s = pd.Series(index, index=index)
    month_ends = pd.DatetimeIndex(s.groupby([index.year, index.month]).max())
    return month_ends[month_ends.map(index.get_loc) >= window]


def compute_rebalance_weights(
    panel: pd.DataFrame, method: str, window: int = WINDOW
) -> pd.DataFrame:
    """Wide weight table (rebalance date x ticker) from a walk-forward loop.

    For a rebalance at position p the estimation slice is panel[p-window:p],
    which EXCLUDES the rebalance day itself - weights use past data only.
    Assets with incomplete data inside a window receive zero weight that round.
    """
    optimiser = OPTIMISERS[method]
    index = panel.index
    rebal_dates = month_end_rebalance_dates(index, window)
    weights = {}
    for d in rebal_dates:
        p = index.get_loc(d)
        est = panel.iloc[p - window:p]  # rebalance day itself excluded
        usable = est.columns[est.notna().all(axis=0)]
        n = len(panel.columns)
        w = np.zeros(n)
        if len(usable) > 0:
            mu, cov = _estimate(est[usable])
            w[panel.columns.get_indexer(usable)] = optimiser(len(usable), mu, cov)
        weights[d] = w
    wdf = pd.DataFrame(weights).T
    wdf.index.name = "date"
    wdf.columns = panel.columns
    return wdf


def portfolio_returns(panel: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    """Daily out-of-sample portfolio returns from a rebalance-weight table.

    Weights set at rebalance date d earn returns from the NEXT trading day
    onward (day d itself belongs to the previous weights), so each day t uses
    the most recent rebalance strictly before t. The OOS series starts the day
    after the first rebalance - at least `window` days into the sample.
    """
    panel = panel.fillna(0.0)
    rebal_pos = panel.index.get_indexer(weights.index)
    day_pos = np.arange(len(panel.index))
    # for each day, position of the latest rebalance strictly before it
    owner = np.searchsorted(rebal_pos, day_pos, side="left") - 1
    live = owner >= 0
    w_daily = weights.to_numpy()[owner[live]]
    rets = (w_daily * panel.to_numpy()[live]).sum(axis=1)
    out = pd.Series(rets, index=panel.index[live], name="return")
    out.index.name = "date"
    return out


def backtest_fund(
    panel: pd.DataFrame, method: str, window: int = WINDOW
) -> tuple[pd.Series, pd.DataFrame]:
    """One fund: (daily OOS returns, wide rebalance-weight table)."""
    weights = compute_rebalance_weights(panel, method, window)
    returns = portfolio_returns(panel, weights)
    return returns, weights


def backtest_all(
    panels: dict[str, pd.DataFrame], window: int = WINDOW
) -> dict[str, dict]:
    """Run the full fund matrix. panels keys: combined / equity / crypto."""
    funds = {}
    for name, (family, method) in FUND_METHODS.items():
        rets, weights = backtest_fund(panels[family], method, window)
        funds[name] = {"returns": rets, "weights": weights, "family": family}
        print(f"      {name}: OOS {rets.index.min().date()} -> "
              f"{rets.index.max().date()} ({len(rets)} days, "
              f"{len(weights)} rebalances)")
    return funds


# --------------------------------------------------------------------------
# Performance metrics
# --------------------------------------------------------------------------

def annualisation_for(family: str) -> int:
    """252 for any fund containing equities; 365 only for pure crypto."""
    return ANN_CRYPTO if family == "crypto" else ANN_EQUITY


def max_drawdown(returns: pd.Series) -> float:
    wealth = (1.0 + returns).cumprod()
    dd = wealth / wealth.cummax() - 1.0
    return float(dd.min())


def performance_metrics(returns: pd.Series, periods_per_year: int) -> dict:
    """Annualised return/vol/Sharpe (rf = 0, stated), max drawdown, n_days."""
    p = periods_per_year
    n = len(returns)
    wealth = (1.0 + returns).cumprod()
    ann_return = float(wealth.iloc[-1] ** (p / n) - 1.0)
    ann_vol = float(returns.std(ddof=1) * np.sqrt(p))
    sharpe = float(returns.mean() / returns.std(ddof=1) * np.sqrt(p))
    return {
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown(returns),
        "n_days": int(n),
    }


def weights_sanity_check(funds: dict[str, dict]) -> pd.DataFrame:
    """Prove the solver did not stall: weights must differ across methods.

    Returns the mean absolute weight difference between each pair of funds
    built on the same asset panel (NaN when a pair shares no rebalance dates).
    """
    rows = []
    names = list(funds)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if funds[a]["family"] != funds[b]["family"]:
                continue
            wa, wb = funds[a]["weights"], funds[b]["weights"]
            common = wa.index.intersection(wb.index)
            diff = (wa.loc[common] - wb.loc[common]).abs().to_numpy().mean()
            rows.append({"fund_a": a, "fund_b": b,
                         "mean_abs_weight_diff": float(diff)})
    return pd.DataFrame(rows)
