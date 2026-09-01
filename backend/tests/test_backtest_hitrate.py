from app.backtest.hitrate import evaluate_window


def test_evaluate_window_discriminating_data_passes_both_conditions():
    # Scores perfectly correlated with returns -- top quartile (highest
    # scores) should clearly beat the median, bottom quartile clearly below.
    scored_returns = [(float(i), float(i) / 1000) for i in range(0, 100, 5)]  # 20 points

    result = evaluate_window(scored_returns)

    assert result["usable"] is True
    assert result["top_beats_median"] is True
    assert result["bottom_at_or_below_median"] is True


def test_evaluate_window_inverted_data_fails_top_condition():
    # Scores inversely correlated with returns -- the top-scoring quartile
    # actually has the worst returns here, so it must fail top_beats_median.
    scored_returns = [(float(i), -float(i) / 1000) for i in range(0, 100, 5)]

    result = evaluate_window(scored_returns)

    assert result["usable"] is True
    assert result["top_beats_median"] is False


def test_evaluate_window_too_few_participants_marked_unusable():
    scored_returns = [(10.0, 0.01), (20.0, 0.02), (30.0, 0.03)]  # only 3

    result = evaluate_window(scored_returns)

    assert result["usable"] is False
    assert "3" in result["reason"]


def test_evaluate_window_includes_quartile_size():
    scored_returns = [(float(i), float(i) / 1000) for i in range(0, 100, 5)]  # 20 points

    result = evaluate_window(scored_returns)

    assert result["quartile_size"] == 20 // 4
