"""Rule-based red flags.

Pure text statistics - deliberately independent of the model, so the UI can
show "why this looks fake" even when the classifier and the rules disagree.
Every rule from the Phase 3 spec section 5 is implemented with a stable code,
a human label and a severity.
"""
from __future__ import annotations

import re

_WORD_RE = re.compile(r"[A-Za-z']+")
# Non-alphanumerics become spaces so "must-buy" matches the phrase "must buy".
_NORMALISE_RE = re.compile(r"[^a-z0-9]+")

PROMOTIONAL_PHRASES = (
    "best",
    "perfect",
    "must buy",
    "life changing",
    "highly recommend",
    "five stars",
)

CONTRAST_WORDS = (
    "but",
    "however",
    "after",
    "although",
    "though",
    "despite",
    "while",
    "whereas",
    "otherwise",
    "instead",
    "yet",
)

# Thresholds (kept here so tests can assert on the documented behaviour).
MAX_WORDS_VERY_SHORT = 9
MIN_EXCLAMATIONS = 3
MIN_CAPS_WORDS = 2
MIN_PROMOTIONAL = 3
EXTREME_COMPOUND = 0.85
EXTREME_MAX_WORDS = 25


def count_meta(text: str) -> dict:
    """Shallow counters shown in the response ``meta`` block."""
    words = (text or "").split()
    caps_words = sum(1 for word in words if len(word) >= 2 and word.isupper())
    return {
        "words": len(words),
        "exclamations": (text or "").count("!"),
        "caps_words": caps_words,
    }


def _normalised(text: str) -> str:
    return _NORMALISE_RE.sub(" ", (text or "").lower()).strip()


def promotional_hits(text: str) -> list[str]:
    haystack = f" {_normalised(text)} "
    hits: list[str] = []
    for phrase in PROMOTIONAL_PHRASES:
        if phrase == "five stars" and (
            " five stars " in haystack or " five star " in haystack
        ):
            hits.append(phrase)
        elif f" {phrase} " in haystack:
            hits.append(phrase)
    return hits


def has_contrast_word(text: str) -> bool:
    haystack = f" {_normalised(text)} "
    return any(f" {word} " in haystack for word in CONTRAST_WORDS)


def _flag(code: str, label: str, severity: str) -> dict:
    return {"code": code, "label": label, "severity": severity}


def detect_flags(
    text: str,
    sentiment: dict | None = None,
    rating: int | None = None,
    meta: dict | None = None,
) -> list[dict]:
    """Return the red flags for one review, strongest severity first."""
    meta = meta or count_meta(text)
    words = int(meta["words"])
    flags: list[dict] = []

    # 1. Very short reviews carry almost no verifiable content.
    if words <= MAX_WORDS_VERY_SHORT:
        severity = "high" if words <= 3 else "medium" if words <= 6 else "low"
        flags.append(_flag("SHORT_REVIEW", "Unusually short review", severity))

    # 2. Three or more exclamation marks.
    exclamations = int(meta["exclamations"])
    if exclamations >= MIN_EXCLAMATIONS:
        flags.append(
            _flag(
                "EXCLAMATION_OVERLOAD",
                "Repeated exclamation marks",
                "high" if exclamations >= 2 * MIN_EXCLAMATIONS else "medium",
            )
        )

    # 3. Two or more words written in ALL CAPS.
    caps_words = int(meta["caps_words"])
    if caps_words >= MIN_CAPS_WORDS:
        severity = (
            "high"
            if caps_words >= 4 * MIN_CAPS_WORDS
            else "medium"
            if caps_words >= 2 * MIN_CAPS_WORDS
            else "low"
        )
        flags.append(_flag("ALL_CAPS", "Words in ALL CAPS", severity))

    # 4. Three or more promotional phrases.
    hits = promotional_hits(text)
    if len(hits) >= MIN_PROMOTIONAL:
        flags.append(
            _flag(
                "PROMOTIONAL_LANGUAGE",
                "Promotional wording (" + ", ".join(hits[:4]) + ")",
                "high" if len(hits) >= MIN_PROMOTIONAL + 1 else "medium",
            )
        )

    # 5. No concrete details: no digits anywhere and no contrast word.
    if words and not any(ch.isdigit() for ch in text) and not has_contrast_word(text):
        flags.append(
            _flag("NO_CONCRETE_DETAILS", "No digits or contrast words", "medium")
        )

    compound = float((sentiment or {}).get("compound", 0.0))
    label = (sentiment or {}).get("label", "Mixed")

    # 6. Extreme one-sided sentiment in a short text.
    if words <= EXTREME_MAX_WORDS and abs(compound) >= EXTREME_COMPOUND:
        flags.append(
            _flag(
                "EXTREME_ONE_SIDED_SENTIMENT",
                f"{'Over-the-top positive' if compound > 0 else 'One-sided negative'}"
                f" sentiment (compound {compound:.2f})",
                "high" if abs(compound) >= 0.95 else "medium",
            )
        )

    # 7. Rating vs sentiment mismatch (only when a rating was supplied).
    if rating is not None:
        try:
            rating_value = int(rating)
        except (TypeError, ValueError):
            rating_value = None
        if rating_value is not None:
            if rating_value >= 4 and label == "Negative":
                flags.append(
                    _flag(
                        "RATING_SENTIMENT_MISMATCH",
                        f"{rating_value}-star rating but the text reads negative",
                        "high" if compound <= -0.4 else "medium",
                    )
                )
            elif rating_value <= 2 and label == "Positive":
                flags.append(
                    _flag(
                        "RATING_SENTIMENT_MISMATCH",
                        f"{rating_value}-star rating but the text reads positive",
                        "high" if compound >= 0.4 else "medium",
                    )
                )

    order = {"high": 0, "medium": 1, "low": 2}
    flags.sort(key=lambda flag: order.get(flag["severity"], 3))
    return flags
