REQUIRED_FIELDS = [
    "trailing_pe",
    "sector_pe",
    "return_on_equity",
    "debt_to_equity",
]


def compute_fundamental_score(data: dict) -> dict:
    """Valuation, profitability, leverage, red-flags components of the
    Fundamental Score, per .claude/skills/fintrixa-scoring-formula.
    Growth and promoter-holding components need multi-year data not yet
    fetched by ingestion — added in the ingestion-breadth plan alongside
    scoring's corresponding component."""
    missing = [f for f in REQUIRED_FIELDS if data.get(f) is None]
    if missing:
        return {
            "score": None,
            "excluded_reason": f"missing required fundamental fields: {', '.join(missing)}",
        }

    # Valuation (0-20 pts): cheaper than sector scores higher
    pe_ratio = data["trailing_pe"] / data["sector_pe"]
    if pe_ratio <= 0.7:
        valuation_pts = 20.0
    elif pe_ratio <= 1.0:
        valuation_pts = 14.0
    elif pe_ratio <= 1.3:
        valuation_pts = 7.0
    else:
        valuation_pts = 2.0

    # Profitability (0-20 pts): ROE only implemented here (ROCE needs a
    # field yfinance doesn't expose — added in ingestion-breadth plan)
    roe = data["return_on_equity"]
    if roe >= 0.20:
        profitability_pts = 20.0
    elif roe >= 0.12:
        profitability_pts = 13.0
    elif roe >= 0.05:
        profitability_pts = 6.0
    else:
        profitability_pts = 0.0

    # Leverage (0-15 pts)
    de = data["debt_to_equity"]
    if de <= 0.2:
        leverage_pts = 15.0
    elif de <= 0.6:
        leverage_pts = 10.0
    elif de <= 1.2:
        leverage_pts = 5.0
    else:
        leverage_pts = 0.0

    # Red flags (0-10 pts, deduction-based)
    red_flag_pts = 10.0
    if data.get("pledged_shares_pct", 0) and data["pledged_shares_pct"] > 0.10:
        red_flag_pts -= 5.0
    if data.get("auditor_changed_recently"):
        red_flag_pts -= 3.0
    if data.get("negative_equity"):
        red_flag_pts -= 10.0
    red_flag_pts = max(red_flag_pts, 0.0)

    # Scaled to 0-100 using the 65 pts currently implemented (valuation
    # 20 + profitability 20 + leverage 15 + red-flags 10) until growth
    # (20) and promoter-holding (15) land.
    raw = valuation_pts + profitability_pts + leverage_pts + red_flag_pts
    score = round((raw / 65.0) * 100, 1)

    return {"score": score, "excluded_reason": None}
