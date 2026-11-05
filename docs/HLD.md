# High-Level Design (HLD)

## 1. System flow (training time)

```mermaid
flowchart LR
    A[Review dataset<br/>Amazon / Yelp / Deceptive Opinion Spam] --> B[Preprocessing<br/>clean, tokenize, lemmatize]
    B --> C[Feature extraction<br/>TF-IDF + VADER + meta features]
    C --> D[Model training<br/>Naive Bayes + SVM, GridSearchCV]
    D --> E[Evaluation<br/>accuracy, precision, recall, F1, ROC-AUC]
    E --> F[(Artifacts<br/>*.pkl + metrics.json)]
```

## 2. Runtime architecture (prediction time)

```mermaid
flowchart LR
    U[User browser] -->|HTTP JSON| FE[Next.js frontend :3000]
    FE -->|REST /api/*| API[FastAPI backend :8000]
    API --> P[Predictor singleton]
    P --> V[vectorizer.pkl + scaler.pkl]
    P --> M[nb_model.pkl / svm_model.pkl]
    P --> S[VADER sentiment]
    API --> DB[(SQLite history)]
    API --> MJ[metrics.json]
```

## 3. Components

| Component | Responsibility | Built in |
|---|---|---|
| Frontend (Next.js) | Premium UI: analyzer, batch, model lab, history, how it works | Phase 1 |
| ML pipeline (`backend/ml`) | Preprocess, features, train NB and SVM, evaluate, save artifacts | Phase 2 |
| Backend API (`backend/app`) | Serve predictions, explanations, history, metrics | Phase 3 |
| Integration | Connect frontend to real API, end-to-end tests, bug fixing | Phase 4 |
| Packaging | Docker, reports, screenshots, presentation notes | Phase 5 |

## 4. Golden design rule

Training and inference MUST use the exact same `clean_text()` and the exact same fitted vectorizer and scaler.
The backend imports them from `backend/ml/`. It never re-implements them.

## 5. Phase dependency chain

```mermaid
flowchart LR
    P1[Phase 1 UI<br/>mock data] --> P2[Phase 2 ML<br/>artifacts committed]
    P2 --> P3[Phase 3 API<br/>uses artifacts]
    P3 --> P4[Phase 4 Integration<br/>UI + API + tests]
    P4 --> P5[Phase 5 Docker + docs]
```

## 6. Prediction pipeline with Phase 3.5 features

```mermaid
flowchart LR
    IN[Review + optional metadata] --> T1{Tier-1 rule filter}
    T1 -->|hard rule hit| SP[Flag as spam<br/>model skipped]
    T1 -->|pass| M[Tier-2 model<br/>Naive Bayes / SVM]
    M --> SA[Sarcasm risk check]
    SA --> OUT[Verdict + flags + sentiment]
    OUT -. on demand .-> EX[POST /api/explain<br/>SHAP tokens]
    SP --> OUT
```

Each of the three additions (Tier-1, sarcasm, SHAP) can be switched off with an environment variable (`ENABLE_TIER1`, `ENABLE_SARCASM`, `ENABLE_SHAP`).
