"""VADER sentiment for display purposes.

Scores come from ``ml.features.extract_vader`` so the numbers shown in the UI
are byte-for-byte the values the pipeline trained on - the API does not create
its own analyzer or re-do the math.
"""
from __future__ import annotations

from ml.features import extract_vader

# Label thresholds fixed by the Phase 3 spec.
POSITIVE_AT = 0.2
NEGATIVE_AT = -0.2

# extract_vader column order (see ml.config.VADER_FEATURE_NAMES).
_IDX_NEG, _IDX_NEU, _IDX_POS, _IDX_COMPOUND = 0, 1, 2, 3


def label_for(compound: float) -> str:
    if compound >= POSITIVE_AT:
        return "Positive"
    if compound <= NEGATIVE_AT:
        return "Negative"
    return "Mixed"


def _round(value: float) -> float:
    return round(float(value), 4)


def analyze(text: str) -> dict:
    """Sentiment block for one review: compound/label/pos/neu/neg."""
    return analyze_many([text])[0]


def analyze_many(texts: list[str]) -> list[dict]:
    """Vectorised VADER scores for many reviews (used by batch analysis)."""
    if not texts:
        return []
    matrix = extract_vader(texts)
    blocks: list[dict] = []
    for row in matrix:
        compound = _round(row[_IDX_COMPOUND])
        blocks.append(
            {
                "compound": compound,
                "label": label_for(compound),
                "pos": _round(row[_IDX_POS]),
                "neu": _round(row[_IDX_NEU]),
                "neg": _round(row[_IDX_NEG]),
            }
        )
    return blocks
