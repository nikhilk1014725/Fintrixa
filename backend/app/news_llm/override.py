"""Applies the red-flag override: caps a stock's displayed verdict at
Hold when an active red flag is present in its latest news corroboration,
regardless of the numeric score -- per .claude/skills/fintrixa-scoring-
formula's "Red-flag override" section. Never raises a label, only caps it
down."""
from app.models import NewsCorroboration, Score

CAPPED_LABEL = "Hold"
LABELS_SUBJECT_TO_CAP = {"Strong Buy", "Buy"}


def apply_red_flag_override(score: Score | None, corroboration: NewsCorroboration | None) -> dict:
    """Returns {"long_term_label": ..., "short_term_label": ...,
    "override_reason": ...} -- the EFFECTIVE labels to display. If there's
    no active red flag (no corroboration, or corroboration with an empty
    red_flags list), returns the score's own labels unchanged and
    override_reason=None."""
    long_term_label = score.long_term_label if score else None
    short_term_label = score.short_term_label if score else None

    if corroboration is None or not corroboration.red_flags:
        return {
            "long_term_label": long_term_label,
            "short_term_label": short_term_label,
            "override_reason": None,
        }

    reason = f"Active red flag(s) found: {'; '.join(corroboration.red_flags)}"
    effective_long = CAPPED_LABEL if long_term_label in LABELS_SUBJECT_TO_CAP else long_term_label
    effective_short = CAPPED_LABEL if short_term_label in LABELS_SUBJECT_TO_CAP else short_term_label

    return {
        "long_term_label": effective_long,
        "short_term_label": effective_short,
        "override_reason": reason,
    }
