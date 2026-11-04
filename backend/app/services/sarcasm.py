"""Sarcasm flag: positive opening vs negative outcome, by rules only.

Phase 3.5 feature 2. A reviewer who starts with "Wow, best phone ever!" and
ends with "total garbage, it broke in a day" is being sarcastic. Sarcastic
reviews are *harder to read*, not automatically fake, so this module never
touches ``verdict`` or ``fake_probability`` - it only raises one extra item in
``flags`` for human review.

Two independent clues are combined into a 0-1 score:

1. **keyword contrast** - a positive-opener cue in the first sentence (capped
   at ``OPENING_MAX_WORDS`` words) together with a strong negative-outcome cue
   anywhere in the review;
2. **VADER contrast** - opening compound >= ``+VADER_CONTRAST_AT`` while the
   rest of the review is <= ``-VADER_CONTRAST_AT``.

``score = KEYWORD_WEIGHT * keyword_contrast + VADER_WEIGHT * vader_contrast``,
so a pure keyword contrast scores 0.60 and both clues together score 1.00.
Reviewers are flagged when ``score >= settings.sarcasm_threshold``.

The Hindi/Hinglish entries are plain keyword matches. The classifier itself is
English-only (see docs/ADVANCED_FEATURES.md); nothing here transmits, translates
or models Hindi.
"""
from __future__ import annotations

import re
import unicodedata

from app.config import settings
from app.services import sentiment

# --- configurable cue lists -------------------------------------------------
POSITIVE_OPENER_CUES: tuple[str, ...] = (
    "wow",
    "great",
    "amazing",
    "awesome",
    "perfect",
    "love",
    "best",
    "thanks",
    "brilliant",
    "excellent",
    "wonderful",
    "fantastic",
)

# Hinglish is included because reviewers type it, not because we support it.
# Cues must be whole words: "बहुत बढ़िय" would never match the token
# "बढ़िया" in a word-boundary test.
POSITIVE_OPENER_CUES_HINGLISH: tuple[str, ...] = (
    "बहुत पसंद आया",
    "बहुत बढ़िया",
    "बढ़िया",
    "bahut achha",
    "bahut accha",
    "badhiya",
    "mast",
    "shandaar",
)

NEGATIVE_OUTCOME_CUES: tuple[str, ...] = (
    "garbage",
    "trash",
    "junk",
    "useless",
    "waste",
    "broke",
    "broken",
    "worst",
    "refund",
    "scam",
    "stopped working",
)

NEGATIVE_OUTCOME_CUES_HINDI: tuple[str, ...] = (
    "बेकार",
    "चिथड़े",
    "तुच्छ",
)

NEGATIVE_OUTCOME_CUES_HINGLISH: tuple[str, ...] = (
    "kachra",
    "bekaar",
    "fraud",
)

# --- tuning knobs -----------------------------------------------------------
OPENING_MAX_WORDS = 8
VADER_CONTRAST_AT = 0.3
KEYWORD_WEIGHT = 0.6
VADER_WEIGHT = 0.4
HIGH_RISK_AT = 0.8

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WS_RE = re.compile(r"\s+")

SARCASM_FLAG_CODE = "SARCASM_SUSPECTED"
SARCASM_FLAG_LABEL = "Possible sarcasm: positive opening, negative outcome"


def _keep_char(char: str) -> bool:
    """Letters, digits and combining vowel signs (Devanagari matsras) survive.

    ``str.isalnum()`` is False for combining marks, so "बेकार" would be cut in
    half by a plain ``[^\\w\\s]`` filter - keeping category "M*" is what makes
    the Hindi keyword lists actually match.
    """
    return char.isalnum() or unicodedata.category(char).startswith("M")


def _normalise(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace (unicode-aware)."""
    kept = "".join(char.lower() if _keep_char(char) else " " for char in (text or ""))
    return _WS_RE.sub(" ", kept).strip()


def split_opening(review: str) -> tuple[str, str]:
    """(first sentence capped at 8 words, everything after it)."""
    text = (review or "").strip()
    if not text:
        return "", ""
    parts = _SENTENCE_SPLIT_RE.split(text, maxsplit=1)
    sentence = parts[0].strip()
    rest = parts[1].strip() if len(parts) > 1 else ""

    # Whitespace tokens, never [\\w]+: that would shred Devanagari words.
    words = sentence.split()
    if len(words) > OPENING_MAX_WORDS:
        opening = " ".join(words[:OPENING_MAX_WORDS])
        leftover = " ".join(words[OPENING_MAX_WORDS:])
        rest = f"{leftover} {rest}".strip()
    else:
        opening = sentence
    return opening, rest


def _matched_cues(text: str, cues: tuple[str, ...]) -> list[str]:
    # The padded haystack makes " cue " a word-boundary test that also matches
    # a cue at the very start or end of the review, including multiword cues.
    haystack = f" {_normalise(text)} "
    hits: list[str] = []
    for cue in cues:
        normalised_cue = _normalise(cue)
        if not normalised_cue:
            continue
        if f" {normalised_cue} " in haystack and cue not in hits:
            hits.append(cue)
    return hits


def positive_cues(opening: str) -> list[str]:
    return _matched_cues(opening, POSITIVE_OPENER_CUES + POSITIVE_OPENER_CUES_HINGLISH)


def negative_cues(review: str) -> list[str]:
    return _matched_cues(
        review, NEGATIVE_OUTCOME_CUES + NEGATIVE_OUTCOME_CUES_HINDI + NEGATIVE_OUTCOME_CUES_HINGLISH
    )


def _risk_level(score: float) -> str:
    if score >= HIGH_RISK_AT:
        return "high"
    if score >= settings.sarcasm_threshold:
        return "medium"
    return "low"


def analyze(review: str) -> dict:
    """Sarcasm block for one review (shape of the optional ``sarcasm`` field)."""
    opening, rest = split_opening(review)
    positives = positive_cues(opening)
    negatives = negative_cues(review)

    keyword_contrast = bool(positives and negatives)
    vader_contrast = False
    if rest:
        # Reuses ml.features.extract_vader, i.e. the same scores the model was
        # trained on - no second sentiment engine here.
        opening_compound = float(sentiment.analyze(opening)["compound"])
        rest_compound = float(sentiment.analyze(rest)["compound"])
        vader_contrast = (
            opening_compound >= VADER_CONTRAST_AT
            and rest_compound <= -VADER_CONTRAST_AT
        )

    score = (
        KEYWORD_WEIGHT if keyword_contrast else 0.0
    ) + (VADER_WEIGHT if vader_contrast else 0.0)
    score = round(min(score, 1.0), 4)
    suspected = score > 0.0 and score >= float(settings.sarcasm_threshold)

    if not suspected:
        # Cheap and honest: report the score, keep the payload small.
        return {"suspected": False, "score": score}

    return {
        "suspected": True,
        "score": score,
        "risk_level": _risk_level(score),
        "positive_cues": positives,
        "negative_cues": negatives,
    }


def flag_entry(result: dict) -> dict:
    """The one extra item added to the existing ``flags`` list when suspected."""
    severity = result.get("risk_level") or "medium"
    if severity not in ("low", "medium", "high"):
        severity = "medium"
    return {"code": SARCASM_FLAG_CODE, "label": SARCASM_FLAG_LABEL, "severity": severity}


def add_flag(flags: list[dict], result: dict) -> list[dict]:
    """Return a new flag list with the sarcasm flag inserted, strongest first."""
    if not result.get("suspected"):
        return list(flags)
    merged = list(flags) + [flag_entry(result)]
    order = {"high": 0, "medium": 1, "low": 2}
    merged.sort(key=lambda flag: order.get(flag.get("severity", "low"), 3))
    return merged
