"""Replays the technical score formula as of a historical date, using only
data that existed at that date (no look-ahead) -- per
.claude/skills/fintrixa-backtest-methodology."""
from datetime import date

import pandas as pd

from app.scoring.technical import compute_technical_score


def replay_technical_score(closes: pd.Series, volumes: pd.Series, as_of: date) -> dict:
    """closes/volumes must be pd.Series indexed by trade_date (ascending).
    Slices to data on or before `as_of` and calls the existing
    compute_technical_score unmodified -- this is what guarantees no
    look-ahead: the score literally cannot see data after `as_of`."""
    sliced_closes = closes[closes.index <= as_of]
    sliced_volumes = volumes[volumes.index <= as_of]
    return compute_technical_score(sliced_closes, sliced_volumes)
