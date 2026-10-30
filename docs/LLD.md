# Low-Level Design (LLD)

## 1. ML modules (`backend/ml/`)

| File | Responsibility |
|---|---|
| `config.py` | Paths, `FAKE_LABEL = 1`, `COLUMN_MAP`, `LABEL_MAP`, `RANDOM_STATE` |
| `preprocess.py` | `clean_text(text)`, `load_dataset(path)` |
| `features.py` | TF-IDF (1-2 grams), VADER, meta features, scaler, `build_features(...)` |
| `train_nb.py` | Multinomial NB, GridSearchCV on alpha |
| `train_svm.py` | SVM (linear/rbf) tuned on C, gamma, wrapped in `CalibratedClassifierCV` |
| `evaluate.py` | Metrics, confusion matrix, ROC, best-model selection, writes `metrics.json` |
| `run_pipeline.py` | One command: `python -m ml.run_pipeline` |

Artifacts written to `backend/models/`: `vectorizer.pkl`, `scaler.pkl`, `nb_model.pkl`, `svm_model.pkl`, `svm_linear_base.pkl`, `metrics.json`.

### metrics.json contract

```json
{
  "generated_at": "ISO-8601",
  "dataset": { "name": "", "size": 0, "train_size": 0, "test_size": 0, "fake_percent": 0.0, "avg_words": 0.0 },
  "best_model": "nb | svm",
  "active_feature_set": "tfidf_only | tfidf_sentiment",
  "models": {
    "nb":  { "tfidf_only": { "accuracy": 0, "precision": 0, "recall": 0, "f1": 0, "roc_auc": 0,
                              "confusion_matrix": [[0,0],[0,0]], "roc_curve": {"fpr": [], "tpr": []}, "best_params": {} },
             "tfidf_sentiment": { "...": "same keys" } },
    "svm": { "tfidf_only": { "...": "same keys" }, "tfidf_sentiment": { "...": "same keys" } }
  }
}
```
Confusion matrix layout is `[[TN, FP], [FN, TP]]`, where "positive" means fake. Floats rounded to 4 decimals.

## 2. Backend modules (`backend/app/`)

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, CORS, lifespan (load models once) |
| `config.py` | Paths, limits, `CORS_ORIGINS`, `DATABASE_URL` |
| `schemas.py` | Pydantic request/response models |
| `routers/predict.py` | `/api/predict`, `/api/predict/batch` |
| `routers/models.py` | `/api/models`, `/api/models/metrics` |
| `routers/history.py` | history list, delete, clear |
| `routers/health.py` | `/api/health` |
| `services/predictor.py` | Singleton: load artifacts, predict, probability |
| `services/explain.py` | Top contributing tokens (NB log-prob diff, SVM coefficients) |
| `services/flags.py` | Rule-based red flags |
| `services/sentiment.py` | VADER scores and label |
| `db/` | SQLAlchemy engine and `history` table |

## 3. API contract

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/predict` | Analyze one review |
| POST | `/api/predict/batch` | Analyze a CSV (max 5000 rows, 5 MB); `?format=csv` returns a CSV |
| GET | `/api/models` | Available models and default |
| GET | `/api/models/metrics` | Contents of `metrics.json` |
| GET | `/api/history` | List with `search`, `verdict`, `limit`, `offset` |
| DELETE | `/api/history/{id}` | Delete one entry |
| DELETE | `/api/history` | Clear all |
| GET | `/api/health` | `{status, models_loaded, version}` |

`POST /api/predict` request: `{ "review": "...", "rating": 1-5 (optional), "model": "best | nb | svm" }`

Response:
```json
{
  "id": 1, "verdict": "fake | genuine", "fake_probability": 0.87, "confidence": 0.87,
  "model_used": "svm",
  "sentiment": { "compound": 0.92, "label": "Positive | Mixed | Negative", "pos": 0.6, "neu": 0.4, "neg": 0.0 },
  "flags": [{ "code": "ALL_CAPS", "label": "Words in ALL CAPS", "severity": "low | medium | high" }],
  "tokens": [{ "token": "amazing", "score": 1.42, "direction": "fake | genuine" }],
  "meta": { "words": 14, "exclamations": 7, "caps_words": 3 },
  "latency_ms": 18, "created_at": "ISO-8601"
}
```
Errors always: `{ "error": { "code": "string", "message": "string" } }`.

## 4. Database

```mermaid
erDiagram
    HISTORY {
        int id PK
        text review_text
        string verdict
        float fake_probability
        string model_used
        float compound
        text flags_json
        text tokens_json
        datetime created_at
    }
```

## 5. Sequence: POST /api/predict

```mermaid
sequenceDiagram
    participant UI as Next.js
    participant API as FastAPI router
    participant PR as Predictor
    participant DB as SQLite
    UI->>API: POST /api/predict {review, rating, model}
    API->>PR: predict(text, rating, model)
    PR->>PR: clean_text, build_features, model.predict_proba
    PR->>PR: explain tokens, flags, VADER
    PR-->>API: PredictionResult
    API->>DB: insert history row
    API-->>UI: JSON response
```

## 6. Frontend component tree (`frontend/src/`)

```
app/            layout, page (landing), analyze, batch, model-lab, history, how-it-works
components/
  ui/           restyled primitives
  layout/       Navbar, Footer, ThemeToggle, StatusChip, CommandPalette
  analyzer/     ReviewInput, VerdictCard, ConfidenceGauge, HighlightedText,
                SentimentMeter, FlagList, ModelSwitch, TopTokens
  batch/        DropZone, ResultsTable, SummaryStats
  lab/          MetricCards, ConfusionMatrix, RocChart, ComparisonBars
  history/      HistoryList, HistoryFilters
lib/            api.ts (real client + switch), mockApi.ts, types.ts, utils.ts
```
