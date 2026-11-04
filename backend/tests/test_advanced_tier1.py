"""Phase 3.5 feature 1: the Tier-1 rule filter.

Covers the two hard rules (velocity, duplicate flood) through both sources,
the three soft signals, the "the model never ran" guarantee, history storage,
metadata validation, the batch CSV columns, and the config thresholds.
"""
from __future__ import annotations

import json

import pytest

from app.config import settings
from app.services import tier1
from app.services.predictor import predictor

REVIEW_FIELDS = {
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

TEXTS = [
    "The hotel lobby smelled like paint and the lift worked only sometimes.",
    "Room 41 had a leaking tap and the breakfast hall closed at nine sharp.",
    "The wifi dropped four times during two working days in room 12.",
    "Staff were polite but the air conditioner rattled all through night.",
    "The pool was closed for maintenance although the booking said it was open.",
    "Checkin took 40 minutes and the key card stopped working twice daily.",
]


def distinct_review(index: int) -> str:
    """A different, unremarkable review each time (no duplicate flood)."""
    return TEXTS[index % len(TEXTS)] + f" Reference {index}."


def codes(block: dict, kind: str | None = None) -> set[str]:
    return {
        rule["code"]
        for rule in block["rules"]
        if kind is None or rule["kind"] == kind
    }


@pytest.fixture()
def no_model_run(monkeypatch):
    """Make running the classifier an error, so 'it was skipped' is provable."""

    def boom(*args, **kwargs):  # pragma: no cover - only reached on failure
        raise AssertionError("the ML model must not run when a hard rule fired")

    monkeypatch.setattr(predictor, "predict_one", boom)
    monkeypatch.setattr(predictor, "predict_many", boom)
    return boom


# ------------------------------------------------------------------ basics ---
def test_request_without_metadata_still_works(advanced_client):
    response = advanced_client.post(
        "/api/predict", json={"review": distinct_review(0)}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert REVIEW_FIELDS <= set(body)
    assert set(body) - REVIEW_FIELDS == {"tier1", "sarcasm", "decision_source"}
    assert body["decision_source"] == "model"
    assert body["model_used"] in ("nb", "svm")
    assert body["tier1"]["triggered"] is False
    assert body["tier1"]["action"] == "pass"
    assert all(rule["kind"] == "soft" for rule in body["tier1"]["rules"])


def test_tier1_block_shape(advanced_client):
    body = advanced_client.post(
        "/api/predict", json={"review": distinct_review(1)}
    ).json()
    assert set(body["tier1"]) == {"triggered", "action", "rules"}
    assert isinstance(body["tier1"]["triggered"], bool)
    assert body["tier1"]["action"] in ("pass", "flag_spam")
    for rule in body["tier1"]["rules"]:
        assert set(rule) == {"code", "label", "severity", "kind"}
        assert rule["severity"] in ("low", "medium", "high")
        assert rule["kind"] in ("soft", "hard")
        assert isinstance(rule["label"], str) and rule["label"]


# ------------------------------------------------------- hard rule: speed ---
def test_velocity_hard_rule_from_metadata(advanced_client, no_model_run):
    body = advanced_client.post(
        "/api/predict",
        json={
            "review": distinct_review(2),
            "metadata": {"user_id": "user-fast", "reviews_last_minute": 9},
        },
    ).json()
    assert body["model_used"] == "tier1_rules"
    assert body["decision_source"] == "tier1_rules"
    assert body["verdict"] == "fake"
    assert body["fake_probability"] == 1.0
    assert body["confidence"] == 1.0
    assert body["tokens"] == []
    assert body["token_map"] == {}
    assert body["tier1"]["triggered"] is True
    assert body["tier1"]["action"] == "flag_spam"
    assert "VELOCITY_EXCEEDED" in codes(body["tier1"], "hard")
    # cheap VADER block still present and well formed
    assert set(body["sentiment"]) == {"compound", "label", "pos", "neu", "neg"}
    assert body["meta"]["words"] > 0


def test_velocity_at_the_limit_does_not_fire(advanced_client):
    """The rule is *more than* N per minute, so exactly 5 reported is allowed."""
    body = advanced_client.post(
        "/api/predict",
        json={
            "review": distinct_review(3),
            "metadata": {"user_id": "user-edge", "reviews_last_minute": 5},
        },
    ).json()
    assert body["decision_source"] == "model"
    assert "VELOCITY_EXCEEDED" not in codes(body["tier1"])


def test_velocity_over_the_limit_fires(advanced_client):
    body = advanced_client.post(
        "/api/predict",
        json={
            "review": distinct_review(4),
            "metadata": {"user_id": "user-over", "reviews_last_minute": 6},
        },
    ).json()
    assert body["decision_source"] == "tier1_rules"
    assert "VELOCITY_EXCEEDED" in codes(body["tier1"], "hard")


def test_velocity_without_user_id_still_uses_the_reported_count(advanced_client):
    """reviews_last_minute alone is evidence; no user_id needed."""
    body = advanced_client.post(
        "/api/predict",
        json={"review": distinct_review(5), "metadata": {"reviews_last_minute": 20}},
    ).json()
    assert body["decision_source"] == "tier1_rules"
    assert "VELOCITY_EXCEEDED" in codes(body["tier1"], "hard")


def test_velocity_sliding_window_from_server_side_counts(
    advanced_client, monkeypatch
):
    """No reported count: the in-memory 60 s window keyed by user_id decides."""
    monkeypatch.setattr(settings, "tier1_max_reviews_per_minute", 2)
    fired_at = None
    for index in range(5):
        body = advanced_client.post(
            "/api/predict",
            json={
                "review": distinct_review(index),
                "metadata": {"user_id": "user-window"},
            },
        ).json()
        if body["decision_source"] == "tier1_rules":
            fired_at = index + 1
            assert "VELOCITY_EXCEEDED" in codes(body["tier1"], "hard")
            break
    assert fired_at == 3, f"expected the 3rd review to exceed a limit of 2, got {fired_at}"


def test_window_is_per_user(advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "tier1_max_reviews_per_minute", 2)
    for index in range(2):
        for user in ("user-a", "user-b", "user-c"):
            # unique text per call, so only velocity can possibly fire here
            review = f"{distinct_review(index)} Posted by {user}."
            body = advanced_client.post(
                "/api/predict",
                json={"review": review, "metadata": {"user_id": user}},
            ).json()
            assert body["decision_source"] == "model", body["tier1"]


def test_posted_at_drives_the_window(advanced_client):
    """A client-supplied timestamp older than the window does not accumulate."""
    body = advanced_client.post(
        "/api/predict",
        json={
            "review": distinct_review(0),
            "metadata": {"user_id": "user-old", "posted_at": "2020-01-01T00:00:00Z"},
        },
    ).json()
    assert body["decision_source"] == "model"
    assert body["tier1"]["triggered"] is False


# --------------------------------------------------- hard rule: duplicate ---
def test_duplicate_flood_fires_on_third_copy(advanced_client):
    review = "Amazing product best price buy now from this seller today"
    decisions = []
    for _ in range(4):
        body = advanced_client.post("/api/predict", json={"review": review}).json()
        decisions.append((body["decision_source"], body["model_used"]))
    assert decisions[0][0] == "model"
    assert decisions[1][0] == "model"
    assert decisions[2] == ("tier1_rules", "tier1_rules")
    assert decisions[3] == ("tier1_rules", "tier1_rules")


def test_duplicate_flood_ignores_case_and_spacing(advanced_client):
    variants = [
        "Fantastic deal you should really buy this today",
        "fantastic  DEAL you should    really buy THIS today",
        "  Fantastic deal you should really buy this today  ",
    ]
    for review in variants[:2]:
        advanced_client.post("/api/predict", json={"review": review})
    body = advanced_client.post("/api/predict", json={"review": variants[2]}).json()
    assert "DUPLICATE_FLOOD" in codes(body["tier1"], "hard")
    assert body["model_used"] == "tier1_rules"


def test_duplicate_threshold_is_configurable(advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "tier1_duplicate_threshold", 5)
    review = "One more very specific review text about a kettle and its warranty"
    for _ in range(3):
        body = advanced_client.post("/api/predict", json={"review": review}).json()
        assert body["decision_source"] == "model"
        assert "DUPLICATE_FLOOD" not in codes(body["tier1"])


def test_duplicate_window_is_ten_minutes():
    """Unit level: the duplicate window prunes hits older than 600 seconds."""
    tracker = tier1.Tier1Tracker(max_keys=10)
    base = 1_700_000_000.0
    hashed = tier1.text_hash("same review text")
    assert tracker.observe_text(hashed, base) == 1
    assert tracker.observe_text(hashed, base + 300) == 2
    # 11 minutes after the first copy, only the second one is still counted.
    assert tracker.observe_text(hashed, base + 660) == 2
    # ... and one more inside that window reaches the default threshold of 3.
    assert tracker.observe_text(hashed, base + 700) == 3


# --------------------------------------------------------- soft signals -----
def test_soft_signals_never_touch_flags(advanced_client):
    body = advanced_client.post("/api/predict", json={"review": "Nice! gooooood"}).json()
    assert body["decision_source"] == "model"
    assert body["tier1"]["triggered"] is False
    assert body["tier1"]["action"] == "pass"
    soft = codes(body["tier1"], "soft")
    assert {"VERY_SHORT", "REPEATED_CHARACTERS"} <= soft
    # The existing flags list keeps only the Phase 3 rules.
    flag_codes = {flag["code"] for flag in body["flags"]}
    assert not ({"VERY_SHORT", "LINK_OR_CONTACT_SPAM", "REPEATED_CHARACTERS"} & flag_codes)


def test_link_and_contact_soft_signal(advanced_client):
    review = (
        "The resort was average but you can book cheaper at http://fake-offer.example "
        "or mail sales@fake-offer.example or call 01234567890 any time of the day."
    )
    body = advanced_client.post("/api/predict", json={"review": review}).json()
    assert "LINK_OR_CONTACT_SPAM" in codes(body["tier1"], "soft")
    assert "LINK_OR_CONTACT_SPAM" not in {flag["code"] for flag in body["flags"]}
    assert body["verdict"] in ("fake", "genuine")


def test_very_short_word_threshold_is_configurable(advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "tier1_min_words", 7)
    body = advanced_client.post(
        "/api/predict", json={"review": "The room was clean and quiet"}
    ).json()  # 6 words
    assert "VERY_SHORT" in codes(body["tier1"], "soft")
    monkeypatch.setattr(settings, "tier1_min_words", 4)
    body = advanced_client.post(
        "/api/predict", json={"review": "The room was clean and quiet"}
    ).json()
    assert "VERY_SHORT" not in codes(body["tier1"])


def test_detailed_review_has_no_soft_signals(advanced_client):
    body = advanced_client.post(
        "/api/predict",
        json={"review": "We stayed 3 nights in room 214 and the manager refunded night 2."},
    ).json()
    assert body["tier1"]["rules"] == []


# ------------------------------------------------------------ history -------
def test_rule_decision_is_saved_to_history(advanced_client):
    review = distinct_review(5)
    created = advanced_client.post(
        "/api/predict",
        json={"review": review, "metadata": {"user_id": "u-save", "reviews_last_minute": 30}},
    ).json()
    listing = advanced_client.get("/api/history").json()
    entry = next(row for row in listing["entries"] if row["id"] == created["id"])
    assert entry["model_used"] == "tier1_rules"
    assert entry["verdict"] == "fake"
    assert entry["fake_probability"] == 1.0
    assert json.loads(entry["tokens_json"]) == []


def test_metadata_validation_errors(advanced_client):
    cases = [
        {"review": "nice hotel", "metadata": {"user_id": "x" * 129}},
        {"review": "nice hotel", "metadata": {"user_id": "   "}},
        {"review": "nice hotel", "metadata": {"reviews_last_minute": -1}},
        {"review": "nice hotel", "metadata": {"reviews_last_minute": 999_999}},
        {"review": "nice hotel", "metadata": {"posted_at": "not-a-date"}},
        {"review": "nice hotel", "metadata": {"unexpected": 1}},
        {"review": "nice hotel", "metadata": "just a string"},
    ]
    for payload in cases:
        response = advanced_client.post("/api/predict", json=payload)
        assert response.status_code == 422, (payload, response.text)
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_metadata_does_not_fall_back_to_a_prediction(advanced_client):
    response = advanced_client.post(
        "/api/predict",
        json={"review": "nice hotel", "metadata": {"reviews_last_minute": "many"}},
    )
    assert response.status_code == 422
    assert "tier1" not in response.json()


# ---------------------------------------------------------------- batch -----
def upload(csv_text: str):
    return {"file": ("reviews.csv", csv_text.encode("utf-8"), "text/csv")}


def test_batch_computes_velocity_per_user_inside_the_file(advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "tier1_max_reviews_per_minute", 2)
    rows = "\n".join(
        f'"u1","2026-01-31T09:00:{index:02d}Z","{distinct_review(index)}"'
        for index in range(5)
    )
    csv_text = "user_id,posted_at,review\n" + rows + "\n"
    response = advanced_client.post("/api/predict/batch", files=upload(csv_text))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"]["total"] == 5
    # rows 3-5 exceed a limit of 2 reviews/minute for u1
    assert body["summary"]["tier1_flagged"] == 3
    assert all(row["fake_probability"] == 1.0 for row in body["rows"][2:])
    assert all(row["fake_probability"] < 1.0 for row in body["rows"][:2])
    assert [row["verdict"] for row in body["rows"][2:]] == ["fake"] * 3


def test_batch_without_behaviour_columns_is_unchanged(advanced_client):
    csv_text = "review,rating\n" + "\n".join(
        f'"{distinct_review(index)}",3' for index in range(4)
    ) + "\n"
    body = advanced_client.post("/api/predict/batch", files=upload(csv_text)).json()
    assert set(body["summary"]) == {
        "total",
        "fake_count",
        "fake_percent",
        "avg_confidence",
    }
    assert "tier1_flagged" not in body["summary"]


def test_batch_duplicate_rows_are_flagged_inside_the_file(advanced_client, monkeypatch):
    monkeypatch.setattr(settings, "tier1_duplicate_threshold", 2)
    same = "A repeated review about a blender that stopped working on day three"
    csv_text = "user_id,review\n" + "\n".join(
        f'"u9","{same}"' for _ in range(3)
    ) + "\n"
    body = advanced_client.post("/api/predict/batch", files=upload(csv_text)).json()
    assert body["summary"]["tier1_flagged"] == 2  # rows 2 and 3 are repeats


def test_batch_rejects_a_bad_posted_at(advanced_client):
    csv_text = 'user_id,posted_at,review\n"u1","yesterday","nice hotel with a pool and gym"\n'
    response = advanced_client.post("/api/predict/batch", files=upload(csv_text))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CSV_INVALID_POSTED_AT"


def test_batch_upload_does_not_pollute_server_counters(advanced_client):
    """The per-file tracker is separate from the one /api/predict uses."""
    same = "Identical review text used to test batch isolation on purpose"
    csv_text = "user_id,review\n" + "\n".join(f'"u7","{same}"' for _ in range(3)) + "\n"
    advanced_client.post("/api/predict/batch", files=upload(csv_text))
    body = advanced_client.post("/api/predict", json={"review": same}).json()
    assert body["decision_source"] == "model"
    assert "DUPLICATE_FLOOD" not in codes(body["tier1"])


# ------------------------------------------------------------- unit level ---
def test_tracker_is_memory_bounded(monkeypatch):
    monkeypatch.setattr(settings, "tier1_max_tracked_keys", 3)
    tracker = tier1.Tier1Tracker()
    base = 1_700_000_000.0
    for index in range(10):
        tracker.observe_user(f"user-{index}", base + index)
        tracker.observe_text(f"hash-{index}", base + index)
    assert tracker.stats() == {"users": 3, "texts": 3}


def test_tracker_window_prunes_old_entries():
    tracker = tier1.Tier1Tracker(max_keys=100)
    base = 1_700_000_000.0
    assert tracker.observe_user("solo", base) == 1
    assert tracker.observe_user("solo", base + 30) == 2
    # 90 s later the first hit is outside the 60 s window, the second is not.
    assert tracker.observe_user("solo", base + 90) == 2
    # 120 s after the first hit both earlier ones are gone.
    assert tracker.observe_user("solo", base + 120) == 2


def test_tracker_is_thread_safe():
    import threading

    tracker = tier1.Tier1Tracker(max_keys=5000)
    errors: list[BaseException] = []

    def hammer(worker: int) -> None:
        try:
            for index in range(40):
                tracker.observe_user(f"thread-{worker}", 1_700_000_000.0 + index)
                tracker.observe_text(f"text-{worker}-{index}", 1_700_000_000.0 + index)
        except BaseException as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=hammer, args=(w,)) for w in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert tracker.stats()["users"] == 8


def test_soft_signals_are_pure():
    assert {"VERY_SHORT"} <= {r["code"] for r in tier1.soft_signals("good buy")}
    assert tier1.soft_signals("We stayed three nights and the room was clean.") == []
    assert tier1.normalise_text("  A  B\tC ") == "a b c"
    assert tier1.text_hash("A  B") == tier1.text_hash("  a b ")
