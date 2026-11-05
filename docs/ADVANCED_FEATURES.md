# Phase 3.5 — Optional Advanced Features

Three extra capabilities sit **on top of** the Phase 3 API. None of them replaced
or changed anything that already worked. Every one of them can be turned off with
an environment variable, and when they are off the API answers exactly the way it
did in Phase 3 — same keys, same types, same numbers.

| # | Feature | What it adds | Needs a model? |
|---|---------|--------------|----------------|
| 1 | Tier-1 rule filter | A cheap spam gate that runs **before** the ML model | No — pure Python rules |
| 2 | Sarcasm flag | One extra item in `flags` plus a `sarcasm` block | No — keyword + VADER contrast |
| 3 | SHAP explanations | A new endpoint, `POST /api/explain` | Uses the SVM that Phase 2 already trained |

Explicitly **not** built (they were out of scope for this phase): transformer
models such as MuRIL or XLM-R, GPT-2 perplexity / burstiness detection, a
Streamlit dashboard, and any retraining. The files in `backend/ml/` and
`backend/models/` were never touched.

---

## 1. Turning the features on or off

All three switches live in `backend/app/config.py` and default to `true`. Set them
in `backend/.env` (or in the shell before starting uvicorn) to change them:

```bash
ENABLE_TIER1=false      # no metadata field, no "tier1" or "decision_source" keys
ENABLE_SARCASM=false    # no "sarcasm" key, no SARCASM_SUSPECTED flag
ENABLE_SHAP=false       # /api/explain still works, labelled "linear-coefficients"
```

Because the response builder uses `response_model_exclude_none`, a disabled
feature removes its key entirely rather than sending `null`. That is what keeps
the "all false" response byte-for-byte compatible with Phase 3, and
`backend/tests/test_advanced_compat.py` proves it.

Tunable thresholds (all optional, all shown as the defaults):

```bash
TIER1_MAX_REVIEWS_PER_MINUTE=5     # VELOCITY_EXCEEDED fires above this count
TIER1_DUPLICATE_THRESHOLD=3        # DUPLICATE_FLOOD fires at this many copies
TIER1_MIN_WORDS=4                  # VERY_SHORT fires below this word count
TIER1_VELOCITY_WINDOW_SECONDS=60   # sliding window for the velocity counter
TIER1_DUPLICATE_WINDOW_SECONDS=600 # sliding window for the duplicate counter
TIER1_MAX_TRACKED_KEYS=2000        # memory cap: oldest keys are dropped
SARCASM_THRESHOLD=0.6              # contrast score needed to raise the flag
```

The full list is appended at the bottom of `.env.example`.

## 2. Installing `shap` (only if you want feature 3 to say "shap-linear")

`shap` is deliberately **not** in `backend/requirements.txt`. It lives in its own
file, and the app starts and runs perfectly without it:

```powershell
.venv\Scripts\pip.exe install -r backend\requirements-advanced.txt -c backend\constraints-advanced.txt
```

`backend/constraints-advanced.txt` copies every pin from `requirements.txt`, so
pip is not allowed to move the ML core while installing `shap`. Verified on this
machine with `shap==0.49.1` installed — `numpy==1.26.4`, `scipy==1.13.1`,
`pandas==2.2.2` and `scikit-learn==1.5.2` came out unchanged. The extra packages
`shap` needs alongside them are `numba`, `llvmlite`, `slicer`, `cloudpickle`,
`regex`, `tqdm` and `packaging`.

The import is lazy: `explain_shap._load_shap()` tries `import shap` inside the
function that needs it, so a missing package costs nothing and breaks nothing.

---

## 3. Feature 1 — the Tier-1 rule filter

`backend/app/services/tier1.py`. The idea: some reviews do not need a neural
network or an SVM to spot. Five reviews a minute from one account, or the same
sentence pasted three times, is spam no matter what the words say. Those checks
take microseconds, and when one of the two *hard* rules fires we skip the model
completely.

### The two hard rules

| Code | Fires when |
|------|-----------|
| `VELOCITY_EXCEEDED` | More than `TIER1_MAX_REVIEWS_PER_MINUTE` reviews per minute for one user. Source is `metadata.reviews_last_minute` if the client sends it; otherwise a server-side sliding window keyed by `metadata.user_id` (60 s, using `posted_at` when supplied, server time otherwise). |
| `DUPLICATE_FLOOD` | The same normalised text (lower-cased, whitespace collapsed, SHA-1 hashed) seen `TIER1_DUPLICATE_THRESHOLD` times inside 10 minutes. |

### The three soft signals

`VERY_SHORT`, `LINK_OR_CONTACT_SPAM` (URL / e-mail / phone), and
`REPEATED_CHARACTERS` (`goooood`, four or more repeats). They are reported inside
the `tier1.rules` array with `"kind": "soft"` and the model still runs and still
decides the verdict. **They are never added to the existing `flags` list** — that
is a compatibility rule, not an oversight.

### New optional request field

```json
{ "review": "…", "model": "best", "metadata": { "user_id": "user-42", "posted_at": "2026-01-31T09:00:00Z", "reviews_last_minute": 9 } }
```

Every field inside `metadata` is optional and Pydantic validates them (`user_id`
up to 128 characters and never blank, `reviews_last_minute` 0–10000, `posted_at`
parsed as ISO-8601 and normalised to UTC). A request with no `metadata` at all
behaves as before, with the server-side window simply not having a user to count.

### Real response when a hard rule fires

Sent with `"metadata": { "user_id": "user-42", "reviews_last_minute": 9 }`:

```json
{"id":5,"verdict":"fake","fake_probability":1.0,"confidence":1.0,"model_used":"tier1_rules","sentiment":{"compound":0.9545,"label":"Positive","pos":0.672,"neu":0.328,"neg":0.0},"flags":[{"code":"PROMOTIONAL_LANGUAGE","label":"Promotional wording (best, perfect, highly recommend, five stars)","severity":"high"},{"code":"EXTREME_ONE_SIDED_SENTIMENT","label":"Over-the-top positive sentiment (compound 0.95)","severity":"high"},{"code":"EXCLAMATION_OVERLOAD","label":"Repeated exclamation marks","severity":"medium"},{"code":"NO_CONCRETE_DETAILS","label":"No digits or contrast words","severity":"medium"}],"tokens":[],"meta":{"words":12,"exclamations":4,"caps_words":1},"latency_ms":1,"created_at":"2026-11-05T04:49:48.459634+00:00","token_map":{},"tier1":{"triggered":true,"action":"flag_spam","rules":[{"code":"VELOCITY_EXCEEDED","label":"Too many reviews from this user in the last minute","severity":"high","kind":"hard"}]},"sarcasm":{"suspected":false,"score":0.0},"decision_source":"tier1_rules"}
```

Read that `fake_probability: 1.0` for what it is: **a rule decision, not a model
score.** The SVM was never asked. `decision_source: "tier1_rules"` exists so a
front end or a report can separate rule verdicts from model verdicts. The row is
still written to history like any other prediction, and `tokens` / `token_map`
are empty because there is no model to attribute.

### Same review three times

Copy 1 and copy 2 pass through the model (identical scores, as they should be);
copy 3 trips `DUPLICATE_FLOOD`:

```json
{"id":8,"verdict":"fake","fake_probability":1.0,"confidence":1.0,"model_used":"tier1_rules","sentiment":{"compound":-0.2263,"label":"Negative","pos":0.0,"neu":0.808,"neg":0.192},"flags":[{"code":"NO_CONCRETE_DETAILS","label":"No digits or contrast words","severity":"medium"}],"tokens":[],"meta":{"words":11,"exclamations":0,"caps_words":0},"latency_ms":1,"created_at":"2026-11-05T04:49:48.741475+00:00","token_map":{},"tier1":{"triggered":true,"action":"flag_spam","rules":[{"code":"DUPLICATE_FLOOD","label":"The same review text submitted repeatedly","severity":"high","kind":"hard"}]},"sarcasm":{"suspected":false,"score":0.0},"decision_source":"tier1_rules"}
```

Matching ignores case and spacing, so `"Great  Hotel!!"` and `"great hotel!!"`
count as the same text.

### Batch mode

`/api/predict/batch` accepts two **optional** CSV columns next to `review`
(and `rating`): `user_id` and `posted_at`. When they are present and
`ENABLE_TIER1` is on, velocity is computed per user with a rolling 60-second
window *inside that upload*, using its own tracker so a big CSV cannot inflate
the server's live counters.

```csv
user_id,posted_at,review
u1,2026-01-31T09:00:00Z,First distinct review of a hotel with a dirty bathroom
u1,2026-01-31T09:00:08Z,Second distinct review of a resort with a loud air conditioner
u1,2026-01-31T09:00:16Z,Third distinct review of an inn with cold water in the shower
u1,2026-01-31T09:00:24Z,Fourth distinct review of a hostel with a broken lift and slow wifi
u1,2026-01-31T09:00:32Z,Fifth distinct review of a motel with a stained carpet and tiny towel
u1,2026-01-31T09:00:40Z,Sixth distinct review of a lodge with a leaking window and cold food
u1,2026-01-31T09:00:48Z,Seventh distinct review of an apartment with a noisy fan and slow checkin
```

Seven rows, same user, all inside one minute → the 6th and 7th cross the limit of
5 and are flagged by rules; the summary grows one key:

```json
{"total":7,"fake_count":2,"fake_percent":28.5714,"avg_confidence":0.9031,"tier1_flagged":2}
```

The two flagged rows come back with the same shape as every other batch row:

```json
{"row":6,"review":"Sixth distinct review of a lodge with a leaking window and cold food","rating":null,"verdict":"fake","fake_probability":1.0,"confidence":1.0,"sentiment_label":"Mixed"}
```

A CSV *without* `user_id` / `posted_at` returns the original four summary keys and
behaves exactly as it did in Phase 3. A bad `posted_at` value fails the upload
with the standard error envelope and code `CSV_INVALID_POSTED_AT`.

---

## 4. Feature 2 — the sarcasm flag

`backend/app/services/sarcasm.py`. It runs **after** the model and can never
change `verdict` or `fake_probability` — an angry, sarcastic paying customer is
still a real customer. All it does is add one entry to `flags` so a human
reviewer knows to look twice.

The logic is a contrast test, not a classifier:

1. Split the review into the opening (first sentence, at most the first 8 words) and the rest.
2. Look for positive-opener cues in the opening: `wow, great, amazing, awesome, perfect, love, best, thanks, brilliant, excellent, wonderful, fantastic`, plus a few Hindi / Hinglish keywords (`बहुत पसंद आया`, `बहुत बढ़िया`, `bahut achha`, `mast`, `shandaar`).
3. Look for negative-outcome cues in the rest: `garbage, trash, junk, useless, waste, broke, broken, worst, refund, scam, stopped working`, plus `बेकार`, `चिथड़े`, `kachra`, `bekaar`, `fraud`.
4. Run VADER on both halves. An opening compound at or above `+0.3` against a remainder at or below `-0.3` is a VADER contrast.
5. `score = 0.6 × keyword_contrast + 0.4 × vader_contrast`, and `suspected = score >= SARCASM_THRESHOLD` (0.6 by default). Severity is `high` at 0.8 and above, otherwise `medium`.

Keyword matching is whole-word only, so "best" matches but "coffee-best" noise
does not, and Devanagari combining marks survive the normalisation (without that,
the Hindi cues silently stop matching).

The review the spec suggested, verbatim from the running API:

```json
{"id":9,"verdict":"genuine","fake_probability":0.354446,"confidence":0.645554,"model_used":"svm","sentiment":{"compound":0.7351,"label":"Positive","pos":0.426,"neu":0.426,"neg":0.149},"flags":[{"code":"SARCASM_SUSPECTED","label":"Possible sarcasm: positive opening, negative outcome","severity":"high"},{"code":"NO_CONCRETE_DETAILS","label":"No digits or contrast words","severity":"medium"}],"tokens":[{"token":"ever","score":0.1485,"direction":"fake"},{"token":"phone","score":-0.1355,"direction":"genuine"},{"token":"garbage","score":0.0999,"direction":"fake"},{"token":"screen","score":0.0912,"direction":"fake"},{"token":"day","score":-0.0818,"direction":"genuine"},{"token":"total","score":-0.0732,"direction":"genuine"},{"token":"break","score":-0.0512,"direction":"genuine"},{"token":"best","score":-0.026,"direction":"genuine"}],"meta":{"words":12,"exclamations":0,"caps_words":0},"latency_ms":4,"created_at":"2026-11-05T04:49:48.832280+00:00","token_map":{"ever":["ever"],"phone":["phone"],"garbage":["garbage"],"screen":["screen"],"day":["day"],"total":["total"],"break":["broke"],"best":["best"]},"tier1":{"triggered":false,"action":"pass","rules":[]},"sarcasm":{"suspected":true,"score":1.0,"risk_level":"high","positive_cues":["wow","best"],"negative_cues":["garbage","broke"]},"decision_source":"model"}
```

Notice: `verdict` stayed `genuine`, the model still ran (`decision_source:
"model"`), and the flag arrived with the cues that caused it. When nothing is
suspected and the feature is on, the block is still present and minimal:
`{"suspected": false, "score": 0.0}`.

---

## 5. Feature 3 — `POST /api/explain`

`backend/app/services/explain_shap.py` plus
`backend/app/routers/explain.py`, registered in `main.py`. It is a separate
endpoint on purpose: explanations are optional and sometimes slow, and the
prediction hot path should not pay for them.

Request, with the same validation and limits as `/api/predict`:

```json
{ "review": "Wow, best phone ever, total garbage, the screen broke in a day", "model": "best" }
```

Response shape:

```json
{ "method": "…", "model_used": "svm", "base_value": -0.138762, "tokens": [{"token": "ever", "score": 0.1485, "direction": "fake"}], "token_map": {"ever": ["ever"]}, "latency_ms": 12 }
```

What `method` means — stated honestly, because a label that lies is worse than no
label:

| `method` | When you get it |
|----------|-----------------|
| `shap-linear` | `shap` is installed, `ENABLE_SHAP` is true, and `shap.LinearExplainer` ran against the committed `svm_linear_base.pkl` with an all-zero sparse background. |
| `linear-coefficients` | `shap` is not installed or `ENABLE_SHAP=false`: the same coefficient × TF-IDF computation, done directly. Numbers identical, label different. |
| `naive-bayes-logprob` | Any NB request. It is a log-probability difference, not SHAP, and is not labelled as if it were. |

Real output for the SVM (cold start, so the first call also pays for loading the
artifacts):

```json
{"method":"shap-linear","model_used":"svm","base_value":-0.138762,"tokens":[{"token":"ever","score":0.1485,"direction":"fake"},{"token":"phone","score":-0.1355,"direction":"genuine"},{"token":"garbage","score":0.0999,"direction":"fake"},{"token":"screen","score":0.0912,"direction":"fake"},{"token":"day","score":-0.0818,"direction":"genuine"},{"token":"total","score":-0.0732,"direction":"genuine"},{"token":"break","score":-0.0512,"direction":"genuine"},{"token":"best","score":-0.026,"direction":"genuine"},{"token":"wow","score":-0.0094,"direction":"genuine"}],"token_map":{"ever":["ever"],"phone":["phone"],"garbage":["garbage"],"screen":["screen"],"day":["day"],"total":["total"],"break":["broke"],"best":["best"],"wow":["Wow"]},"latency_ms":660}
```

The same review with `"model": "nb"`:

```json
{"method":"naive-bayes-logprob","model_used":"nb","base_value":0.00627,"tokens":[{"token":"ever","score":0.1806,"direction":"fake"},{"token":"garbage","score":0.1792,"direction":"fake"},{"token":"total","score":-0.1667,"direction":"genuine"},{"token":"phone","score":-0.0947,"direction":"genuine"},{"token":"break","score":-0.0878,"direction":"genuine"},{"token":"screen","score":0.0768,"direction":"fake"},{"token":"day","score":-0.0446,"direction":"genuine"},{"token":"wow","score":0.0405,"direction":"fake"},{"token":"best","score":0.0344,"direction":"fake"}],"token_map":{"ever":["ever"],"garbage":["garbage"],"total":["total"],"phone":["phone"],"break":["broke"],"screen":["screen"],"day":["day"],"wow":["Wow"],"best":["best"]},"latency_ms":1}
```

And the same SVM request with `ENABLE_SHAP=false` running the fallback — same
`base_value`, same scores, honest relabel:

```json
{"method":"linear-coefficients","model_used":"svm","base_value":-0.138762,"tokens":[{"token":"ever","score":0.1485,"direction":"fake"},{"token":"phone","score":-0.1355,"direction":"genuine"},{"token":"garbage","score":0.0999,"direction":"fake"},{"token":"screen","score":0.0912,"direction":"fake"},{"token":"day","score":-0.0818,"direction":"genuine"},{"token":"total","score":-0.0732,"direction":"genuine"},{"token":"break","score":-0.0512,"direction":"genuine"},{"token":"best","score":-0.026,"direction":"genuine"},{"token":"wow","score":-0.0094,"direction":"genuine"}],"token_map":{"ever":["ever"],"phone":["phone"],"garbage":["garbage"],"screen":["screen"],"day":["day"],"total":["total"],"break":["broke"],"best":["best"],"wow":["Wow"]},"latency_ms":1}
```

Details worth knowing:

* Top 10 tokens by absolute score, `direction` is the sign of the score.
* `base_value + Σ(scores)` reproduces the model's own decision value — the tests check this against `decision_function()` directly. For the linear SVM that is arithmetic, not a coincidence: with an all-zero background, a linear model's Shapley value for feature *j* **is** `coef[j] × x[j]`, and the base value is `f(0)`, the intercept.
* `token_map` uses the same stem → surface-words convention as `/api/predict`, so `"break"` maps back to the word "broke" the user actually typed.
* Text-only input like `"!!! ??? ..."` returns HTTP 200 with `"tokens": []`. Nothing crashes.
* Errors use the existing envelope: `{"error": {"code": "VALIDATION_ERROR", "message": "review: 'review' must be a non-empty string (1-5000 characters)."}}`, `INVALID_MODEL` for an unknown `model`, `MODELS_NOT_LOADED` (503) if the artifacts are missing.
* `/api/explain` **never writes to history** — it is read-only explanation, not a prediction.
* It ignores `ENABLE_TIER1` / `ENABLE_SARCASM`; it has its own `ENABLE_SHAP` switch.

---

## 6. What is where

| File | Change |
|------|--------|
| `backend/app/services/tier1.py` | new — rules, thresholds, thread-safe sliding-window tracker |
| `backend/app/services/sarcasm.py` | new — contrast heuristic and flag builder |
| `backend/app/services/explain_shap.py` | new — SHAP path, direct fallback, NB log-probabilities |
| `backend/app/routers/explain.py` | new — `POST /api/explain` |
| `backend/app/config.py` | additive — the three switches and the tuning knobs |
| `backend/app/schemas.py` | additive — `PredictMetadata`, `Tier1Block`, `SarcasmBlock`, `ExplainRequest`, `ExplainResponse` |
| `backend/app/routers/predict.py` | additive — Tier-1 before the model, sarcasm after it, batch metadata columns |
| `backend/app/main.py` | two lines: import and `include_router(explain.router)` |
| `backend/requirements-advanced.txt`, `backend/constraints-advanced.txt` | new — `shap` and the pins that protect the ML core |
| `backend/tests/test_advanced_{tier1,sarcasm,explain,compat}.py` | new — 85 tests |
| `backend/tests/conftest.py` | new — pins the switches off for the pre-existing Phase 3 test files and on for `test_advanced_*` |
| `frontend/src/**` | additive — see the analyze page |

## 7. Limitations — please read before citing numbers

* **The classifier is English-only.** It was trained on the Deceptive Opinion
  Spam Corpus, English hotel reviews. Hindi and Hinglish text is **not**
  supported by the model; the Hindi and Hinglish words in the sarcasm lists are
  plain keyword matches, nothing more. A Hindi review is scored by an English
  model and its result should not be trusted.
* **Tier-1 and sarcasm are heuristics.** Their accuracy was never measured
  against a labelled dataset. There is no precision, recall or F1 number for
  them in this project, and no claim of one should be made in a report or a
  presentation. The measured metrics in `backend/models/metrics.json` belong to
  the NB and SVM models only.
* **Sarcasm is a review-risk flag, not a fake verdict.** `SARCASM_SUSPECTED`
  means "a human should read this twice". It never changes `verdict` or
  `fake_probability`, by design and by test.
* **Tracking is in memory, per server process, and resets on restart.** The
  velocity and duplicate counters live in a bounded dictionary inside one Python
  process. Behind multiple workers or multiple containers, each one counts only
  what it sees, so the effective limits are per worker, not global. A restart
  clears them. Making them global would need Redis or the database, which was not
  in scope.
* **SHAP explains the linear SVM only**, and for a linear model with a zero
  background its value is exactly `coefficient × TF-IDF value` — so the "SHAP"
  label here describes the attribution method, not a hidden capability. Naive
  Bayes gets a log-probability explanation instead and is labelled
  `naive-bayes-logprob`. There is no SHAP for NB here.
* **Not implemented:** transformer models, multilingual models, and
  LLM-generated-text detection. Those are the obvious next steps if this project
  continues, and each would need a real dataset and measured metrics.
