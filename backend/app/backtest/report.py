"""Orchestrates the full backtest run: pulls price history from the DB,
replays the technical score at each rolling window, computes forward
returns, evaluates the release gate, and produces the pass/fail report
per .claude/skills/fintrixa-backtest-methodology's Reporting section."""
import pandas as pd
from sqlalchemy.orm import Session

from app.backtest.forward_returns import compute_forward_return
from app.backtest.hitrate import evaluate_window
from app.backtest.replay import replay_technical_score
from app.backtest.windows import generate_rolling_windows
from app.models import DailyPrice, Stock
from app.scoring.technical import MIN_HISTORY_DAYS

MIN_WINDOWS_REQUIRED = 8
RELEASE_GATE_THRESHOLD = 0.60


def _load_price_series(db: Session) -> dict[str, tuple[pd.Series, pd.Series]]:
    """Returns {ticker: (closes, volumes)}, each a pd.Series indexed by
    trade_date ascending."""
    stocks = db.query(Stock).all()
    series_by_ticker = {}
    for stock in stocks:
        rows = (
            db.query(DailyPrice)
            .filter(DailyPrice.stock_id == stock.id)
            .order_by(DailyPrice.trade_date.asc())
            .all()
        )
        if not rows:
            continue
        dates = [r.trade_date for r in rows]
        closes = pd.Series([r.close for r in rows], index=pd.Index(dates))
        volumes = pd.Series([r.volume for r in rows], index=pd.Index(dates))
        series_by_ticker[stock.ticker] = (closes, volumes)
    return series_by_ticker


def run_backtest(db: Session, horizon_trading_days: int, horizon_label: str) -> dict:
    """Runs the full release-gate backtest for one horizon (e.g. 21
    trading days ~= T+1mo, 63 ~= T+3mo). Returns a report dict with full
    window-by-window evidence -- never a bare pass/fail."""
    series_by_ticker = _load_price_series(db)
    if not series_by_ticker:
        return {
            "horizon": horizon_label,
            "status": "insufficient history",
            "reason": "no price history in DB",
        }

    master_calendar = sorted({d for closes, _ in series_by_ticker.values() for d in closes.index})
    window_dates = generate_rolling_windows(master_calendar, MIN_HISTORY_DAYS, horizon_trading_days)

    window_results = []
    for as_of in window_dates:
        scored_returns = []
        for closes, volumes in series_by_ticker.values():
            replayed = replay_technical_score(closes, volumes, as_of)
            if replayed["score"] is None:
                continue
            forward_return = compute_forward_return(closes, as_of, horizon_trading_days)
            if forward_return is None:
                continue
            scored_returns.append((replayed["score"], forward_return))

        result = evaluate_window(scored_returns)
        result["as_of"] = as_of.isoformat()
        window_results.append(result)

    usable_windows = [w for w in window_results if w["usable"]]
    if len(usable_windows) < MIN_WINDOWS_REQUIRED:
        return {
            "horizon": horizon_label,
            "status": "insufficient history",
            "usable_windows": len(usable_windows),
            "required": MIN_WINDOWS_REQUIRED,
            "windows": window_results,
        }

    top_pass_rate = sum(1 for w in usable_windows if w["top_beats_median"]) / len(usable_windows)
    bottom_pass_rate = sum(1 for w in usable_windows if w["bottom_at_or_below_median"]) / len(usable_windows)
    passed = top_pass_rate >= RELEASE_GATE_THRESHOLD and bottom_pass_rate >= RELEASE_GATE_THRESHOLD

    return {
        "horizon": horizon_label,
        "status": "pass" if passed else "fail",
        "usable_windows": len(usable_windows),
        "top_quartile_pass_rate": round(top_pass_rate, 3),
        "bottom_quartile_pass_rate": round(bottom_pass_rate, 3),
        "windows": window_results,
    }
