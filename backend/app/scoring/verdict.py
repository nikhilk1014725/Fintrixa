def _label(score: float) -> str:
    if score >= 80:
        return "Strong Buy"
    if score >= 60:
        return "Buy"
    if score >= 40:
        return "Hold"
    return "Avoid"


def combine_scores(fundamental_score: float | None, technical_score: float | None) -> dict:
    """Combines the two sub-scores per .claude/skills/fintrixa-scoring-formula:
    Long-Term = 70% fundamental / 30% technical, Short-Term = 70% technical
    / 30% fundamental. Missing either input excludes both verdicts rather
    than defaulting the missing one to a neutral value."""
    if fundamental_score is None or technical_score is None:
        missing = []
        if fundamental_score is None:
            missing.append("fundamental score")
        if technical_score is None:
            missing.append("technical score")
        return {
            "long_term_score": None,
            "short_term_score": None,
            "long_term_label": None,
            "short_term_label": None,
            "explanation": None,
            "excluded_reason": f"missing {' and '.join(missing)}",
        }

    long_term = round(0.7 * fundamental_score + 0.3 * technical_score, 1)
    short_term = round(0.7 * technical_score + 0.3 * fundamental_score, 1)
    long_term_label = _label(long_term)
    short_term_label = _label(short_term)

    explanation = (
        f"Long-term: {long_term_label.lower()} on fundamentals "
        f"({fundamental_score:.0f}/100) with technicals at "
        f"{technical_score:.0f}/100. Short-term: {short_term_label.lower()} "
        f"on current momentum."
    )

    return {
        "long_term_score": long_term,
        "short_term_score": short_term,
        "long_term_label": long_term_label,
        "short_term_label": short_term_label,
        "explanation": explanation,
        "excluded_reason": None,
    }
