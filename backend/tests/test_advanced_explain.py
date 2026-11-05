"""Phase 3.5 feature 3: POST /api/explain (SHAP for the SVM, log-probs for NB).

These tests pass whether or not the optional ``shap`` package is installed: the
expected ``method`` label is derived from what is actually available, and the
fallback paths are driven by monkeypatching the single lazy import helper.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.config import settings
from app.services import explain_shap
from app.services.predictor import predictor

REVIEW = (
    "We stayed 3 nights in room 214. The location was fine but the bathroom was "
    "dirty, the wifi failed twice, and the manager refused to refund the last night."
)
RESPONSE_KEYS = {
    "method",
    "model_used",
    "base_value",
    "tokens",
    "token_map",
    "latency_ms",
}


def shap_usable() -> bool:
    """Is the optional library importable right now (and switched on)?"""
    return bool(settings.enable_shap) and explain_shap._load_shap() is not None


def expected_svm_method() -> str:
    return (
        explain_shap.METHOD_SHAP_LINEAR
        if shap_usable()
        else explain_shap.METHOD_LINEAR_COEFFICIENTS
    )


def post(client, review: str = REVIEW, model: str = "best", **extra):
    payload = {"review": review, "model": model}
    payload.update(extra)
    return client.post("/api/explain", json=payload)


# ------------------------------------------------------------------ contract --
def test_svm_explain_shape(advanced_client):
    response = post(advanced_client, model="svm")
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == RESPONSE_KEYS
    assert body["method"] == expected_svm_method()
    assert body["model_used"] == "svm"
    assert isinstance(body["base_value"], float)
    assert body["latency_ms"] >= 1
    assert 0 < len(body["tokens"]) <= explain_shap.TOP_TOKENS
    for token in body["tokens"]:
        assert set(token) == {"token", "score", "direction"}
        assert isinstance(token["score"], float)
        assert token["direction"] == ("fake" if token["score"] > 0 else "genuine")
    # ranked by absolute contribution, strongest first
    magnitudes = [abs(token["score"]) for token in body["tokens"]]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_nb_explain_is_labelled_as_logprob(advanced_client):
    body = post(advanced_client, model="nb").json()
    assert body["method"] == explain_shap.METHOD_NB_LOGPROB
    assert body["model_used"] == "nb"
    assert 0 < len(body["tokens"]) <= explain_shap.TOP_TOKENS
    assert isinstance(body["base_value"], float)


def test_best_resolves_to_a_real_model(advanced_client):
    body = post(advanced_client, model="best").json()
    assert body["model_used"] in ("nb", "svm")
    metrics = advanced_client.get("/api/models").json()
    assert body["model_used"] == metrics["best_model"]


def test_token_map_maps_cleaned_tokens_back_to_surface_words(advanced_client):
    body = post(advanced_client, model="svm").json()
    tokens = [token["token"] for token in body["tokens"]]
    assert set(body["token_map"]) == set(tokens)
    for token, surface in body["token_map"].items():
        assert isinstance(surface, list)
        for word in surface:
            assert word.lower().strip("'") in REVIEW.lower()
    assert any(body["token_map"].values()), "at least one token maps back to a word"


# ------------------------------------------------------------- the maths ------
def _dense_row(review: str):
    from scipy import sparse as sp

    matrix = predictor._matrix([review])
    if sp.issparse(matrix):
        dense = np.asarray(matrix.todense(), dtype=float).ravel()
    else:
        dense = np.asarray(matrix, dtype=float).ravel()
    return matrix, dense


def _fake_sign() -> int:
    """+1 when the model's positive direction already means "fake"."""
    classes = [int(value) for value in predictor.svm_linear_base.classes_]
    return 1 if classes.index(int(settings.fake_label)) == 1 else -1


def test_contributions_are_additive_with_the_base_value(advanced_client):
    """base_value + sum(coef * x) is exactly the model's own decision value."""
    matrix, dense = _dense_row(REVIEW)
    coefficients = predictor.svm_linear_base.coef_.ravel()
    expected = float(predictor.svm_linear_base.decision_function(matrix)[0])
    body = post(advanced_client, model="svm").json()
    assert body["base_value"] + float(np.dot(coefficients, dense)) == pytest.approx(
        expected, abs=1e-6
    )


def test_every_reported_score_is_coef_times_tfidf(advanced_client):
    """SHAP of a linear model with a zero background == coef * value, per token."""
    _, dense = _dense_row(REVIEW)
    coefficients = predictor.svm_linear_base.coef_.ravel()
    names = [str(name) for name in predictor.feature_names]
    sign = _fake_sign()
    body = post(advanced_client, model="svm").json()

    for token in body["tokens"]:
        index = names.index(token["token"])
        value = round(float(coefficients[index]) * float(dense[index]), 4)
        assert token["score"] == pytest.approx(sign * value, abs=1e-4)

    strongest = float(np.max(np.abs(coefficients * dense)))
    assert abs(body["tokens"][0]["score"]) == pytest.approx(strongest, abs=1e-4)


def test_direct_computation_and_shap_agree(advanced_client, monkeypatch):
    """The fallback is not an approximation: same tokens, same scores."""
    # decided before patching, so it reflects this machine for real
    expected = expected_svm_method()
    with_shap = post(advanced_client, model="svm").json()
    monkeypatch.setattr(explain_shap, "_load_shap", lambda: None)
    without = post(advanced_client, model="svm").json()

    assert without["method"] == explain_shap.METHOD_LINEAR_COEFFICIENTS
    assert with_shap["method"] == expected
    assert [token["token"] for token in without["tokens"]] == [
        token["token"] for token in with_shap["tokens"]
    ]
    assert [token["score"] for token in without["tokens"]] == [
        token["score"] for token in with_shap["tokens"]
    ]
    assert without["base_value"] == with_shap["base_value"]


# ------------------------------------------------------------- fallbacks ------
def test_missing_shap_package_still_answers_200(advanced_client, monkeypatch):
    monkeypatch.setattr(explain_shap, "_load_shap", lambda: None)
    body = post(advanced_client, model="svm").json()
    assert body["method"] == explain_shap.METHOD_LINEAR_COEFFICIENTS
    assert body["model_used"] == "svm"
    assert body["tokens"]


def test_enable_shap_false_falls_back(advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "enable_shap", False)
    body = post(advanced_client, model="svm").json()
    assert body["method"] == explain_shap.METHOD_LINEAR_COEFFICIENTS
    assert body["tokens"]


def test_explainer_raising_keeps_the_shap_label(advanced_client, monkeypatch):
    """A library failure is not a different explanation: identical value, same name."""

    class BrokenExplainer:
        def __init__(self, model, background):
            raise NotImplementedError("LinearExplainer cannot handle sparse coefficients")

    class FakeShap:
        LinearExplainer = BrokenExplainer

    monkeypatch.setattr(explain_shap, "_load_shap", lambda: FakeShap)
    body = post(advanced_client, model="svm").json()
    assert body["method"] == explain_shap.METHOD_SHAP_LINEAR
    monkeypatch.setattr(explain_shap, "_load_shap", lambda: None)
    fallback = post(advanced_client, model="svm").json()
    assert body["tokens"] == fallback["tokens"]
    assert body["base_value"] == fallback["base_value"]


def test_nb_ignores_the_shap_switch(advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "enable_shap", False)
    body = post(advanced_client, model="nb").json()
    assert body["method"] == explain_shap.METHOD_NB_LOGPROB


def test_review_with_no_vocabulary_returns_empty_tokens(advanced_client):
    body = post(advanced_client, review="!!! ??? ...").json()
    assert body["tokens"] == []
    assert body["token_map"] == {}
    assert body["method"] in (
        explain_shap.METHOD_SHAP_LINEAR,
        explain_shap.METHOD_LINEAR_COEFFICIENTS,
    )


# ------------------------------------------------------------ validation ------
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"review": ""},
        {"review": "    "},
        {"review": "a" * 5001},
        {"review": "nice hotel", "model": "random-forest"},
        {"review": "nice hotel", "unexpected": 1},
        {"review": 42},
    ],
)
def test_validation_uses_the_error_envelope(advanced_client, payload):
    response = advanced_client.post("/api/explain", json=payload)
    assert response.status_code == 422, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"]


def test_explain_never_writes_to_history(advanced_client):
    before = advanced_client.get("/api/history").json()["total"]
    post(advanced_client, model="svm")
    post(advanced_client, model="nb")
    assert advanced_client.get("/api/history").json()["total"] == before


def test_explain_is_independent_of_the_predict_features(
    advanced_client, monkeypatch
):
    """Tier-1 and sarcasm off: the explain endpoint still works normally."""
    monkeypatch.setattr(settings, "enable_tier1", False)
    monkeypatch.setattr(settings, "enable_sarcasm", False)
    assert post(advanced_client, model="svm").status_code == 200
    assert post(advanced_client, model="nb").status_code == 200


def test_shap_available_helper_reflects_the_switch(monkeypatch):
    monkeypatch.setattr(settings, "enable_shap", False)
    assert explain_shap.shap_available() is False
    monkeypatch.setattr(settings, "enable_shap", True)
    assert explain_shap.shap_available() is (explain_shap._load_shap() is not None)
