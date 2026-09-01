"""Quartile-buckets a single window's (score, forward_return) pairs and
checks the release-gate conditions for that window, per
.claude/skills/fintrixa-backtest-methodology."""
import statistics


def evaluate_window(scored_returns: list[tuple[float, float]]) -> dict:
    """scored_returns: list of (technical_score, forward_return) for every
    stock that had enough history/forward-room to participate in this
    window. Requires at least 4 participants (so each quartile has >=1
    stock) -- fewer than that, the window is flagged unusable rather than
    computing a meaningless stat on too few points."""
    n = len(scored_returns)
    if n < 4:
        return {"usable": False, "reason": f"only {n} stocks had data this window, need >=4"}

    ranked = sorted(scored_returns, key=lambda pair: pair[0])
    quartile_size = n // 4
    bottom_quartile = ranked[:quartile_size]
    top_quartile = ranked[-quartile_size:]

    universe_returns = [r for _, r in scored_returns]
    median_return = statistics.median(universe_returns)

    top_mean = statistics.mean(r for _, r in top_quartile)
    bottom_mean = statistics.mean(r for _, r in bottom_quartile)

    return {
        "usable": True,
        "n_participants": n,
        "median_return": median_return,
        "top_quartile_mean": top_mean,
        "bottom_quartile_mean": bottom_mean,
        "top_beats_median": top_mean > median_return,
        "bottom_at_or_below_median": bottom_mean <= median_return,
    }
