"""Phase 3.5 feature 2: the SARCASM_SUSPECTED risk flag.

The rule is a contrast test, not a classifier: a positive opening followed by a
negative outcome. These tests pin the scoring, prove that the verdict and the
fake probability are untouched by the flag, and check the Hindi/Hinglish keyword
lists (plain substring matching - the model itself is English-only).
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.services import sarcasm

SARCASTIC = "Wow, best phone ever, total garbage, the screen broke in a day"
PLAIN_POSITIVE = (
    "The hotel was great and the staff were wonderful; we loved the pool and "
    "the breakfast spread was generous every single morning."
)
PLAIN_NEGATIVE = (
    "The room was dirty, the wifi failed twice and the desk refused a refund "
    "for the last night we could not use."
)
HINDI_SARCASTIC = (
    "बहुत बढ़िया प्रोडक्ट था, लेकिन दो दिन में पूरी बेकार और चिथड़े हो गया।"
)
KEYWORD_ONLY = "Wow amazing laptop, absolutely useless, it stopped working on day one"

PHASE3_KEYS = {
    "id",
    "verdict",
    "fake_probability",
    "confidence",
    "model_used",
    "sentiment",
    "flags",
    "tokens",
    "meta",
    "latency_ms",
    "created_at",
    "token_map",
}


def predict(client, review: str) -> dict:
    response = client.post("/api/predict", json={"review": review})
    assert response.status_code == 200, response.text
    return response.json()


def sarcasm_flags(body: dict) -> list[dict]:
    return [flag for flag in body["flags"] if flag["code"] == "SARCASM_SUSPECTED"]


# ------------------------------------------------------------------- happy ---
def test_sarcastic_review_is_flagged(advanced_client):
    body = predict(advanced_client, SARCASTIC)
    assert body["sarcasm"]["suspected"] is True
    assert body["sarcasm"]["score"] >= settings.sarcasm_threshold
    assert body["sarcasm"]["risk_level"] in ("medium", "high")
    assert "wow" in body["sarcasm"]["positive_cues"]
    assert "garbage" in body["sarcasm"]["negative_cues"]
    assert "broke" in body["sarcasm"]["negative_cues"]

    flags = sarcasm_flags(body)
    assert len(flags) == 1
    assert flags[0]["label"] == "Possible sarcasm: positive opening, negative outcome"
    assert flags[0]["severity"] in ("low", "medium", "high")


def test_keyword_only_contrast_scores_lower_than_full_contrast(advanced_client):
    body = predict(advanced_client, KEYWORD_ONLY)
    assert body["sarcasm"]["suspected"] is True
    assert body["sarcasm"]["score"] < 1.0
    assert body["sarcasm"]["risk_level"] == "medium"


NOT_FLAGGED = [
    PLAIN_POSITIVE,
    PLAIN_NEGATIVE,
    "Nice",
    "It is a Tuesday.",
    "The room had two beds, a desk and a window facing the car park.",
]


@pytest.mark.parametrize("review", NOT_FLAGGED)
def test_ordinary_reviews_are_not_flagged(advanced_client, review):
    body = predict(advanced_client, review)
    # The block is always there while the feature is on, even when clean.
    assert "sarcasm" in body
    assert body["sarcasm"]["suspected"] is False
    assert body["sarcasm"]["score"] == 0.0
    assert sarcasm_flags(body) == []


def test_clean_review_block_is_minimal(advanced_client):
    body = predict(advanced_client, PLAIN_POSITIVE)
    assert set(body["sarcasm"]) == {"suspected", "score"}


# ------------------------------------------------- does not touch verdict ---
def test_flag_never_changes_verdict_or_probability(advanced_client, monkeypatch):
    with_sarcasm = predict(advanced_client, SARCASTIC)
    monkeypatch.setattr(settings, "enable_sarcasm", False)
    without = predict(advanced_client, SARCASTIC)

    assert with_sarcasm["verdict"] == without["verdict"]
    assert with_sarcasm["fake_probability"] == without["fake_probability"]
    assert with_sarcasm["confidence"] == without["confidence"]
    assert with_sarcasm["model_used"] == without["model_used"]
    assert with_sarcasm["sentiment"] == without["sentiment"]
    # ... the only difference is the extra review-risk flag and the new block.
    assert "sarcasm" not in without
    assert sarcasm_flags(without) == []
    assert len(with_sarcasm["flags"]) == len(without["flags"]) + 1


def test_sarcastic_customer_is_not_declared_a_spam_rule(advanced_client):
    """A sarcastic-but-genuine-sounding review keeps the model's own verdict."""
    body = predict(advanced_client, SARCASTIC)
    assert body["decision_source"] == "model"
    assert body["model_used"] in ("nb", "svm")
    assert body["tokens"], "the model explanation is still produced"
    assert 0.0 <= body["fake_probability"] <= 1.0


# ------------------------------------------------------------ multilingual --
def test_hindi_keyword_contrast_is_flagged(advanced_client):
    body = predict(advanced_client, HINDI_SARCASTIC)
    assert body["sarcasm"]["suspected"] is True
    assert "बहुत बढ़िया" in body["sarcasm"]["positive_cues"]
    assert "बेकार" in body["sarcasm"]["negative_cues"]
    # Keyword-only contrast: VADER has no Devanagari lexicon, so no +0.4 bonus.
    assert body["sarcasm"]["score"] < 1.0


# ------------------------------------------------------------ thresholds ---
def test_threshold_is_configurable(advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "sarcasm_threshold", 0.9)
    body = predict(advanced_client, KEYWORD_ONLY)
    assert body["sarcasm"]["suspected"] is False
    assert body["sarcasm"]["score"] == pytest.approx(0.6)
    assert sarcasm_flags(body) == []

    monkeypatch.setattr(settings, "sarcasm_threshold", 0.2)
    body = predict(advanced_client, KEYWORD_ONLY)
    assert body["sarcasm"]["suspected"] is True


def test_disabled_features_remove_their_keys_entirely(
    advanced_client, monkeypatch
):
    monkeypatch.setattr(settings, "enable_sarcasm", False)
    monkeypatch.setattr(settings, "enable_tier1", False)
    body = predict(advanced_client, SARCASTIC)
    assert "sarcasm" not in body
    assert "tier1" not in body
    assert "decision_source" not in body
    assert set(body) == PHASE3_KEYS
    assert sarcasm_flags(body) == []
    assert body["model_used"] in ("nb", "svm")


# ------------------------------------------------------------- unit level ---
def test_split_opening_caps_at_eight_words():
    text = "one two three four five six seven eight nine ten"
    opening, rest = sarcasm.split_opening(text)
    assert len(opening.split()) == sarcasm.OPENING_MAX_WORDS
    assert rest.startswith("nine ten")


def test_split_opening_uses_the_first_sentence():
    opening, rest = sarcasm.split_opening("Great product. It broke immediately though.")
    assert opening == "Great product."
    assert rest == "It broke immediately though."


def test_analyze_handles_empty_and_tiny_text():
    assert sarcasm.analyze("")["suspected"] is False
    assert sarcasm.analyze("wow")["suspected"] is False
    assert sarcasm.split_opening("") == ("", "")


def test_cue_matching_is_word_bounded():
    assert sarcasm.negative_cues("the screen broke in a day") == ["broke"]
    assert sarcasm.negative_cues("the kitchen has a brick oven") == []
    assert sarcasm.positive_cues("best") == ["best"]
    assert sarcasm.positive_cues("the bestest") == []


def test_add_flag_keeps_strongest_first():
    result = {"suspected": True, "score": 1.0, "risk_level": "high"}
    merged = sarcasm.add_flag([{"code": "X", "label": "x", "severity": "low"}], result)
    assert [flag["code"] for flag in merged] == ["SARCASM_SUSPECTED", "X"]
    untouched = sarcasm.add_flag([{"code": "X", "label": "x", "severity": "low"}],
                                 {"suspected": False, "score": 0.0})
    assert [flag["code"] for flag in untouched] == ["X"]
