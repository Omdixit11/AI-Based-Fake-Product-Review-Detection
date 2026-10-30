# PHASE 2 PROMPT: ML Pipeline

> Give this ENTIRE file to your Antigravity agent. It is Phase 2 of 5. Read `README.md` and `docs/LLD.md` first.

---

## 0. TEAM CONTEXT (read first, these rules override anything below)

- This is the **TruthLens** monorepo. The folder skeleton already exists. Do NOT recreate the structure; fill in only your phase.
- Five people work in strict order. You do **ONLY Phase 2**. Earlier phases are finished and already in git. Do not rewrite or "improve" their work.
- **PROTECTED files, never edit:** README.md, docs/HLD.md, docs/LLD.md, docs/PROJECT_STRUCTURE.md, everything in prompts/, everything in .githooks/, scripts/check_phase.py, scripts/protected.sha256. A git pre-commit hook blocks commits that touch them.
- **You MAY create or change:** `backend/ml/**`, `backend/models/**`, `backend/tests/test_ml.py`. You may APPEND packages to `backend/requirements.txt` only if truly required (never change existing pinned versions).
- **You must NOT change:** `frontend/`, `backend/app/`, `Makefile`, `.env.example`, `docs/`, and the protected files.
- Never use `git push --force`. Never commit secrets, `node_modules`, `.venv`, or the raw dataset.

### 0.1 Start checklist (run these first)

```bash
git checkout main
git pull origin main --tags
git config core.hooksPath .githooks
python scripts/check_phase.py --ready 2
git checkout -b phase-2-ml
```
If `check_phase.py --ready 2` prints NOT READY, **stop and tell me**. Do not try to fix earlier phases.

### 0.2 Adjustments for this repo (these override anything below that conflicts)

1. The skeleton already has `backend/requirements.txt` with pinned versions (scikit-learn 1.5.2 etc.) and empty `__init__.py` files. Do not change the pins: the trained `.pkl` files must load on every teammate's machine.
2. Setup: `pip install -r backend/requirements.txt` then `python scripts/download_nltk.py`. Run everything from the `backend/` folder: `cd backend && python -m ml.run_pipeline`. Tests: `cd backend && python -m pytest tests -q`.
3. **The dataset is NOT in git.** The human must place it at `backend/data/raw/reviews.csv` before you start. If it is missing, STOP and tell me exactly what to download. Never train on made-up data. `dataset.name` in `metrics.json` must be the real dataset name and must not contain the word "synthetic".
4. **The trained artifacts ARE committed to git** (`backend/models/*.pkl` and `metrics.json`), because Phases 3, 4 and 5 need them and teammates do not have the dataset. Therefore EVERY file in `backend/models/` must be smaller than 90 MB (GitHub's limit is 100 MB). If the calibrated SVM is too big, reduce `max_features` (for example 20000), use a linear kernel, or reduce the grid. Report the file sizes.
5. The final `metrics.json` must follow the contract in `docs/LLD.md` exactly, including both feature sets for both models, because the checker script and the frontend read it.
6. Add `backend/tests/test_ml.py` with the tests described below. They must pass without the dataset present (use tiny inline text samples), because teammates run them without the dataset.

---

---

## 1. GOAL

In the monorepo `truthlens/`, build only the **machine learning pipeline** inside `backend/ml/` for a fake product review detector. Use **NLP, TF-IDF, Sentiment Analysis, Naive Bayes and SVM**. A separate FastAPI service and a separate frontend will consume your output, so the file names and `metrics.json` schema below are a strict contract. Do not change them.

Stack: Python 3.11, pandas, numpy, scipy, scikit-learn, NLTK (stopwords, wordnet, vader_lexicon), imbalanced-learn, joblib, matplotlib (only for optional report images), pytest.

---

## 2. FILES TO CREATE

```
backend/
├── requirements.txt
├── data/raw/                  # dataset goes here (do not commit)
├── models/                    # outputs go here
└── ml/
    ├── config.py              # paths, FAKE_LABEL=1, column mapping, random_state
    ├── preprocess.py          # clean_text(), load_dataset()
    ├── features.py            # TF-IDF, VADER, meta features, scaler
    ├── train_nb.py
    ├── train_svm.py
    ├── evaluate.py
    └── run_pipeline.py        # one command runs everything
backend/tests/test_ml.py
```

---

## 3. DATASET RULES

- Expect `backend/data/raw/reviews.csv` with columns mapped in `config.py` to: `text`, `label` (1 = fake, 0 = genuine), optional `rating`.
- Suggested real sources: the Deceptive Opinion Spam Corpus, or a Yelp/Amazon fake-review dataset from Kaggle. Different datasets use different column names and label strings (for example "CG"/"OR" or "truthful"/"deceptive"), so keep a `LABEL_MAP` and `COLUMN_MAP` in `config.py`.
- If the file is missing, **stop and print exact instructions** on what to download and where to put it. Do not invent training data and present it as real.
- Only for smoke-testing the code, you may generate a tiny synthetic CSV in `tests/`, clearly named `synthetic_smoke_test.csv`. Never use it for reported metrics.
- Drop duplicates and empty rows. Print dataset size, class balance and average review length.

---

## 4. IMPLEMENTATION DETAILS

**preprocess.py**
- `clean_text(text: str) -> str`: lowercase, remove URLs, HTML tags, punctuation and digits, collapse whitespace, remove stopwords **but keep negations** (not, no, never, nor), lemmatize with WordNet.
- This function is the single source of truth. The API will import it, so keep it pure, deterministic and dependency-light.
- `load_dataset(path) -> DataFrame` applies `COLUMN_MAP` and `LABEL_MAP`.

**features.py**
- TF-IDF: `ngram_range=(1,2)`, `min_df=2`, `max_df=0.9`, `sublinear_tf=True`.
- VADER features: `neg, neu, pos, compound`.
- Meta features: char count, word count, exclamation count, uppercase-word ratio, has-digit flag, average word length. Compute these on the **raw** text, not the cleaned text.
- Two feature sets: `tfidf_only` and `tfidf_sentiment` (TF-IDF + VADER + meta, extra columns scaled with MinMaxScaler so Naive Bayes gets non-negative values, then sparse-hstacked).
- Expose `build_features(texts, fitted_objects, feature_set)` so the API can rebuild features identically at inference time.

**train_nb.py / train_svm.py**
- Stratified 80/20 split, fixed `random_state`. Fit the vectorizer and scaler on the **training split only** (no leakage).
- Apply SMOTE on the training split only, and only if the minority class is under 40 percent.
- GridSearchCV, 5-fold stratified, scoring F1. NB: tune `alpha`. SVM: tune `C`, `kernel` (linear, rbf), `gamma`.
- Wrap the final SVM in `CalibratedClassifierCV` so it has `predict_proba`. Keep the underlying linear SVM available for coefficient-based explanations.
- Train both models on **both** feature sets.

**evaluate.py**
- For each model and feature set compute accuracy, precision, recall, F1, ROC-AUC, confusion matrix and ROC curve points on the held-out test split.
- Choose `best_model` by F1 (tie-break by ROC-AUC) and the best feature set for each model.

---

## 5. OUTPUT ARTIFACTS (exact names, in `backend/models/`)

- `vectorizer.pkl`, `scaler.pkl`
- `nb_model.pkl`, `svm_model.pkl` (the calibrated one), and `svm_linear_base.pkl` (for explanations)
- `metrics.json` with this exact shape:

```json
{
  "generated_at": "ISO-8601",
  "dataset": { "name": "string", "size": 0, "train_size": 0, "test_size": 0, "fake_percent": 0.0, "avg_words": 0.0 },
  "best_model": "nb | svm",
  "active_feature_set": "tfidf_only | tfidf_sentiment",
  "models": {
    "nb": {
      "tfidf_only":      { "accuracy": 0, "precision": 0, "recall": 0, "f1": 0, "roc_auc": 0,
                           "confusion_matrix": [[0,0],[0,0]],
                           "roc_curve": { "fpr": [], "tpr": [] },
                           "best_params": {} },
      "tfidf_sentiment": { "...same keys..." }
    },
    "svm": { "tfidf_only": { "..." }, "tfidf_sentiment": { "..." } }
  }
}
```
Confusion matrix layout: `[[TN, FP], [FN, TP]]` where "positive" means fake. Round floats to 4 decimals. Downsample ROC curves to at most 100 points.

---

## 6. RUN COMMAND

`python -m ml.run_pipeline` runs: load, clean, features, train NB and SVM, evaluate, save artifacts, write `metrics.json`, and print a readable summary table.

---

## 7. TESTS (pytest)

- `clean_text` keeps negations, removes URLs, and is deterministic.
- Feature matrix has the same column count at train time and when rebuilt through `build_features` on new text.
- Saved artifacts load back and `predict_proba` returns two probabilities that sum to 1.
- `metrics.json` has every required key.

---

## 8. RULES

1. Do not fabricate or hard-code any metric. Every number must come from the real run.
2. No data leakage: split first, then fit vectorizer, scaler and SMOTE on training data only.
3. If accuracy is suspiciously perfect (above 0.99), investigate for leakage or duplicates and report it honestly.
4. After finishing, run the pipeline and show me the printed summary table and the contents of `metrics.json`, and tell me which model won and why.

Start by listing your plan in 8 lines and any assumptions about the dataset columns.

---

## FINISH CHECKLIST (every item must be true before you hand off)

- `cd backend && python -m ml.run_pipeline` completed on the REAL dataset and printed a summary table.
- `backend/models/` contains `vectorizer.pkl`, `scaler.pkl`, `nb_model.pkl`, `svm_model.pkl`, `svm_linear_base.pkl`, `metrics.json`; every file is under 90 MB.
- `metrics.json` has `best_model`, `active_feature_set`, and all 4 blocks (nb/svm x tfidf_only/tfidf_sentiment) with every required key.
- `cd backend && python -m pytest tests -q` passes (without the dataset).
- You told me which model won, its F1 and ROC-AUC, and whether anything looked suspicious (such as accuracy above 0.99).
- `python scripts/check_phase.py 2` prints **OK. All checks passed.**
- `git status` shows no changes to protected files (README.md, docs/HLD.md, docs/LLD.md, prompts/, scripts/check_phase.py).

## GIT HAND-OFF (run exactly, in this order)

```bash
git add -A
git commit -m "phase 2: ML pipeline, trained models and metrics"
git checkout main
git pull origin main
git merge --no-ff phase-2-ml -m "Merge phase 2"
python scripts/check_phase.py 2
git push origin main
git tag phase-2-complete
git push origin phase-2-complete
```
If the push is rejected, do NOT force push. Run `git pull --rebase origin main`, re-run the check, and push again. If there is a conflict you cannot resolve safely, stop and ask me.

When done, tell me: the final commit hash, a 5-line summary of what you built, and anything unfinished.
