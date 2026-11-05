"""Phase 3.5 safety contract: the three switches must be pure additions.

With ``ENABLE_TIER1=false ENABLE_SARCASM=false ENABLE_SHAP=false`` the
``/api/predict`` body has exactly the Phase 3 key set and the Phase 3 values;
with them on, every Phase 3 key is still present, with the same type and the
same meaning. This is the test that protects the 78 committed Phase 3 tests.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.services import tier1

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
NEW_KEYS = {"tier1", "sarcasm", "decision_source"}
PHASE3_TYPES = {
    "id": int,
    "verdict": str,
    "fake_probability": float,
    "confidence": float,
    "model_used": str,
    "sentiment": dict,
    "flags": list,
    "tokens": list,
    "meta": dict,
    "latency_ms": int,
    "created_at": str,
    "token_map": dict,
}

REVIEW = (
    "We stayed 3 nights in room 214. The location was fine but the bathroom was "
    "dirty, the wifi failed twice, and the manager refused to refund the last night."
)
SARCASTIC = "Wow, best phone ever, total garbage, the screen broke in a day"
BATCH_COLUMNS = {
    "row",
    "review",
    "rating",
    "verdict",
    "fake_probability",
    "confidence",
    "sentiment_label",
}
BATCH_SUMMARY_KEYS = {"total", "fake_count", "fake_percent", "avg_confidence"}


def upload(csv_text: str):
    return {"file": ("reviews.csv", csv_text.encode("utf-8"), "text/csv")}


@pytest.fixture()
def all_off(monkeypatch):
    monkeypatch.setattr(settings, "enable_tier1", False)
    monkeypatch.setattr(settings, "enable_sarcasm", False)
    monkeypatch.setattr(settings, "enable_shap", False)


@pytest.fixture()
def all_on(monkeypatch):
    monkeypatch.setattr(settings, "enable_tier1", True)
    monkeypatch.setattr(settings, "enable_sarcasm", True)
    monkeypatch.setattr(settings, "enable_shap", True)


def predict(client, review: str = REVIEW, **extra) -> dict:
    payload = {"review": review}
    payload.update(extra)
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


# ------------------------------------------------------- everything off ------
def test_off_gives_exact_phase3_keys(all_off, advanced_client):
    body = predict(advanced_client)
    assert set(body) == PHASE3_KEYS
    assert body["model_used"] in ("nb", "svm")
    assert body["verdict"] in ("fake", "genuine")
    assert 0.0 <= body["fake_probability"] <= 1.0
    assert set(body["sentiment"]) == {"compound", "label", "pos", "neu", "neg"}
    assert set(body["meta"]) == {"words", "exclamations", "caps_words"}
    for flag in body["flags"]:
        assert set(flag) == {"code", "label", "severity"}
    for token in body["tokens"]:
        assert set(token) == {"token", "score", "direction"}


def test_off_ignores_metadata_that_would_otherwise_fire(
    all_off, advanced_client, monkeypatch
):
    """reviews_last_minute=9 is only a rule trigger while Tier-1 is enabled."""
    body = predict(
        advanced_client, metadata={"user_id": "u-off", "reviews_last_minute": 9}
    )
    assert "tier1" not in body
    assert "decision_source" not in body
    assert body["model_used"] in ("nb", "svm")
    assert body["tokens"], "the model still explains, as in Phase 3"


def test_off_never_duplicate_floods(all_off, advanced_client):
    for _ in range(5):
        body = predict(advanced_client, review="Identical repeated text used five times")
        assert body["model_used"] in ("nb", "svm")
        assert "tier1" not in body


def test_off_sarcasm_adds_nothing(all_off, advanced_client):
    body = predict(advanced_client, review=SARCASTIC)
    assert "sarcasm" not in body
    assert not [flag for flag in body["flags"] if flag["code"] == "SARCASM_SUSPECTED"]


def test_off_batch_summary_keeps_four_keys(all_off, advanced_client):
    csv_text = (
        "user_id,posted_at,review\n"
        '"u1","2026-01-31T09:00:00Z","First distinct review about a kettle"\n'
        '"u1","2026-01-31T09:00:10Z","Second distinct review about a toaster"\n'
    )
    body = advanced_client.post("/api/predict/batch", files=upload(csv_text)).json()
    assert set(body["summary"]) == BATCH_SUMMARY_KEYS
    for row in body["rows"]:
        assert set(row) == BATCH_COLUMNS


# ------------------------------------------------------- everything on -------
def test_on_keeps_every_phase3_key_with_the_same_type(all_on, advanced_client):
    with_off = predict(advanced_client)
    with_on = predict(advanced_client)
    assert PHASE3_KEYS <= set(with_on)
    assert set(with_on) - PHASE3_KEYS == NEW_KEYS
    for key, expected_type in PHASE3_TYPES.items():
        assert type(with_on[key]) is expected_type, key
        assert type(with_off[key]) is expected_type, key


def test_features_on_do_not_change_model_output(advanced_client, monkeypatch):
    """The verdict, probability and explanation come from the model unchanged."""
    for name in ("enable_tier1", "enable_sarcasm"):
        monkeypatch.setattr(settings, name, False)
    off = predict(advanced_client)
    for name in ("enable_tier1", "enable_sarcasm"):
        monkeypatch.setattr(settings, name, True)
    on = predict(advanced_client)

    for key in (
        "verdict",
        "fake_probability",
        "confidence",
        "model_used",
        "sentiment",
        "flags",
        "tokens",
        "token_map",
        "meta",
    ):
        assert on[key] == off[key], key
    assert on["decision_source"] == "model"
    assert 0.0 <= on["fake_probability"] <= 1.0
    assert on["meta"]["words"] == len(REVIEW.split())


def test_new_fields_are_the_only_difference(all_on, advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "enable_tier1", False)
    monkeypatch.setattr(settings, "enable_sarcasm", False)
    stripped = predict(advanced_client)
    monkeypatch.setattr(settings, "enable_tier1", True)
    monkeypatch.setattr(settings, "enable_sarcasm", True)
    full = predict(advanced_client)

    for key in PHASE3_KEYS - {"id", "latency_ms", "created_at"}:
        assert full[key] == stripped[key], key
    assert set(full) - set(stripped) == NEW_KEYS


def test_new_blocks_have_the_documented_shape(all_on, advanced_client):
    body = predict(advanced_client, review=SARCASTIC)
    assert set(body["tier1"]) == {"triggered", "action", "rules"}
    assert body["decision_source"] in ("model", "tier1_rules")
    assert body["sarcasm"]["suspected"] is True
    assert set(body["sarcasm"]) == {
        "suspected",
        "score",
        "risk_level",
        "positive_cues",
        "negative_cues",
    }


def test_explain_endpoint_is_unaffected_by_the_predict_switches(
    advanced_client, monkeypatch
):
    monkeypatch.setattr(settings, "enable_tier1", False)
    monkeypatch.setattr(settings, "enable_sarcasm", False)
    response = advanced_client.post("/api/explain", json={"review": REVIEW, "model": "svm"})
    assert response.status_code == 200, response.text
    assert {"method", "tokens", "model_used"} <= set(response.json())


def test_other_endpoints_unchanged(all_on, advanced_client):
    health = advanced_client.get("/api/health").json()
    assert set(health) == {"status", "models_loaded", "version"}
    models = advanced_client.get("/api/models").json()
    assert set(models) == {"models", "default", "best_model", "active_feature_set"}
    history = advanced_client.get("/api/history").json()
    assert set(history) == {"total", "entries", "items"}


def test_default_settings_are_on(advanced_client):
    """Fresh values of Settings() read the environment with switches enabled."""
    from app.config import Settings

    assert all(
        getattr(Settings(), name) is True
        for name in ("enable_tier1", "enable_sarcasm", "enable_shap")
    )


def test_batch_without_behaviour_columns_is_identical(all_on, advanced_client):
    csv_text = 'review,rating\n"Distinct review about a kettle",3\n'
    body = advanced_client.post("/api/predict/batch", files=upload(csv_text)).json()
    assert set(body["summary"]) == BATCH_SUMMARY_KEYS
    assert set(body["rows"][0]) == BATCH_COLUMNS


def test_tier1_soft_rules_never_reach_flags(all_on, advanced_client):
    body = predict(advanced_client, review="goooood buy")
    soft = {
        rule["code"] for rule in body["tier1"]["rules"] if rule["kind"] == "soft"
    }
    assert soft & {"VERY_SHORT", "REPEATED_CHARACTERS", "LINK_OR_CONTACT_SPAM"}
    assert not (soft & {flag["code"] for flag in body["flags"]})


def test_hard_rule_only_changes_its_own_fields(all_on, advanced_client):
    body = predict(
        advanced_client,
        review="Some review text",
        metadata={"user_id": "u-x", "reviews_last_minute": 40},
    )
    assert body["model_used"] == "tier1_rules"
    assert body["verdict"] == "fake"
    assert body["fake_probability"] == 1.0
    assert body["confidence"] == 1.0
    assert body["tokens"] == []
    assert body["decision_source"] == "tier1_rules"
    # still a valid Phase 3 body otherwise
    assert PHASE3_KEYS <= set(body)
    assert set(body["sentiment"]) == {"compound", "label", "pos", "neu", "neg"}
    assert set(body["meta"]) == {"words", "exclamations", "caps_words"}


def test_module_singletons_are_reset_between_tests(advanced_client):
    """The autouse fixture gives each advanced test an empty Tier-1 tracker."""
    assert tier1.tracker.stats() == {"users": 0, "texts": 0}
    advanced_client.post(
        "/api/predict",
        json={"review": "One more review about a kettle", "metadata": {"user_id": "z"}},
    )
    assert tier1.tracker.stats()["users"] == 1
