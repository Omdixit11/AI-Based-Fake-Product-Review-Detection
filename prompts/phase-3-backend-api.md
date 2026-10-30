# PHASE 3 PROMPT: Backend API (FastAPI)

> Give this ENTIRE file to your Antigravity agent. It is Phase 3 of 5. Read `README.md` and `docs/LLD.md` first.

---

## 0. TEAM CONTEXT (read first, these rules override anything below)

- This is the **TruthLens** monorepo. The folder skeleton already exists. Do NOT recreate the structure; fill in only your phase.
- Five people work in strict order. You do **ONLY Phase 3**. Earlier phases are finished and already in git. Do not rewrite or "improve" their work.
- **PROTECTED files, never edit:** README.md, docs/HLD.md, docs/LLD.md, docs/PROJECT_STRUCTURE.md, everything in prompts/, everything in .githooks/, scripts/check_phase.py, scripts/protected.sha256. A git pre-commit hook blocks commits that touch them.
- **You MAY create or change:** `backend/app/**`, `backend/tests/test_api.py`, `backend/tests/test_services.py`. Append-only changes to `backend/requirements.txt` if truly needed.
- **You must NOT change:** `frontend/`, `backend/ml/`, `backend/models/` (read only), `Makefile`, `.env.example`, `docs/`, and the protected files. If you find a REAL bug in `backend/ml/`, do not fix it silently: stop and tell me.
- Never use `git push --force`. Never commit secrets, `node_modules`, `.venv`, or the raw dataset.

### 0.1 Start checklist (run these first)

```bash
git checkout main
git pull origin main --tags
git config core.hooksPath .githooks
python scripts/check_phase.py --ready 3
git checkout -b phase-3-backend
```
If `check_phase.py --ready 3` prints NOT READY, **stop and tell me**. Do not try to fix earlier phases.

### 0.2 Adjustments for this repo (these override anything below that conflicts)

1. The trained artifacts and `metrics.json` are already in `backend/models/` (committed by Phase 2). You do NOT need the dataset and must not retrain.
2. Run everything from `backend/`: `cd backend && uvicorn app.main:app --reload --port 8000`. Tests: `cd backend && python -m pytest tests -q`. `pytest.ini` already sets `pythonpath = .`, so `from ml.preprocess import clean_text` works.
3. Before anything else run `python scripts/download_nltk.py` (VADER and WordNet data). Tests must not need internet after that.
4. SQLite path comes from env `DATABASE_URL` (default `sqlite:///./history.db`). The `.db` file is git-ignored.
5. Use the exact file names from the folder structure below (a checker script looks for them): `app/{main,config,schemas}.py`, `app/routers/{predict,models,history,health}.py`, `app/services/{predictor,explain,flags,sentiment}.py`, `app/db/{database,models}.py`, and the tests `test_api.py` and `test_services.py`.
6. The API contract in `docs/LLD.md` is the single source of truth. The frontend was already built against it with mock data. Do not rename fields.

---

---

## 1. GOAL

In the monorepo `truthlens/`, build the **FastAPI backend** in `backend/app/` that serves the trained fake-review models to a separate Next.js frontend. The API contract below is strict because the frontend is already built against it.

Stack: Python 3.11, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy + SQLite, scikit-learn, NLTK VADER, joblib, pandas, python-multipart, pytest + httpx.

---

## 2. FILES TO CREATE

```
backend/app/
├── main.py             # app, CORS, lifespan startup (load models once)
├── config.py           # paths, FAKE_LABEL, limits, CORS origins from env
├── schemas.py          # Pydantic models
├── routers/ (predict.py, models.py, history.py, health.py)
├── services/
│   ├── predictor.py    # singleton: load artifacts, predict
│   ├── explain.py      # top contributing tokens
│   ├── flags.py        # rule-based red flags
│   └── sentiment.py    # VADER
└── db/ (database.py, models.py)
backend/tests/ (test_api.py, test_services.py)
```

---

## 3. CRITICAL RULE

**Import `clean_text` and `build_features` from `backend/ml/`. Never re-implement preprocessing or feature logic in the API.** Training and inference must be identical. Add a test that proves the API uses the same function objects as the ML package.

---

## 4. ENDPOINTS (strict contract)

**POST `/api/predict`**
Request: `{ "review": string (1-5000 chars, required), "rating": int 1-5 (optional), "model": "best" | "nb" | "svm" (default "best") }`
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
Each successful prediction is saved to history.

**POST `/api/predict/batch`**: multipart CSV, required column `review`, optional `rating`. Max 5,000 rows and 5 MB. Returns `{ "rows": [...same fields minus tokens...], "summary": { "total", "fake_count", "fake_percent", "avg_confidence" } }`. Also support `?format=csv` to return a downloadable CSV. Use vectorized batch prediction, not a per-row loop, so 1,000 rows finish in under 10 seconds.

**GET `/api/models`**: list of available models and which is the default "best".
**GET `/api/models/metrics`**: return `models/metrics.json` as is.
**GET `/api/history?search=&verdict=&limit=&offset=`**: items plus `total`.
**DELETE `/api/history/{id}`** and **DELETE `/api/history`** (clear all).
**GET `/api/health`**: `{ "status": "ok", "models_loaded": true, "version": "1.0.0" }`.

Errors always use `{ "error": { "code": "string", "message": "string" } }` with correct HTTP status codes. Never expose stack traces.

---

## 5. SERVICE DETAILS

**predictor.py**
- Load all artifacts once at startup (FastAPI lifespan). If a file is missing, fail fast with a clear message saying which file and which command (`python -m ml.run_pipeline`) creates it.
- Use the `active_feature_set` and `best_model` from `metrics.json`. `model="best"` resolves to `best_model`.
- Map the fake probability using `model.classes_` and `FAKE_LABEL` from config, never a hard-coded index.
- Target under 100 ms per single review.

**explain.py**
- Naive Bayes: token score = `feature_log_prob_[fake] - feature_log_prob_[genuine]` for tokens present in the review.
- SVM: use the coefficients of `svm_linear_base.pkl` for tokens present.
- Return the top 8 tokens by absolute score with `direction`, and also return enough info to map tokens back to the original words (original word to cleaned token) so the frontend can highlight them.

**flags.py** (rule-based, each with severity): very short review, 3+ exclamation marks, 2+ ALL CAPS words, 3+ promotional phrases (best, perfect, must buy, life changing, highly recommend, five stars), no concrete details (no digits and no contrast words like but/however/after), extreme one-sided sentiment in a short text, and rating vs sentiment mismatch when `rating` is given.

**sentiment.py**: VADER scores and label (Positive at 0.2 or above, Negative at -0.2 or below, else Mixed).

**Database**: table `history` with `id, review_text, verdict, fake_probability, model_used, compound, flags_json, tokens_json, created_at`.

---

## 6. SECURITY AND ROBUSTNESS

- Validate lengths and CSV size/rows. Sanitize CSV parsing errors into friendly messages.
- CORS allow-list read from env `CORS_ORIGINS` (default `http://localhost:3000`).
- No secrets in code. Add simple per-IP rate limiting if easy, otherwise note it as a future item.
- Logging: structured, one line per request with latency.

---

## 7. TESTS

- Happy path and validation errors for every endpoint.
- `model="nb"` and `model="svm"` both work and `model_used` matches.
- Label mapping test with a swapped `FAKE_LABEL`.
- Batch CSV with missing column, empty file, and too many rows.
- History create, list with filters, delete, clear.
- Parity test from section 3.

---

## 8. RULES

1. No mock responses, hard-coded predictions or fake data anywhere.
2. Do not modify files in `backend/ml/` unless you find a real bug, and tell me if you do.
3. When done, run the server, call every endpoint with curl, and show me the real outputs. Also run `pytest` and show the result.

Start with a 8-line plan and list assumptions.

---

## FINISH CHECKLIST (every item must be true before you hand off)

- `cd backend && python -m pytest tests -q` passes (all of `test_ml.py`, `test_api.py`, `test_services.py`).
- The server starts with `uvicorn app.main:app --port 8000` using the committed artifacts.
- You called EVERY endpoint with curl and showed me real output: predict (nb, svm, best), batch (good CSV and bad CSV), models, metrics, history (list, filter, delete, clear), health.
- Predictions import `clean_text` and `build_features` from `backend/ml` (parity test passes).
- `python scripts/check_phase.py 3` prints **OK. All checks passed.**
- `git status` shows no changes to protected files (README.md, docs/HLD.md, docs/LLD.md, prompts/, scripts/check_phase.py).

## GIT HAND-OFF (run exactly, in this order)

```bash
git add -A
git commit -m "phase 3: FastAPI backend"
git checkout main
git pull origin main
git merge --no-ff phase-3-backend -m "Merge phase 3"
python scripts/check_phase.py 3
git push origin main
git tag phase-3-complete
git push origin phase-3-complete
```
If the push is rejected, do NOT force push. Run `git pull --rebase origin main`, re-run the check, and push again. If there is a conflict you cannot resolve safely, stop and ask me.

When done, tell me: the final commit hash, a 5-line summary of what you built, and anything unfinished.
