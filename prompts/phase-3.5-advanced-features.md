# PHASE 3.5 PROMPT: Advanced Features (Tier-1 filter, Sarcasm flag, SHAP explanations)

> Give this ENTIRE file to your Antigravity/Qoder agent. It runs AFTER Phase 3 and BEFORE Phase 4.
> Read `README.md`, `docs/LLD.md` and `prompts/phase-3-backend-api.md` first.

---

## 0. TEAM CONTEXT (these rules override anything below)

- Phases 1, 2 and 3 are finished, pushed and verified. **Your job is to ADD three optional features without breaking anything that already works.**
- **PROTECTED files, never edit:** README.md, docs/HLD.md, docs/LLD.md, docs/PROJECT_STRUCTURE.md, everything in `prompts/`, everything in `.githooks/`, `scripts/check_phase.py`, `scripts/protected.sha256`. The human owner updates README and docs later. A git hook blocks commits that touch them.
- **You must NOT change:** `backend/ml/`, `backend/models/` (never retrain, never re-run `python -m ml.run_pipeline`), `backend/requirements.txt`, `Makefile`, and **any existing test file** (`test_ml.py`, `test_api.py`, `test_services.py`).
- **You MAY create or change:**
  - Backend: `backend/app/**`, new test files named `backend/tests/test_advanced_*.py`, new file `backend/requirements-advanced.txt`.
  - Frontend: `frontend/src/**` (additive changes only).
  - Docs: new file `docs/ADVANCED_FEATURES.md`.
  - `.env.example` (append new variables only).
- Always use `.venv\Scripts\python.exe` and `.venv\Scripts\pip.exe` (Windows PowerShell). Never the system Python. Never use `git push --force`.
- This machine has very little free RAM. Run one server at a time and stop all servers when finished.

### 0.1 Start checklist (read-only first)

```bash
git checkout main
git pull origin main --tags
git config core.hooksPath .githooks
python scripts/check_phase.py --ready 4        # phases 1-3 must be OK
git status --short                              # must be empty
git checkout -b phase-3.5-advanced
```
If any command fails, STOP and tell me. Then summarize your plan in 8 lines and **wait for my approval** before writing code.

---

## 1. SCOPE: exactly three features

| # | Feature | Type |
|---|---|---|
| 1 | Tier-1 rule filter (spam gate before the ML model) | rule-based, no ML |
| 2 | Sarcasm flag `SARCASM_SUSPECTED` (sentiment contrast) | rule-based, no ML |
| 3 | SHAP explanations on demand (`POST /api/explain`) | uses the existing SVM |

**Explicitly OUT of scope (do not build, do not add dependencies for them):** transformer models (MuRIL, XLM-R), GPT-2 perplexity/burstiness detection, a Streamlit dashboard, any retraining.

All three features are **additive and optional**. The existing Phase 3 API contract must keep working exactly as it does today.

---

## 2. THE SAFETY CONTRACT (most important section)

1. **Feature switches** in `backend/app/config.py`, read from environment variables, default `true`:
   `ENABLE_TIER1`, `ENABLE_SARCASM`, `ENABLE_SHAP`.
2. **Backward compatibility test:** with all three set to `false`, the `/api/predict` response must have exactly the same keys and behavior as Phase 3. Write a test that proves it (`test_advanced_compat.py`).
3. **Existing fields keep their names and meaning:** `verdict`, `fake_probability`, `confidence`, `model_used`, `sentiment`, `flags`, `tokens`, `meta`, `latency_ms`, `created_at`, `token_map`. New information goes only into NEW optional fields.
4. **The 78 existing tests must pass unchanged.** If one fails because of your change, fix YOUR code, never the test. Tier-1 soft signals must therefore NOT be added to the existing `flags` list (see 3.1).
5. **No heavy dependencies.** The only new package allowed is `shap`, and only in `backend/requirements-advanced.txt`. The app must start and all other features must work when `shap` is NOT installed (import it lazily inside the explain code path).
6. **Never edit `backend/requirements.txt`.** Install advanced deps with:
   `.venv\Scripts\pip.exe install -r backend\requirements-advanced.txt -c backend\constraints-advanced.txt`
   where `backend/constraints-advanced.txt` (create it) copies the pinned lines of `requirements.txt` without extras. The install must NOT upgrade or downgrade numpy (1.26.4), scipy, pandas, or scikit-learn (1.5.2). If it tries to, STOP and tell me.
   Suggested pin: `shap==0.49.1` (resolves with the pinned versions).
7. In the finish checklist, `python scripts/check_phase.py 3` must still print OK.

---

## 3. BACKEND DESIGN

### 3.1 Feature 1: Tier-1 rule filter (`backend/app/services/tier1.py`)

Pure Python rules, microseconds per call, run BEFORE the model.

**Optional request field** on `POST /api/predict` (new, optional):
```json
"metadata": { "user_id": "string?", "posted_at": "ISO-8601?", "reviews_last_minute": 0 }
```
Validate it with Pydantic (all fields optional, sane limits). Requests without `metadata` must still work.

**Hard rules (decide immediately, skip the ML model):**
- `VELOCITY_EXCEEDED`: more than `TIER1_MAX_REVIEWS_PER_MINUTE` (default 5) reviews per minute from the same user. Source: `metadata.reviews_last_minute` if given, else a server-side in-memory sliding window keyed by `metadata.user_id` (60 s window, use `posted_at` if given else server time).
- `DUPLICATE_FLOOD`: the same normalized text (lowercased, whitespace-collapsed, hashed) seen at least `TIER1_DUPLICATE_THRESHOLD` (default 3) times within 10 minutes.

**Soft signals (reported, but the model still runs; they never change the verdict and are NOT added to the existing `flags` list):**
- `VERY_SHORT` (fewer than `TIER1_MIN_WORDS`, default 4 words)
- `LINK_OR_CONTACT_SPAM` (URL, e-mail or phone number)
- `REPEATED_CHARACTERS` (for example "goooood", 4 or more repeats)

Thread-safe (use a lock), memory-bounded (cap stored keys/hashes, drop the oldest), thresholds in `config.py` with env overrides.

**Response when `ENABLE_TIER1` is true** (new optional fields):
```json
"tier1": {
  "triggered": false,
  "action": "pass | flag_spam",
  "rules": [{ "code": "VERY_SHORT", "label": "Very short text", "severity": "low | medium | high", "kind": "soft | hard" }]
},
"decision_source": "model | tier1_rules"
```
When a HARD rule fires: do not load or run the model. Return `verdict: "fake"`, `fake_probability: 1.0`, `confidence: 1.0`, `model_used: "tier1_rules"`, `decision_source: "tier1_rules"`, `tokens: []`, cheap VADER `sentiment`, and `tier1.action: "flag_spam"`. Save it to history like any other prediction. Document that this probability is a rule decision, not a model score.

**Batch (`/api/predict/batch`):** optional CSV columns `user_id` and `posted_at`. If present and `ENABLE_TIER1` is on, compute velocity per user inside the file with a rolling 60 s window. Add `tier1_flagged` (count) to the batch `summary`. A CSV without those columns behaves exactly as before.

### 3.2 Feature 2: Sarcasm flag (`backend/app/services/sarcasm.py`)

Rule-based sentiment contrast. It runs AFTER the model and **never changes `verdict` or `fake_probability`** (an angry sarcastic customer is not necessarily fake). It only raises a risk flag for human review.

Logic:
- Split the review into the opening part (first sentence, at most the first 8 words) and the rest.
- Positive-opener cues: a configurable list. English examples: wow, great, amazing, awesome, perfect, love, best, thanks, brilliant. Small Hindi/Hinglish keyword lists are allowed (for example "बहुत पसंद आया", "बहुत बढ़िया", "bahut achha", "mast"). Keyword matching only, no model.
- Strong negative-outcome cues: garbage, trash, junk, useless, waste, broke, broken, worst, refund, scam, "stopped working"; Hindi/Hinglish examples "बेकार", "चिथड़े", "kachra". Keyword matching only.
- Use VADER too: opening sentiment compound >= +0.3 AND remaining text compound <= -0.3 counts as a contrast.
- `score` in 0 to 1: keyword contrast plus VADER contrast. `suspected = score >= SARCASM_THRESHOLD` (default 0.6, env override).

**Response when `ENABLE_SARCASM` is true and suspected:** add a new optional object and ONE extra item in the existing `flags` list:
```json
"sarcasm": { "suspected": true, "score": 0.82, "risk_level": "high", "positive_cues": ["wow"], "negative_cues": ["garbage"] }
```
```json
{ "code": "SARCASM_SUSPECTED", "label": "Possible sarcasm: positive opening, negative outcome", "severity": "high" }
```
When not suspected, still include `"sarcasm": { "suspected": false, "score": 0.0 }` (only when the feature is enabled).

### 3.3 Feature 3: SHAP explanations (`backend/app/services/explain_shap.py`, `backend/app/routers/explain.py`)

New endpoint (does not touch `/api/predict`, so predictions stay fast):

`POST /api/explain` with `{ "review": "string (1-5000)", "model": "best | nb | svm" }`
Response:
```json
{
  "method": "shap-linear | naive-bayes-logprob",
  "model_used": "svm",
  "base_value": 0.0,
  "tokens": [{ "token": "amaze", "score": 0.1889, "direction": "fake | genuine" }],
  "token_map": { "amaze": ["AMAZING"] },
  "latency_ms": 12
}
```
- For the SVM: use the linear base model (`svm_linear_base.pkl`, already committed) with `shap.LinearExplainer` on the sparse TF-IDF vector, background = a single all-zero row. **Test this in the real environment.** `LinearExplainer` can fail on sparse coefficients (a known `NotImplementedError` with `SVC(kernel="linear")`). If it fails, compute the identical value directly (for a linear model with a zero background, the SHAP value of a feature is `coef * tfidf_value`) and still label the method `shap-linear`.
- For Naive Bayes: reuse the existing log-probability difference from `explain.py` and label the method `naive-bayes-logprob`. Do not pretend it is SHAP.
- Return the top 10 tokens by absolute score, with `token_map` like the existing one.
- If `shap` is not installed or `ENABLE_SHAP` is false: SVM requests fall back to the existing `explain.py` coefficient scores with `method: "linear-coefficients"` and HTTP 200. Never crash.
- Same error envelope as the rest of the API, same validation rules and size limits as `/api/predict`.
- Register the router in `main.py` (this is the only required change there).

### 3.4 Wiring (minimal changes to existing files)

Keep edits to `routers/predict.py`, `schemas.py`, `config.py` and `main.py` small and additive. Order inside predict: Tier-1, then (if not short-circuited) the existing model path, then sarcasm, then build the response. Do not refactor existing code.

### 3.5 Backend tests (new files only)

- `test_advanced_tier1.py`: hard rules (velocity via metadata and via the sliding window, duplicate flood), soft signals do not touch `flags`, model is skipped on a hard rule, no-metadata request works, thresholds via config.
- `test_advanced_sarcasm.py`: a sarcastic example is flagged, a plain positive review and a plain negative review are not, `verdict` and `fake_probability` are unchanged by the flag, Hindi keyword example works.
- `test_advanced_explain.py`: SVM and NB both return tokens, the method label is correct, fallback works when `shap` is missing (use `monkeypatch` or `pytest.importorskip` so tests pass with or without `shap` installed).
- `test_advanced_compat.py`: with all three switches false, the `/api/predict` key set equals the Phase 3 key set; with them true, all Phase 3 keys are still present with the same types.
- Run the **whole** suite: `cd backend && ..\.venv\Scripts\python.exe -m pytest tests -q`. All 78 old tests plus the new ones must pass.

---

## 4. FRONTEND (additive only, `frontend/src/**`)

The frontend must keep working when the new fields are missing (mock mode or old backend).

- `lib/types.ts`: add the new optional fields (`metadata` in the request, `tier1`, `sarcasm`, `decision_source` in the response, the explain request/response types). Add `"tier1_rules"` to the allowed `model_used` values.
- `lib/api.ts` and `lib/mockApi.ts`: add `explain()` (real call to `/api/explain`, mock returns realistic data). Update the mock `predict` to sometimes return `tier1` and `sarcasm` so the UI can be tested in mock mode.
- `components/analyzer/ReviewInput.tsx`: a collapsed "Advanced" section with optional inputs (user id, reviews in the last minute). Collapsed by default, no layout shift.
- New components in `components/analyzer/`:
  - `Tier1Banner.tsx`: shown only when `tier1.triggered`; says the review was flagged by rules before the model, lists the rules, and shows soft signals as small chips.
  - `SarcasmBadge.tsx`: shown only when `sarcasm.suspected`; amber/high-risk style, explains "needs human review, not automatically fake".
  - `ExplainPanel.tsx`: an "Explain with SHAP" button, loading and error states, then the returned tokens highlighted (red = pushes toward fake, blue = toward genuine) with score tooltips, and the method label shown honestly.
- Keep the existing premium design system, dark and light themes, and accessibility (focus states, reduced motion).
- `cd frontend && npm run build` must pass with no errors (use `NODE_OPTIONS=--max-old-space-size=2048` if memory is low). Do not change any other page's behavior.
- Show me screenshots (mock mode is fine): analyze page with the Tier-1 banner, the sarcasm badge, and the SHAP panel, in dark theme.

---

## 5. DOCUMENTATION (new file only): `docs/ADVANCED_FEATURES.md`

Plain, honest, student-friendly. Must contain: what each feature does, how to turn each on or off (environment variables), how to install `shap` (the exact pip command with the constraints file), the new API fields and the new endpoint with real example responses from the running API, and a **Limitations** section that states clearly:
- The model is trained on English hotel reviews only. Hindi and Hinglish text is NOT supported by the classifier; the Hindi/Hinglish words in the sarcasm lists are simple keyword matches.
- Tier-1 and sarcasm rules are heuristics. Their accuracy was not measured on a labelled dataset. Do not claim an accuracy number.
- Sarcasm is a review-risk flag, not a fake verdict.
- The velocity and duplicate tracking is in memory, per server process, and resets on restart.
- SHAP explains the linear SVM only; for a linear model it equals coefficient times TF-IDF value. Naive Bayes uses a log-probability explanation instead.
- Not implemented: transformer models, LLM-generated text detection, multilingual models.

Do NOT edit `README.md` or `docs/LLD.md`. The owner will update them.

---

## 6. FINISH CHECKLIST (all must be true)

- Backend: the full pytest suite passes (78 old tests unchanged + new tests).
- `python scripts/check_phase.py 3` prints **OK. All checks passed.**
- `cd frontend && npm run build` passes.
- With `ENABLE_TIER1=false ENABLE_SARCASM=false ENABLE_SHAP=false`, `/api/predict` matches the Phase 3 response shape (proved by a test).
- You called, with real output shown to me (curl.exe or Invoke-RestMethod): a normal predict; a predict with `metadata.reviews_last_minute = 9` (Tier-1 hard rule, `model_used: "tier1_rules"`); the same review text sent 3 times (duplicate flood); a sarcastic review ("Wow, best phone ever, total garbage, the screen broke in a day"); `/api/explain` for `svm` and for `nb`; a batch CSV with `user_id` and `posted_at` columns.
- `git status --short` shows no changes to `README.md`, `docs/HLD.md`, `docs/LLD.md`, `prompts/`, `scripts/`, `backend/ml/`, `backend/models/`, `backend/requirements.txt`, or any existing test file.
- No `.db`, `.pkl` from new work, or `node_modules` is committed.

## 7. GIT HAND-OFF (run exactly, in this order)

Show me the pytest summary, the `check_phase.py 3` output, and `git status --short` BEFORE pushing. Push only if all are clean.

```bash
git add -A
git commit -m "phase 3.5: tier-1 filter, sarcasm flag, SHAP explanations (optional features)"
git checkout main
git pull origin main
git merge --no-ff phase-3.5-advanced -m "Merge phase 3.5"
python scripts/check_phase.py 3
git push origin main
git tag phase-3.5-complete
git push origin phase-3.5-complete
```
If the push is rejected, do NOT force push: `git pull --rebase origin main`, re-run the checks, push again. If there is a conflict you cannot resolve safely, stop and ask me.

When done, tell me: the final commit hash, a 5-line summary, the real outputs requested above, and anything unfinished. Be honest about anything that did not work.
