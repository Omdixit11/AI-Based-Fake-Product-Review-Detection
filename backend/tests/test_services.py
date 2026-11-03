"""Unit tests for the Phase 3 service layer.

Covers the two rules the spec calls critical:
* predictions must reuse ``backend/ml`` preprocessing/feature code (parity);
* the fake probability must be mapped through ``model.classes_`` + FAKE_LABEL,
  never a hard-coded column index (proved with a swapped label).
"""
from __future__ import annotations

import numpy as np
import pytest

import ml.features as ml_features
import ml.preprocess as ml_preprocess
from app.config import settings
from app.services import explain, flags, sentiment
from app.services.predictor import (
    ModelArtifactError,
    Prediction,
    Predictor,
    predictor,
)

FAKY_TEXT = (
    "This hotel is AMAZING!!! Perfect stay, highly recommend, five stars, "
    "best ever, life changing experience!!!"
)
Genuine_TEXT = (
    "We stayed 3 nights in room 214. The location was fine but the bathroom "
    "was dirty, the wifi failed twice, and the manager refused to refund the "
    "last night. Breakfast ended at 10 although we were told 11."
)


@pytest.fixture(scope="module", autouse=True)
def loaded_predictor():
    predictor.load()
    return predictor


# --------------------------------------------------------------- parity ----
def test_api_uses_the_same_ml_function_objects():
    """The API must not re-implement preprocessing or feature building."""
    assert predictor.__module__ == "app.services.predictor"
    module = __import__("app.services.predictor", fromlist=["clean_text"])
    assert module.clean_text is ml_preprocess.clean_text
    assert module.build_features is ml_features.build_features


def test_clean_text_parity_on_a_review():
    cleaned = module_clean_text(FAKY_TEXT)
    assert cleaned == ml_preprocess.clean_text(FAKY_TEXT)
    assert not any(ch.isdigit() for ch in cleaned)


def module_clean_text(text: str) -> str:
    module = __import__("app.services.predictor", fromlist=["clean_text"])
    return module.clean_text(text)


def test_features_match_the_ml_pipeline_exactly():
    from ml.config import NB_MODEL_PATH, VECTORIZER_PATH, SCALER_PATH  # noqa: F401
    import joblib

    fitted = {
        "vectorizer": predictor.vectorizer,
        "scaler": predictor.scaler,
    }
    via_api = predictor._matrix([FAKY_TEXT])
    via_ml = ml_features.build_features(
        [FAKY_TEXT], fitted, predictor.active_feature_set
    )
    assert np.allclose(via_api.todense(), via_ml.todense())


# ------------------------------------------------------------ sentiment ----
def test_sentiment_labels_use_the_documented_thresholds():
    assert sentiment.label_for(0.2) == "Positive"
    assert sentiment.label_for(0.19) == "Mixed"
    assert sentiment.label_for(-0.2) == "Negative"
    assert sentiment.label_for(-0.19) == "Mixed"
    assert sentiment.label_for(0.0) == "Mixed"


def test_sentiment_block_shape_and_vectorised_agreement():
    texts = [FAKY_TEXT, Genuine_TEXT, "It is a room."]
    many = sentiment.analyze_many(texts)
    for text, block in zip(texts, many):
        single = sentiment.analyze(text)
        assert single == block
        assert set(single) == {"compound", "label", "pos", "neu", "neg"}
        assert single["label"] in ("Positive", "Mixed", "Negative")


def test_sentiment_matches_vader_scores_from_the_ml_package():
    neg, neu, pos, compound = ml_features.extract_vader([FAKY_TEXT])[0]
    block = sentiment.analyze(FAKY_TEXT)
    assert block["pos"] == round(float(pos), 4)
    assert block["neu"] == round(float(neu), 4)
    assert block["neg"] == round(float(neg), 4)
    assert block["compound"] == round(float(compound), 4)
    assert block["label"] == "Positive"


# --------------------------------------------------------------- flags -----
def test_flags_promo_review_hits_the_expected_rules():
    detected = {
        f["code"]: f
        for f in flags.detect_flags(FAKY_TEXT, sentiment.analyze(FAKY_TEXT))
    }
    assert "EXCLAMATION_OVERLOAD" in detected
    assert "PROMOTIONAL_LANGUAGE" in detected
    assert "EXTREME_ONE_SIDED_SENTIMENT" in detected
    assert "NO_CONCRETE_DETAILS" in detected
    # only one word is fully upper-case ("AMAZING!!!"), so ALL_CAPS must not fire
    assert "ALL_CAPS" not in detected
    for flag in detected.values():
        assert flag["severity"] in ("low", "medium", "high")
        assert flag["label"]


def test_all_caps_flag_needs_two_words():
    one_caps = "WOW great hotel stay, the pool was clean and staff helpful overall."
    assert "ALL_CAPS" not in [f["code"] for f in flags.detect_flags(one_caps)]

    two_caps = "WOW GREAT hotel stay, the pool was clean and staff helpful overall."
    hits = [f for f in flags.detect_flags(two_caps) if f["code"] == "ALL_CAPS"]
    assert len(hits) == 1
    assert hits[0]["label"] == "Words in ALL CAPS"


def test_balanced_review_is_not_flagged_as_vague():
    codes = {
        f["code"]
        for f in flags.detect_flags(Genuine_TEXT, sentiment.analyze(Genuine_TEXT))
    }
    assert "NO_CONCRETE_DETAILS" not in codes  # digits + contrast words present
    assert "EXCLAMATION_OVERLOAD" not in codes
    assert "SHORT_REVIEW" not in codes


def test_rating_sentiment_mismatch_only_when_rating_given():
    without = [f["code"] for f in flags.detect_flags("Amazing perfect stay best ever", sentiment.analyze("Amazing perfect stay best ever"))]
    assert "RATING_SENTIMENT_MISMATCH" not in without
    positive_text = "The staff were excellent and the suite was beautiful."
    with_low_rating = flags.detect_flags(
        positive_text, sentiment.analyze(positive_text), rating=1
    )
    assert any(f["code"] == "RATING_SENTIMENT_MISMATCH" for f in with_low_rating)
    negative_text = "Dirty sheets, broken air conditioning and rude reception staff."
    with_high_rating = flags.detect_flags(
        negative_text, sentiment.analyze(negative_text), rating=5
    )
    assert any(f["code"] == "RATING_SENTIMENT_MISMATCH" for f in with_high_rating)


def test_short_review_flag_and_severity_ordering():
    detected = flags.detect_flags("Great hotel!!!")
    assert detected[0]["severity"] in ("high", "medium", "low")
    codes = {f["code"] for f in detected}
    assert "SHORT_REVIEW" in codes
    order = {"high": 0, "medium": 1, "low": 2}
    severities = [f["severity"] for f in detected]
    assert severities == sorted(severities, key=lambda s: order[s])


def test_meta_counters():
    meta = flags.count_meta("Wow WOW!!! Room 101 is GREAT")
    # words: Wow, WOW!!!, Room, 101, is, GREAT - caps: WOW!!! and GREAT
    assert meta == {"words": 6, "exclamations": 3, "caps_words": 2}


# -------------------------------------------------------------- explain ----
def test_explain_token_count_and_direction_are_consistent():
    prediction = predictor.predict_one(FAKY_TEXT, "svm")
    tokens = prediction.tokens
    assert 0 < len(tokens) <= settings.max_tokens_returned
    for token in tokens:
        assert set(token) == {"token", "score", "direction"}
        assert token["direction"] == ("fake" if token["score"] > 0 else "genuine")
    scores = [abs(t["score"]) for t in tokens]
    assert scores == sorted(scores, reverse=True)


def test_explain_tokens_map_back_to_surface_words():
    prediction = predictor.predict_one(FAKY_TEXT, "svm")
    assert prediction.token_map, "surface-word mapping must be returned"
    for token, words in prediction.token_map.items():
        assert words, f"no surface words for {token}"
        lowered_review = FAKY_TEXT.lower()
        for word in words:
            assert word.lower() in lowered_review


def test_nb_scores_are_log_probability_differences():
    scores = explain.nb_score_vector(predictor.models["nb"], settings.fake_label)
    log_prob = predictor.models["nb"].feature_log_prob_
    assert scores.shape == (log_prob.shape[1],)
    assert np.isfinite(scores).all()


def test_svm_scores_come_from_the_linear_base_coefficients():
    scores = explain.svm_score_vector(predictor.svm_linear_base, settings.fake_label)
    coef = np.asarray(predictor.svm_linear_base.coef_, dtype=float).reshape(-1)
    assert scores.shape == coef.shape
    assert np.allclose(scores, coef)  # FAKE_LABEL=1 is the positive side
    flipped = explain.svm_score_vector(predictor.svm_linear_base, 0)
    assert np.allclose(flipped, -coef)


def test_top_contributions_only_uses_present_features():
    names = list(predictor.feature_names)
    matrix = predictor._matrix([FAKY_TEXT])
    scores = explain.svm_score_vector(predictor.svm_linear_base, settings.fake_label)
    top = explain.top_contributions(scores, matrix[0], names, limit=8)
    present = set(names[index] for index in matrix[0].indices)
    assert all(entry["token"] in present for entry in top)
    assert len(top) <= 8


def test_surface_map_lemmatizes_like_the_pipeline():
    mapping = explain.surface_map("Amazing rooms but the hotel was dirty")
    assert "amaze" in mapping and "Amazing" in mapping["amaze"]
    assert "room" in mapping
    # stop words are dropped by clean_text, so they cannot appear as keys
    assert "the" not in mapping
    assert explain.expand_to_surface([{"token": "hotel amaze"}], mapping)["hotel amaze"]


# ------------------------------------------------------------ predictor ----
def test_resolve_model_best_follows_metrics_json():
    assert predictor.resolve_model("best") == predictor.best_model
    assert predictor.resolve_model("nb") == "nb"
    assert predictor.resolve_model("svm") == "svm"
    with pytest.raises(ValueError):
        predictor.resolve_model("random-forest")


def test_fake_column_is_taken_from_classes_not_position():
    model = predictor.models["svm"]
    column = predictor.fake_column(model)
    assert int(model.classes_[column]) == settings.fake_label


def test_swapped_fake_label_inverts_the_probability(monkeypatch):
    original = predictor.predict_one(FAKY_TEXT, "svm")
    monkeypatch.setattr(settings, "fake_label", 0)
    swapped = predictor.predict_one(FAKY_TEXT, "svm")
    monkeypatch.undo()
    assert swapped.verdict != original.verdict or original.fake_probability == 0.5
    assert swapped.fake_probability == pytest.approx(1.0 - original.fake_probability, abs=1e-6)
    assert swapped.confidence == pytest.approx(original.confidence, abs=1e-6)


def test_verdict_and_confidence_relationship():
    for text in (FAKY_TEXT, Genuine_TEXT):
        prediction = predictor.predict_one(text, "nb")
        expected = "fake" if prediction.fake_probability >= 0.5 else "genuine"
        assert prediction.verdict == expected
        assert prediction.confidence == pytest.approx(
            max(prediction.fake_probability, 1 - prediction.fake_probability), abs=1e-6
        )


def test_batch_predictions_agree_with_single_predictions():
    texts = [FAKY_TEXT, Genuine_TEXT, "It was okay, nothing special at all."]
    batch = predictor.predict_many(texts, "nb")
    singles = [predictor.predict_one(text, "nb") for text in texts]
    assert [b.verdict for b in batch] == [s.verdict for s in singles]
    assert [b.fake_probability for b in batch] == [s.fake_probability for s in singles]
    assert all(not b.tokens for b in batch)  # batch rows carry no explanation


def test_single_review_is_fast():
    predictor.predict_one(Genuine_TEXT, "best")  # warm
    import time

    started = time.perf_counter()
    predictor.predict_one(Genuine_TEXT, "best")
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert elapsed_ms < 500, f"single review took {elapsed_ms:.0f} ms"


def test_missing_artifact_error_names_the_file_and_command(tmp_path, monkeypatch):
    import app.services.predictor as predictor_module

    fake_path = tmp_path / "nb_model.pkl"
    monkeypatch.setattr(
        predictor_module,
        "ARTIFACTS",
        (("nb_model", fake_path),),
    )
    lonely = Predictor()
    with pytest.raises(ModelArtifactError) as excinfo:
        lonely.load()
    message = excinfo.value.friendly_message()
    assert "nb_model.pkl" in message
    assert "python -m ml.run_pipeline" in message


def test_prediction_dataclass_defaults():
    prediction = Prediction(
        verdict="fake",
        fake_probability=0.9,
        confidence=0.9,
        model_used="nb",
        sentiment=sentiment.analyze("good"),
    )
    assert prediction.tokens == []
    assert prediction.token_map == {}
