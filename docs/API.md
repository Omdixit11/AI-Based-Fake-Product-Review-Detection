# TruthLens REST API Reference

The TruthLens API is a FastAPI service designed for deceptive review detection, linguistic explainability, and review forensics.

- **Base URL:** `http://localhost:8000`
- **Interactive Documentation (Swagger / OpenAPI):** `http://localhost:8000/docs`
- **Alternative Specification (ReDoc):** `http://localhost:8000/redoc`
- **API Version:** `1.0.0`

> [!NOTE]
> **Dataset Domain Context:**  
> TruthLens targets product review analysis. However, its offline trained models and empirical benchmarks are evaluated on the **Deceptive Opinion Spam Corpus (Ott et al., 2011)**, consisting of 1,596 English hotel reviews. While feature extractors and heuristics are designed for general consumer review texts, performance on retail consumer products (e.g. electronics, apparel, home goods) has not been established by this dataset and may exhibit domain shift without retraining or domain adaptation.

---

## 1. Request Limits & Runtime Configuration

The API enforces strict limits on inputs to ensure deterministic performance, bounded memory usage, and resilience against abusive traffic. All default thresholds are defined in `backend/app/config.py` and can be overridden via environment variables.

| Setting / Limit | Default Value | Environment Variable | Scope & Description |
| :--- | :--- | :--- | :--- |
| **Review Length** | 1 to 5,000 characters | `MAX_REVIEW_CHARS` | Minimum 1 char; maximum 5,000 chars for `/api/predict` and `/api/explain`. Reviews exceeding this limit trigger a `422 VALIDATION_ERROR`. |
| **Batch CSV Size** | 5 MiB (5,242,880 bytes) | `MAX_BATCH_BYTES` | Maximum uploaded file size for `/api/predict/batch`. Uploads exceeding 5 MiB return `413 PAYLOAD_TOO_LARGE`. |
| **Batch CSV Rows** | 5,000 data rows | `MAX_BATCH_ROWS` | Maximum rows in a batch upload. CSV files with > 5,000 rows return `413 PAYLOAD_TOO_LARGE`. |
| **Star Rating** | 1 to 5 | `MIN_RATING` / `MAX_RATING` | Rating scale (whole integers 1–5). Invalid ratings trigger `422 VALIDATION_ERROR` (single) or `400 BAD_REQUEST` (batch). |
| **Prediction Tokens** | 8 tokens | `MAX_TOKENS` | Maximum top contributing tokens returned in `POST /api/predict`. |
| **Explanation Tokens** | 10 tokens | Fixed constant (`TOP_TOKENS`) | Maximum top contributing tokens returned in `POST /api/explain`. |
| **Rate Limit** | 300 req / min per IP | `RATE_LIMIT_PER_MINUTE` | Per-client IP sliding window rate limit on `/api` routes (except HTTP `OPTIONS`). Setting `0` disables rate limiting. Exceeding triggers `429 RATE_LIMITED`. |
| **History Default Limit** | 50 records | `HISTORY_DEFAULT_LIMIT` | Default page size for `GET /api/history` when `limit` query param is omitted. |
| **History Max Limit** | 500 records | `HISTORY_MAX_LIMIT` | Upper bound for `limit` query param on `GET /api/history`. Values > 500 are capped at 500. |
| **CORS Origins** | `http://localhost:3000` | `CORS_ORIGINS` | Comma-separated list of allowed browser origins for cross-origin resource sharing. |
| **Database URL** | `sqlite:///./history.db` | `DATABASE_URL` | SQLAlchemy connection string for SQLite analysis history persistence. |
| **Tier-1 Rules Switch** | `true` | `ENABLE_TIER1` | Enables pre-model deterministic rules (`VELOCITY_EXCEEDED`, `DUPLICATE_FLOOD`, etc.). |
| **Sarcasm Switch** | `true` | `ENABLE_SARCASM` | Enables post-model heuristic sarcasm contrast analysis. |
| **SHAP Explainer Switch** | `true` | `ENABLE_SHAP` | Enables on-demand SHAP calculation in `POST /api/explain` when the optional `shap` package is present. |

---

## 2. Unified Error Envelope

All error responses strictly adhere to a consistent JSON error envelope across all status codes:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "review: 'review' must be a non-empty string (1-5000 characters)."
  }
}
```

### HTTP Status Codes & Error Code Mapping

The API uses specific HTTP status codes and standardized error codes. Not every error code applies to every endpoint:

| Status Code | Standard Error Code | Typical Causes | Endpoints |
| :--- | :--- | :--- | :--- |
| **400 Bad Request** | `BAD_REQUEST`<br>`INVALID_MODEL`<br>`INVALID_FORMAT`<br>`INVALID_VERDICT`<br>`CSV_EMPTY`<br>`CSV_UNREADABLE`<br>`CSV_MISSING_COLUMN`<br>`CSV_NO_ROWS`<br>`CSV_EMPTY_REVIEW`<br>`CSV_REVIEW_TOO_LONG`<br>`CSV_INVALID_RATING`<br>`CSV_INVALID_POSTED_AT` | - Unknown model parameter (e.g. `model="xgboost"`).<br>- Invalid batch format parameter (not `json` or `csv`).<br>- Invalid history verdict filter (not `fake` or `genuine`).<br>- Malformed, empty, or unparseable CSV upload.<br>- Missing required `review` column in CSV.<br>- CSV contains empty reviews, rows > 5,000 chars, invalid ratings, or invalid timestamps. | `/api/predict`<br>`/api/predict/batch`<br>`/api/explain`<br>`/api/history` |
| **404 Not Found** | `NOT_FOUND`<br>`HISTORY_NOT_FOUND` | - History record with the requested integer ID does not exist in SQLite.<br>- Non-existent URL route requested. | `/api/history/{id}`<br>All routes |
| **405 Method Not Allowed** | `METHOD_NOT_ALLOWED` | - HTTP verb not supported on the target path (e.g. `POST /api/history`). | All routes |
| **413 Payload Too Large** | `PAYLOAD_TOO_LARGE`<br>`CSV_TOO_LARGE`<br>`CSV_TOO_MANY_ROWS` | - Uploaded CSV exceeds 5 MiB (5,242,880 bytes).<br>- Uploaded CSV contains more than 5,000 data rows. | `/api/predict/batch` |
| **422 Validation Error** | `VALIDATION_ERROR` | - Single review text is missing, empty, or exceeds 5,000 characters.<br>- Rating is not an integer between 1 and 5.<br>- Malformed JSON request body or unrecognized extra keys in `metadata`.<br>- Negative pagination `offset` or `limit < 1`. | `/api/predict`<br>`/api/explain`<br>`/api/history` |
| **429 Too Many Requests** | `RATE_LIMITED` | - Client IP exceeded the configured rate limit (default: 300 requests/minute). | All `/api` routes (except OPTIONS) |
| **500 Internal Error** | `INTERNAL_ERROR` | - Unhandled server exception (internal tracebacks are suppressed from responses). | All routes |
| **503 Service Unavailable** | `MODELS_NOT_LOADED` | - Required machine learning model pickle files are missing or failed to load. | `/api/predict`<br>`/api/predict/batch`<br>`/api/explain`<br>`/api/models`<br>`/api/health` |

---

## 3. Endpoints Overview

| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Service status | Verifies API health, loaded models, and service version. |
| `GET` | `/api/models` | Model catalog | Returns available models, default classifier, and active feature set. |
| `GET` | `/api/models/metrics` | Model metrics | Serves the exact evaluation metrics from `backend/models/metrics.json`. |
| `POST` | `/api/predict` | Single review analysis | Classifies review, extracts sentiment, flags, and tokens (up to 8). |
| `POST` | `/api/predict/batch` | Bulk CSV analysis | Evaluates up to 5,000 reviews from an uploaded CSV (max 5 MiB). |
| `POST` | `/api/explain` | On-demand attribution | Detailed word attribution (up to 10 tokens) using Linear SVM companion model or Naive Bayes log-probabilities. |
| `GET` | `/api/history` | List analysis history | Paginated list of past analyses with filtering and dual `entries`/`items` keys. |
| `DELETE` | `/api/history/{id}` | Delete history entry | Deletes a single analysis record by ID from SQLite. |
| `DELETE` | `/api/history` | Clear history | Clears all stored analysis records. |

---

## 4. Detailed Endpoint Documentation

### 4.1 GET `/api/health`

Verifies service liveness, operational readiness, and confirms whether model artifacts are successfully initialized in memory.

#### Example Request:
```bash
curl -X GET http://localhost:8000/api/health
```

#### Real Response (200 OK):
```json
{
  "status": "ok",
  "models_loaded": true,
  "version": "1.0.0"
}
```

---

### 4.2 GET `/api/models`

Lists active classifiers, default selection, and the active feature engineering pipeline.

#### Example Request:
```bash
curl -X GET http://localhost:8000/api/models
```

#### Real Response (200 OK):
```json
{
  "models": [
    "nb",
    "svm"
  ],
  "default": "best",
  "best_model": "svm",
  "active_feature_set": "tfidf_only"
}
```

---

### 4.3 GET `/api/models/metrics`

Serves `backend/models/metrics.json` verbatim, detailing corpus metadata, train/test split sizes, confusion matrices, and ROC curves.

#### Example Request:
```bash
curl -X GET http://localhost:8000/api/models/metrics
```

#### Real Response (200 OK - Excerpt):
```json
{
  "generated_at": "2026-11-02T13:34:48.517691+00:00",
  "dataset": {
    "name": "Deceptive Opinion Spam Corpus (Ott et al., 2011)",
    "size": 1596,
    "train_size": 1276,
    "test_size": 320,
    "fake_percent": 50.1253,
    "avg_words": 148.718
  },
  "best_model": "svm",
  "active_feature_set": "tfidf_only",
  "models": {
    "nb": {
      "tfidf_only": {
        "accuracy": 0.8562,
        "precision": 0.8393,
        "recall": 0.8812,
        "f1": 0.8598,
        "roc_auc": 0.9325,
        "confusion_matrix": [
          [133, 27],
          [19, 141]
        ],
        "best_params": {
          "alpha": 0.1
        }
      }
    },
    "svm": {
      "tfidf_only": {
        "accuracy": 0.8875,
        "precision": 0.8605,
        "recall": 0.925,
        "f1": 0.8916,
        "roc_auc": 0.9432,
        "confusion_matrix": [
          [136, 24],
          [12, 148]
        ],
        "best_params": {
          "C": 3.0,
          "gamma": "scale",
          "kernel": "rbf"
        }
      }
    }
  }
}
```

---

### 4.4 POST `/api/predict`

Classifies a single review. Evaluates optional Tier-1 deterministic heuristics, executes model inference via Support Vector Machine (RBF kernel) or Multinomial Naive Bayes, performs VADER sentiment analysis, extracts up to 8 top contributing tokens, flags heuristic anomalies, and checks for sarcasm contrast.

#### Request Schema:
| Field | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `review` | `string` | **Yes** | — | Raw review text (1 to 5,000 characters). Must be non-empty. |
| `rating` | `integer` | No | `null` | Optional customer star rating (integer between 1 and 5). |
| `model` | `string` | No | `"best"` | Classifier choice: `"best"` (default), `"svm"`, or `"nb"`. |
| `metadata` | `object` | No | `null` | Optional Tier-1 behavioral context. Unrecognized extra keys are forbidden. |

#### Optional `metadata` Object Fields:
- `user_id` (`string`, optional): User identifier (non-blank, maximum 128 characters).
- `posted_at` (`string`, optional): ISO-8601 UTC timestamp string (e.g. `"2026-01-31T09:15:00Z"`).
- `reviews_last_minute` (`integer`, optional): Count of recent submissions (integer between 0 and 10,000).

#### Response Properties & Conditional Phase 3.5 Fields:
- **Core fields (always present):** `id`, `verdict` (`"fake"` or `"genuine"`), `fake_probability` (0.0 to 1.0), `confidence` (0.5 to 1.0), `model_used` (`"svm"`, `"nb"`, or `"tier1_rules"`), `sentiment`, `flags`, `tokens` (up to 8 tokens), `token_map`, `meta`, `latency_ms`, `created_at`.
- **Conditional fields (controlled by feature switches):**
  - `tier1` (`object`, conditional): Included when `ENABLE_TIER1=true`. Contains `triggered` (`boolean`), `action` (`"pass"` or `"flag_spam"`), and `rules` (array of triggered rules with `code`, `label`, `severity`, and `kind`: `"soft"` or `"hard"`).
  - `decision_source` (`string`, conditional): Included when `ENABLE_TIER1=true`. Indicates whether the verdict was determined by `"model"` or short-circuited by `"tier1_rules"`.
  - `sarcasm` (`object`, conditional): Included when `ENABLE_SARCASM=true`. Contains `suspected` (`boolean`) and `score` (contrast score 0.0 to 1.0). When suspected, also includes `risk_level` (`"high"`), `positive_cues` (`string[]`), and `negative_cues` (`string[]`).
- **Sarcasm Behavior:** Sarcasm analysis operates strictly as an informational risk signal for human moderation. It appends the `SARCASM_SUSPECTED` flag to `flags` when contrast thresholds are met, but **never mutates or overrides the underlying ML verdict or fake probability**.

#### Example Request (Standard Review Classification):
```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "review": "OMG this is the BEST product I have EVER bought! Absolutely AMAZING quality, my life is CHANGED forever! Buy it NOW, you will NOT regret it! Five stars!",
    "rating": 5,
    "model": "best"
  }'
```

#### Real Response (200 OK - Deceptive Review Detected):
```json
{
  "id": 101,
  "verdict": "fake",
  "fake_probability": 0.883528,
  "confidence": 0.883528,
  "model_used": "svm",
  "sentiment": {
    "compound": 0.9356,
    "label": "Positive",
    "pos": 0.356,
    "neu": 0.644,
    "neg": 0.0
  },
  "flags": [
    {
      "code": "EXCLAMATION_OVERLOAD",
      "label": "Repeated exclamation marks",
      "severity": "medium"
    },
    {
      "code": "ALL_CAPS",
      "label": "Words in ALL CAPS",
      "severity": "medium"
    },
    {
      "code": "NO_CONCRETE_DETAILS",
      "label": "No digits or contrast words",
      "severity": "medium"
    }
  ],
  "tokens": [
    {
      "token": "regret",
      "score": 0.1803,
      "direction": "fake"
    },
    {
      "token": "amaze",
      "score": 0.1662,
      "direction": "fake"
    },
    {
      "token": "buy",
      "score": -0.1579,
      "direction": "genuine"
    },
    {
      "token": "forever",
      "score": 0.1078,
      "direction": "fake"
    },
    {
      "token": "ever",
      "score": 0.0882,
      "direction": "fake"
    },
    {
      "token": "absolutely",
      "score": 0.0807,
      "direction": "fake"
    },
    {
      "token": "not regret",
      "score": 0.0805,
      "direction": "fake"
    },
    {
      "token": "star",
      "score": -0.0727,
      "direction": "genuine"
    }
  ],
  "meta": {
    "words": 28,
    "exclamations": 4,
    "caps_words": 7
  },
  "latency_ms": 20,
  "created_at": "2026-11-13T16:56:13.399090+00:00",
  "token_map": {
    "regret": ["regret"],
    "amaze": ["AMAZING"],
    "buy": ["bought", "Buy"],
    "forever": ["forever"],
    "ever": ["EVER"],
    "absolutely": ["Absolutely"],
    "not regret": ["NOT", "regret"],
    "star": ["stars"]
  },
  "tier1": {
    "triggered": false,
    "action": "pass",
    "rules": []
  },
  "sarcasm": {
    "suspected": false,
    "score": 0.0
  },
  "decision_source": "model"
}
```

#### Example Request (Tier-1 Hard Rule Short-Circuit):
When a hard rule fires (e.g. `VELOCITY_EXCEEDED` or `DUPLICATE_FLOOD`), ML inference is bypassed:
```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "review": "Clean and quiet stay with fast check-in.",
    "metadata": {
      "user_id": "bot-user-42",
      "reviews_last_minute": 9
    }
  }'
```

#### Real Response (200 OK - Short-Circuited by Tier-1):
```json
{
  "id": 104,
  "verdict": "fake",
  "fake_probability": 1.0,
  "confidence": 1.0,
  "model_used": "tier1_rules",
  "sentiment": {
    "compound": 0.4019,
    "label": "Positive",
    "pos": 0.252,
    "neu": 0.748,
    "neg": 0.0
  },
  "flags": [
    {
      "code": "NO_CONCRETE_DETAILS",
      "label": "No digits or contrast words",
      "severity": "medium"
    },
    {
      "code": "SHORT_REVIEW",
      "label": "Unusually short review",
      "severity": "low"
    }
  ],
  "tokens": [],
  "meta": {
    "words": 8,
    "exclamations": 0,
    "caps_words": 0
  },
  "latency_ms": 1,
  "created_at": "2026-11-13T16:56:13.442921+00:00",
  "token_map": {},
  "tier1": {
    "triggered": true,
    "action": "flag_spam",
    "rules": [
      {
        "code": "VELOCITY_EXCEEDED",
        "label": "Too many reviews from this user in the last minute",
        "severity": "high",
        "kind": "hard"
      }
    ]
  },
  "sarcasm": {
    "suspected": false,
    "score": 0.0
  },
  "decision_source": "tier1_rules"
}
```

---

### 4.5 POST `/api/predict/batch`

Analyzes reviews in bulk from an uploaded CSV file. Processes up to 5,000 reviews with a 5 MiB file size ceiling.

#### Upload Constraints & Limits:
- **Maximum File Size:** 5 MiB / 5,242,880 bytes (`MAX_BATCH_BYTES`). Files larger than 5 MiB return `413 PAYLOAD_TOO_LARGE` (`CSV_TOO_LARGE`).
- **Maximum Row Count:** 5,000 data rows (`MAX_BATCH_ROWS`). CSV files with > 5,000 rows return `413 PAYLOAD_TOO_LARGE` (`CSV_TOO_MANY_ROWS`).
- **Required CSV Column:** `review` (case-insensitive header). Missing `review` column returns `400 BAD_REQUEST` (`CSV_MISSING_COLUMN`).
- **Optional CSV Columns:**
  - `rating`: Customer rating (integer 1 to 5). Bad ratings return `400 BAD_REQUEST` (`CSV_INVALID_RATING`).
  - `user_id`: User identifier (string <= 128 chars) for per-upload Tier-1 tracking.
  - `posted_at`: ISO-8601 timestamp string (e.g. `"2026-01-31T09:15:00Z"`). Bad formats return `400 BAD_REQUEST` (`CSV_INVALID_POSTED_AT`).
- **Query Parameters:**
  - `model` (`string`, optional, default: `"best"`): Model to use (`"best"`, `"svm"`, or `"nb"`).
  - `format` (`string`, optional, default: `"json"`): Output format (`"json"` or `"csv"`). Invalid formats return `400 BAD_REQUEST` (`INVALID_FORMAT`).

#### Example CSV Input (`sample.csv`):
```csv
review,rating,user_id,posted_at
"OMG best hotel ever highly recommended!",5,user-101,2026-02-01T10:00:00Z
"Terrible service dirty sheets never coming back.",1,user-102,2026-02-01T10:05:00Z
```

#### Example Request:
```bash
curl -X POST "http://localhost:8000/api/predict/batch?model=best&format=json" \
  -F "file=@sample.csv"
```

#### Real Response (200 OK - JSON Format):
```json
{
  "rows": [
    {
      "row": 1,
      "review": "OMG best hotel ever highly recommended!",
      "rating": 5,
      "verdict": "fake",
      "fake_probability": 0.964489,
      "confidence": 0.964489,
      "sentiment_label": "Positive"
    },
    {
      "row": 2,
      "review": "Terrible service dirty sheets never coming back.",
      "rating": 1,
      "verdict": "fake",
      "fake_probability": 0.919897,
      "confidence": 0.919897,
      "sentiment_label": "Negative"
    }
  ],
  "summary": {
    "total": 2,
    "fake_count": 2,
    "fake_percent": 100.0,
    "avg_confidence": 0.9422
  }
}
```

#### CSV Output Mode (`format=csv`):
When `format=csv` is requested, the endpoint returns a `text/csv` stream with header:
```csv
row,review,rating,verdict,fake_probability,confidence,sentiment_label
1,"OMG best hotel ever highly recommended!",5,fake,0.964489,0.964489,Positive
2,"Terrible service dirty sheets never coming back.",1,fake,0.919897,0.919897,Negative
```

---

### 4.6 POST `/api/explain` (On-Demand Attribution)

Provides granular word-level feature attributions for an input review, returning **up to 10 tokens** (compared to the 8 tokens returned by `/api/predict`).

#### Model Attribution Mechanics:
- **Production SVM vs. Auxiliary Linear SVM:**  
  The production classifier deployed for inference is a **Support Vector Machine with RBF kernel** (`{"kernel": "rbf", "C": 3.0, "gamma": "scale"}`). Because RBF kernels map inputs into non-linear dual space, they do not possess a single vector of direct linear feature weights.  
  To provide transparent, rapid token attributions, the explanation service evaluates an auxiliary **Linear SVM companion model** (`svm_linear_base.pkl`, trained with `LinearSVC(C=1.0)`).  
  **Token attributions for SVM reflect the linear feature weights of this auxiliary companion model and are not an exact mathematical representation of the production RBF decision boundary.**
- **Attribution Methods (`method`):**
  - `"shap-linear"`: Returned when the optional `shap` library is installed and `ENABLE_SHAP=true`, computing Shapley values via `shap.LinearExplainer` against an all-zero TF-IDF baseline.
  - `"linear-coefficients"`: Returned when `shap` is absent or `ENABLE_SHAP=false`. Evaluates direct linear contributions `coef[j] * x[j]`, which is mathematically identical to `LinearExplainer` on an all-zero background.
  - `"naive-bayes-logprob"`: Returned for Naive Bayes. Computes token log-odds differences: `feature_log_prob_[fake] - feature_log_prob_[genuine]` scaled by term frequency. **Naive Bayes log-probability differences are never described as SHAP.**

#### Request Schema:
| Field | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `review` | `string` | **Yes** | — | Review text to explain (1 to 5,000 characters). |
| `model` | `string` | No | `"best"` | `"best"`, `"svm"`, or `"nb"`. |

#### Example Request:
```bash
curl -X POST http://localhost:8000/api/explain \
  -H "Content-Type: application/json" \
  -d '{
    "review": "Wow, best phone ever, total garbage, the screen broke in a day",
    "model": "svm"
  }'
```

#### Real Response (200 OK):
```json
{
  "method": "linear-coefficients",
  "model_used": "svm",
  "base_value": -0.138762,
  "tokens": [
    {
      "token": "ever",
      "score": 0.1485,
      "direction": "fake"
    },
    {
      "token": "phone",
      "score": -0.1355,
      "direction": "genuine"
    },
    {
      "token": "garbage",
      "score": 0.0999,
      "direction": "fake"
    },
    {
      "token": "screen",
      "score": 0.0912,
      "direction": "fake"
    },
    {
      "token": "day",
      "score": -0.0818,
      "direction": "genuine"
    },
    {
      "token": "total",
      "score": -0.0732,
      "direction": "genuine"
    },
    {
      "token": "break",
      "score": -0.0512,
      "direction": "genuine"
    },
    {
      "token": "best",
      "score": -0.026,
      "direction": "genuine"
    },
    {
      "token": "wow",
      "score": -0.0094,
      "direction": "genuine"
    }
  ],
  "token_map": {
    "ever": ["ever"],
    "phone": ["phone"],
    "garbage": ["garbage"],
    "screen": ["screen"],
    "day": ["day"],
    "total": ["total"],
    "break": ["broke"],
    "best": ["best"],
    "wow": ["Wow"]
  },
  "latency_ms": 4
}
```

---

### 4.7 GET `/api/history`

Retrieves analysis history from SQLite storage with support for text search, verdict filtering, and pagination.

#### Dual Response Structure:
The response includes both `entries` and `items` keys containing the **identical array of records**. `entries` is consumed by the frontend client, while `items` maintains conformance with the Phase 3 API specification.

#### Query Parameters:
- `search` (`string`, optional): Case-insensitive review text substring query.
- `verdict` (`string`, optional): Filter by `"fake"` or `"genuine"`. Invalid values return `400 BAD_REQUEST` (`INVALID_VERDICT`).
- `limit` (`integer`, optional, default: 50, maximum: 500): Number of records per page. Values > 500 are capped at 500.
- `offset` (`integer`, optional, default: 0): Records to skip for pagination.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/api/history?limit=1&verdict=fake"
```

#### Real Response (200 OK):
```json
{
  "total": 48,
  "entries": [
    {
      "id": 104,
      "review_text": "Clean and quiet stay with fast check-in.",
      "verdict": "fake",
      "fake_probability": 1.0,
      "model_used": "tier1_rules",
      "compound": 0.4019,
      "flags_json": "[{\"code\": \"NO_CONCRETE_DETAILS\", \"label\": \"No digits or contrast words\", \"severity\": \"medium\"}, {\"code\": \"SHORT_REVIEW\", \"label\": \"Unusually short review\", \"severity\": \"low\"}]",
      "tokens_json": "[]",
      "created_at": "2026-11-13T16:56:13.442921+00:00"
    }
  ],
  "items": [
    {
      "id": 104,
      "review_text": "Clean and quiet stay with fast check-in.",
      "verdict": "fake",
      "fake_probability": 1.0,
      "model_used": "tier1_rules",
      "compound": 0.4019,
      "flags_json": "[{\"code\": \"NO_CONCRETE_DETAILS\", \"label\": \"No digits or contrast words\", \"severity\": \"medium\"}, {\"code\": \"SHORT_REVIEW\", \"label\": \"Unusually short review\", \"severity\": \"low\"}]",
      "tokens_json": "[]",
      "created_at": "2026-11-13T16:56:13.442921+00:00"
    }
  ]
}
```

---

### 4.8 DELETE `/api/history/{entry_id}`

Deletes a single analysis record by ID from SQLite storage.

#### Example Request:
```bash
curl -X DELETE http://localhost:8000/api/history/104
```

#### Real Response (200 OK):
```json
{
  "deleted": 1,
  "id": 104
}
```

#### Error Response (404 Not Found):
When the requested record does not exist:
```json
{
  "error": {
    "code": "HISTORY_NOT_FOUND",
    "message": "No history entry with id 99999."
  }
}
```

---

### 4.9 DELETE `/api/history`

Deletes all stored analysis records from the SQLite database.

#### Example Request:
```bash
curl -X DELETE http://localhost:8000/api/history
```

#### Real Response (200 OK):
```json
{
  "deleted": 48
}
```
