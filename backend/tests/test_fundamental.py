from app.scoring.fundamental import compute_fundamental_score


def test_strong_fundamentals_score_high():
    result = compute_fundamental_score(
        {
            "trailing_pe": 15.0,
            "sector_pe": 25.0,
            "return_on_equity": 0.22,
            "debt_to_equity": 0.1,
            "pledged_shares_pct": 0.0,
            "auditor_changed_recently": False,
            "negative_equity": False,
        }
    )
    assert result["score"] >= 60
    assert result["excluded_reason"] is None


def test_missing_required_field_excludes_not_zeroes():
    result = compute_fundamental_score(
        {
            "trailing_pe": None,
            "sector_pe": 25.0,
            "return_on_equity": 0.22,
            "debt_to_equity": 0.1,
            "pledged_shares_pct": 0.0,
            "auditor_changed_recently": False,
            "negative_equity": False,
        }
    )
    assert result["score"] is None
    assert "trailing_pe" in result["excluded_reason"]


def test_pledged_shares_deduct_red_flag_points():
    base = dict(
        trailing_pe=15.0,
        sector_pe=25.0,
        return_on_equity=0.22,
        debt_to_equity=0.1,
        pledged_shares_pct=0.0,
        auditor_changed_recently=False,
        negative_equity=False,
    )
    clean = compute_fundamental_score(base)
    pledged = compute_fundamental_score({**base, "pledged_shares_pct": 0.15})
    assert pledged["score"] < clean["score"]
