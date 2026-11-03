"""HTTP tests for the FastAPI surface (contract shape, validation, history).

A temporary SQLite file from pytest's tmp_path is used, so no .db file is ever
written next to the repo (and nothing can be committed by accident).
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.config import settings
from app.db.database import database, session_scope
from app.db.models import History
from app.main import app, reset_rate_limiter

FAKE_REVIEW = (
    "This hotel is AMAZING!!! Perfect stay, highly recommend, five stars, "
    "best ever, life changing experience!!!"
)
GENUINE_REVIEW = (
    "We stayed 3 nights in room 214. The location was fine but the bathroom "
    "was dirty, the wifi failed twice, and the manager refused to refund the "
    "last night. Breakfast ended at 10 although we were told 11."
)

CONTRACT_KEYS = {
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
}
BATCH_ROW_KEYS = {
    "row",
    "review",
    "rating",
    "verdict",
    "fake_probability",
    "confidence",
    "sentiment_label",
}


@pytest.fixture(scope="session")
def temp_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("truthlens-db") / "api_history_test.db"
    settings.database_url = f"sqlite:///{db_path.as_posix()}"
    settings.rate_limit_per_minute = 0  # enabled explicitly in one test
    database.reset()
    database.create_tables()
    yield db_path
    database.reset()


@pytest.fixture(scope="session")
def client(temp_db):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_history(client):
    with session_scope() as session:
        session.execute(delete(History))
    reset_rate_limiter()
    yield


def upload(csv_text: str, filename: str = "reviews.csv"):
    return {"file": (filename, csv_text.encode("utf-8"), "text/csv")}


def assert_error(response, code: str, status_code: int):
    assert response.status_code == status_code, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert "Traceback" not in response.text


# ------------------------------------------------------------- basics ------
def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "models_loaded": True,
        "version": "1.0.0",
    }


def test_models_listing(client):
    body = client.get("/api/models").json()
    assert body["models"] == ["nb", "svm"]
    assert body["default"] == "best"
    assert body["best_model"] in ("nb", "svm")
    assert body["active_feature_set"] in ("tfidf_only", "tfidf_sentiment")


def test_metrics_endpoint_returns_metrics_json_verbatim(client):
    from app.config import METRICS_PATH

    response = client.get("/api/models/metrics")
    assert response.status_code == 200
    on_disk = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    assert response.json() == on_disk
    assert {"generated_at", "dataset", "best_model", "active_feature_set", "models"} <= set(
        response.json()
    )


def test_unknown_route_uses_the_error_envelope(client):
    assert_error(client.get("/api/does-not-exist"), "NOT_FOUND", 404)


# ------------------------------------------------------------- predict -----
@pytest.mark.parametrize("choice", ["best", "nb", "svm"])
def test_predict_contract_per_model(client, choice):
    response = client.post(
        "/api/predict", json={"review": FAKE_REVIEW, "model": choice}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # LLD fields are all present; token_map is the only additive extra.
    assert CONTRACT_KEYS <= set(body)
    assert set(body) - CONTRACT_KEYS == {"token_map"}
    assert body["verdict"] in ("fake", "genuine")
    assert 0.0 <= body["fake_probability"] <= 1.0
    assert body["model_used"] in ("nb", "svm")
    if choice == "best":
        metrics = client.get("/api/models").json()
        assert body["model_used"] == metrics["best_model"]
    else:
        assert body["model_used"] == choice
    assert set(body["sentiment"]) == {"compound", "label", "pos", "neu", "neg"}
    assert body["sentiment"]["label"] in ("Positive", "Mixed", "Negative")
    assert set(body["meta"]) == {"words", "exclamations", "caps_words"}
    assert len(body["tokens"]) <= 8
    for token in body["tokens"]:
        assert set(token) == {"token", "score", "direction"}
        assert token["direction"] in ("fake", "genuine")
    for flag in body["flags"]:
        assert set(flag) == {"code", "label", "severity"}
        assert flag["severity"] in ("low", "medium", "high")
    assert isinstance(body["id"], int) and body["id"] > 0
    assert body["latency_ms"] >= 1
    assert "T" in body["created_at"]


def test_predict_promotional_review_is_flagged_fake(client):
    body = client.post("/api/predict", json={"review": FAKE_REVIEW}).json()
    assert body["verdict"] == "fake"
    assert body["fake_probability"] > 0.5
    codes = {flag["code"] for flag in body["flags"]}
    assert "PROMOTIONAL_LANGUAGE" in codes


def test_predict_detailed_review_is_less_suspicious(client):
    promo = client.post("/api/predict", json={"review": FAKE_REVIEW, "model": "nb"}).json()
    detailed = client.post("/api/predict", json={"review": GENUINE_REVIEW, "model": "nb"}).json()
    assert detailed["fake_probability"] < promo["fake_probability"]


def test_predict_with_rating_surfaces_mismatch_flag(client):
    body = client.post(
        "/api/predict",
        json={"review": "The staff were excellent and the suite was beautiful.", "rating": 1},
    ).json()
    assert any(flag["code"] == "RATING_SENTIMENT_MISMATCH" for flag in body["flags"])


def test_predict_saves_to_history(client):
    first = client.post("/api/predict", json={"review": FAKE_REVIEW}).json()
    listing = client.get("/api/history").json()
    assert listing["total"] == 1
    entry = listing["entries"][0]
    assert entry["id"] == first["id"]
    assert entry["review_text"] == FAKE_REVIEW
    assert entry["verdict"] == first["verdict"]
    assert json.loads(entry["tokens_json"]) == first["tokens"]
    assert json.loads(entry["flags_json"]) == first["flags"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"review": ""},
        {"review": "    "},
        {"review": "a" * 5001},
        {"review": "short", "rating": 0},
        {"review": "short", "rating": 6},
        {"review": "short", "model": "random-forest"},
        {"review": "short", "unexpected": 1},
        {"review": 42},
    ],
)
def test_predict_validation_errors(client, payload):
    assert_error(
        client.post("/api/predict", json=payload), "VALIDATION_ERROR", 422
    )


def test_predict_requires_json_body(client):
    response = client.post(
        "/api/predict", content="not json", headers={"Content-Type": "text/plain"}
    )
    assert response.status_code in (400, 415, 422)
    assert "Traceback" not in response.text


# -------------------------------------------------------------- batch ------
def test_batch_happy_path(client):
    csv_text = "review,rating\n" + '"Excellent perfect stay, highly recommend!!",5\n' + (
        '"Room 12 was dusty but the manager fixed it on day 2",'
        "3\n"
    )
    response = client.post("/api/predict/batch", files=upload(csv_text))
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"rows", "summary"}
    assert len(body["rows"]) == 2
    for row in body["rows"]:
        assert set(row) == BATCH_ROW_KEYS
        assert row["verdict"] in ("fake", "genuine")
    assert body["rows"][0]["row"] == 1
    assert body["rows"][1]["row"] == 2
    assert body["rows"][1]["rating"] == 3
    summary = body["summary"]
    assert set(summary) == {"total", "fake_count", "fake_percent", "avg_confidence"}
    assert summary["total"] == 2
    assert summary["fake_count"] == sum(1 for r in body["rows"] if r["verdict"] == "fake")
    assert abs(summary["fake_percent"] - 100.0 * summary["fake_count"] / 2) < 1e-6
    assert 0.0 <= summary["avg_confidence"] <= 1.0


def test_batch_csv_format(client):
    csv_text = 'review\n"Excellent perfect stay, highly recommend!!"\n'
    response = client.post("/api/predict/batch?format=csv", files=upload(csv_text))
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0] == "row,review,rating,verdict,fake_probability,confidence,sentiment_label"
    assert len(lines) == 2


def test_batch_uses_a_real_model_choice(client):
    csv_text = "review\nnice hotel with a great view and clean pool\n"
    nb = client.post("/api/predict/batch?model=nb", files=upload(csv_text)).json()
    svm = client.post("/api/predict/batch?model=svm", files=upload(csv_text)).json()
    assert nb["rows"][0]["verdict"] in ("fake", "genuine")
    assert svm["rows"][0]["verdict"] in ("fake", "genuine")
    unknown = client.post("/api/predict/batch?model=nope", files=upload(csv_text))
    assert_error(unknown, "INVALID_MODEL", 400)


def test_batch_missing_review_column(client):
    assert_error(
        client.post("/api/predict/batch", files=upload("text,stars\nfoo,5\n")),
        "CSV_MISSING_COLUMN",
        400,
    )


def test_batch_empty_file(client):
    assert_error(
        client.post("/api/predict/batch", files=upload("")), "CSV_EMPTY", 400
    )


def test_batch_header_only(client):
    assert_error(
        client.post("/api/predict/batch", files=upload("review\n")),
        "CSV_NO_ROWS",
        400,
    )


def test_batch_blank_review_cell(client):
    assert_error(
        client.post(
            "/api/predict/batch", files=upload('review,rating\nnice hotel,\n,4\n')
        ),
        "CSV_EMPTY_REVIEW",
        400,
    )


def test_batch_invalid_rating(client):
    assert_error(
        client.post(
            "/api/predict/batch", files=upload("review,rating\nnice hotel,9\n")
        ),
        "CSV_INVALID_RATING",
        400,
    )


def test_batch_unreadable_csv(client):
    assert_error(
        client.post(
            "/api/predict/batch", files=upload('review\n"unterminated quote\n')
        ),
        "CSV_UNREADABLE",
        400,
    )


def test_batch_row_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "max_batch_rows", 4)
    csv_text = "review\n" + "\n".join(f"hotel number {i} was clean" for i in range(6)) + "\n"
    assert_error(
        client.post("/api/predict/batch", files=upload(csv_text)),
        "CSV_TOO_MANY_ROWS",
        413,
    )


def test_batch_size_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "max_batch_bytes", 64)
    csv_text = "review\n" + "\n".join("a" * 40 for _ in range(10)) + "\n"
    assert_error(
        client.post("/api/predict/batch", files=upload(csv_text)),
        "CSV_TOO_LARGE",
        413,
    )


def test_batch_hundreds_of_rows_is_vectorised(client):
    import time

    csv_text = "review\n" + "\n".join(
        f"Hotel stay {i}: the room was clean but the wifi failed twice" for i in range(300)
    )
    started = time.perf_counter()
    response = client.post("/api/predict/batch", files=upload(csv_text))
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    assert response.json()["summary"]["total"] == 300
    assert elapsed < 10.0, f"300 rows took {elapsed:.1f}s"


# ------------------------------------------------------------- history -----
def seed(client, count: int, text_factory=lambda index: f"seed review number {index}"):
    for index in range(count):
        client.post("/api/predict", json={"review": text_factory(index)})


def test_history_empty_by_default(client):
    body = client.get("/api/history").json()
    assert body == {"total": 0, "entries": [], "items": []}


def test_history_lists_entries_newest_first(client):
    seed(client, 3, lambda index: f"Distinctive marker {index} hotel review")
    body = client.get("/api/history").json()
    assert body["total"] == 3
    assert len(body["entries"]) == 3
    assert [entry["id"] for entry in body["entries"]] == sorted(
        (entry["id"] for entry in body["entries"]), reverse=True
    )


def test_history_search_and_verdict_filters(client):
    client.post("/api/predict", json={"review": FAKE_REVIEW})
    client.post("/api/predict", json={"review": GENUINE_REVIEW})
    searched = client.get("/api/history", params={"search": "manager"}).json()
    assert searched["total"] == 1
    assert "manager" in searched["entries"][0]["review_text"]

    verdict = client.get("/api/history", params={"verdict": "fake"}).json()
    assert all(entry["verdict"] == "fake" for entry in verdict["entries"])
    assert verdict["total"] >= 1

    both = client.get(
        "/api/history", params={"search": "AMAZING", "verdict": "genuine"}
    ).json()
    assert both["total"] == 0
    assert both["entries"] == []


def test_history_paging(client):
    seed(client, 5, lambda index: f"paged review {index} about a hotel")
    page_one = client.get("/api/history", params={"limit": 2, "offset": 0}).json()
    page_two = client.get("/api/history", params={"limit": 2, "offset": 2}).json()
    assert page_one["total"] == 5 and page_two["total"] == 5
    assert len(page_one["entries"]) == 2 and len(page_two["entries"]) == 2
    ids_one = {entry["id"] for entry in page_one["entries"]}
    ids_two = {entry["id"] for entry in page_two["entries"]}
    assert ids_one.isdisjoint(ids_two)


def test_history_invalid_verdict_and_limit(client):
    assert_error(
        client.get("/api/history", params={"verdict": "suspicious"}),
        "INVALID_VERDICT",
        400,
    )
    response = client.get("/api/history", params={"limit": 0})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_history_delete_one(client):
    created = client.post("/api/predict", json={"review": FAKE_REVIEW}).json()
    other = client.post("/api/predict", json={"review": GENUINE_REVIEW}).json()
    response = client.delete(f"/api/history/{created['id']}")
    assert response.status_code == 200
    assert response.json() == {"deleted": 1, "id": created["id"]}
    listing = client.get("/api/history").json()
    assert listing["total"] == 1
    assert listing["entries"][0]["id"] == other["id"]


def test_history_delete_missing_id(client):
    assert_error(client.delete("/api/history/424242"), "HISTORY_NOT_FOUND", 404)


def test_history_clear_all(client):
    seed(client, 3, lambda index: f"review to clear {index}")
    response = client.delete("/api/history")
    assert response.status_code == 200
    assert response.json() == {"deleted": 3}
    body = client.get("/api/history").json()
    assert body["total"] == 0 and body["entries"] == []


# ---------------------------------------------------------- robustness -----
def test_rate_limit_returns_envelope(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    reset_rate_limiter()
    responses = [client.get("/api/health") for _ in range(4)]
    assert [r.status_code for r in responses[:3]] == [200, 200, 200]
    assert_error(responses[3], "RATE_LIMITED", 429)


def test_responses_never_leak_stack_traces(client):
    broken = client.post(
        "/api/predict", json={"review": "x" * 10, "model": "not-a-model"}
    )
    assert "Traceback" not in broken.text
    assert "File \"" not in broken.text


def test_cors_preflight_allows_the_frontend_origin(client):
    response = client.options(
        "/api/predict",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code in (200, 204)
