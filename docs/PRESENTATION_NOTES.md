# TruthLens Presentation Notes & Viva Preparation Guide

A comprehensive guide for college project demonstrations, evaluator reviews, and technical viva examinations for **TruthLens: AI-Based Fake Product Review Detection**.

---

## 1. Ten-Slide Presentation Outline

### Slide 1: Title & Project Overview
- **Title:** TruthLens — AI-Based Fake Product Review Detection & Forensic Linguistic Analysis
- **Team & Roles:** 5-member pipeline (UI Engineering, ML Pipeline, Backend API, Integration Testing, Packaging & Deployment).
- **Core Problem:** The proliferation of deceptive online reviews, sponsored astroturfing, and automated spam that mislead consumers and distort e-commerce trust.
- **Solution:** A real-time, explainable AI web application combining machine learning (Support Vector Machine / Naive Bayes on TF-IDF), deterministic Tier-1 spam filtration, sentiment contrast detection, and token attribution.

### Slide 2: High-Level Architecture
- **Three-Tier Architecture:**
  1. *Frontend:* Next.js 14 (App Router, Tailwind CSS, Framer Motion, Recharts).
  2. *Backend API:* FastAPI with Pydantic v2 schemas, SQLite history persistence.
  3. *Inference & Forensic Engine:*
     - *Production Classifier:* Support Vector Machine with RBF kernel ($C=3.0$, $\gamma=\text{scale}$) trained on TF-IDF features, with probability calibration via Platt scaling (`CalibratedClassifierCV`), alongside a Multinomial Naive Bayes baseline.
     - *Auxiliary Explainer:* A companion Linear SVM (`LinearSVC`) model fitted separately and used exclusively for `/api/explain` token attribution.
     - *Heuristics:* Rule-based Tier-1 spam filtration and NLTK VADER sentiment contrast detection.
- **Design Philosophy:** Strict parity between training and inference preprocessing (`backend/ml/` as single source of truth; zero duplicate text-cleaning code).

### Slide 3: Dataset & Data Integrity
- **Corpus:** *Deceptive Opinion Spam Corpus* (Ott et al., 2011, Cornell University).
- **Corpus Domain:** 1,596 English hotel reviews (Chicago hotels). Generalization to retail consumer product reviews (e.g., electronics, cosmetics, apparel) has not been empirically established and may exhibit domain shift.
- **Data Partition:** 1,276 training samples (79.95%) and 320 held-out test samples (20.05%).
- **Class Distribution:** Approximately 50.13% deceptive (800 reviews) and 49.87% genuine (796 reviews).
- **Data Leakage Prevention:** Vectorizers and scalers fitted *strictly* on training splits within 5-fold stratified cross-validation; zero test set leakage.
- **Preprocessing:** Negation words (`not`, `no`, `never`, `cannot`, `barely`, `without`) explicitly preserved during stopword filtering, retaining sentiment polarity and reversal signals.

### Slide 4: Feature Engineering Strategy
- **Evaluated Feature Sets:**
  - *TF-IDF Vectorization:* Sublinear term frequency scaling `(1 + log(tf))` with unigram and bigram `(1, 2)` extraction across 20,000 max features, `min_df=2`, `max_df=0.9`.
  - *Sentiment & Stylometric Meta-Features:* Evaluated variant combining TF-IDF with VADER sentiment scores (compound, positive, neutral, negative) and 6 standardized stylometric features (character count, word length, exclamation counts, uppercase ratio, digit presence, average word length).
- **Active Production Configuration:**
  - The deployed production model uses **TF-IDF only** (`tfidf_only`).
  - While TF-IDF + Sentiment was also evaluated during experimentation, sentiment and stylometric features are **not active in the deployed production classifier**, eliminating runtime feature extraction overhead while matching peak test accuracy (88.75%) and achieving the highest test recall (92.50%).
  - VADER sentiment is extracted separately for UI display and heuristic flag detection, but is not passed to the production classifier.

### Slide 5: Machine Learning Models & Evaluation
- **Classifiers Evaluated:**
  - *Multinomial Naive Bayes:* Fast probabilistic baseline (85.62% accuracy on TF-IDF; 87.81% on TF-IDF + Sentiment).
  - *Support Vector Machine (RBF kernel):* Active production classifier with RBF kernel ($C=3.0$, $\gamma=\text{scale}$) trained on TF-IDF only, achieving **88.75% test accuracy**, **86.05% precision**, **92.50% recall**, **89.16% F1**, and **0.9432 ROC-AUC**.
  - *Support Vector Machine (Linear kernel):* Evaluated on TF-IDF + Sentiment (88.75% accuracy, 0.9477 ROC-AUC).
- **Production vs. Explanation Model:**
  - The production classifier is an SVM with **RBF kernel** on TF-IDF only.
  - An auxiliary **Linear SVM** (`LinearSVC(C=1.0)`) companion model is maintained separately and used strictly for `/api/explain` linear token attribution.
- **Probability Calibration:**
  - Platt scaling (`CalibratedClassifierCV` using sigmoid calibration) transforms raw SVM decision function values into calibrated probability estimates between 0 and 1 for the UI confidence meter.

### Slide 6: Phase 3.5 Advanced Capabilities
- **Feature 1 — Tier-1 Hard Rule Filter:** Deterministic safety net catching velocity spam (>5 reviews/minute from the same user/IP) and duplicate text floods ($\ge 3$ identical reviews in 10 minutes) before the ML model runs, saving CPU inference compute. Short-circuits with `decision_source: 'tier1_rules'`. (Note: Deterministic heuristic; precision and recall have not been measured on an annotated evaluation benchmark).
- **Feature 2 — Sarcasm Risk Flag:** Detects contrast between positive text openings and sharp negative ratings/outcomes. Operates strictly as an informational risk flag for human moderation without altering the ML prediction verdict or probability. (Heuristic indicator, not proof of fraud).
- **Feature 3 — Explainability Architecture:**
  - On-demand token attribution via `/api/explain`.
  - In Docker Compose, `ENABLE_SHAP=false` is set by default to avoid heavy runtime overhead. The API falls back to fast linear coefficient attribution ($w_i \cdot x_i$) on the auxiliary Linear SVM (`linear-coefficients`), or log-probability differences for Naive Bayes (`naive-bayes-logprob`).
  - SVM token attribution reflects the auxiliary linear companion model, not the non-linear production RBF decision boundary.

### Slide 7: System Integration & Performance
- **Verified Latency & Throughput:**
  - Single-review inference: **10.3 ms** average latency across 20 inputs.
  - Batch processing: **1,000 reviews analyzed in 2.68–2.92 seconds** with zero errors.
- **Accessibility & Responsiveness:**
  - **Lighthouse Accessibility score: 100/100** across three core pages (`/`, `/analyze`, `/batch`) in both light and dark themes. (Note: Automated Lighthouse audits verify structural accessibility, contrast, and ARIA attributes; not a claim of universal manual WCAG AA compliance).
  - **Zero horizontal overflow** tested and confirmed at 360px (mobile), 768px (tablet), and 1440px (desktop) viewports.
  - Theme toggle supporting light and dark modes with persistent local storage.

### Slide 8: Packaging, Containerization & Portability
- **Docker Multi-Stage Build & Container Sizing:**
  - *Frontend Container:* Multi-stage Next.js build using `output: "standalone"` running as non-root `nodejs:nodejs` (UID 1001), measured at **226 MB**. The standalone build traces application dependencies and bundles only the required server files and minimal node modules without build tooling.
  - *Backend Container:* Python 3.11 slim image containing FastAPI, scikit-learn, and pre-cached NLTK corpora (`vader_lexicon`, `stopwords`, `punkt`, `punkt_tab`) with `/api/health` probes, measured at **1.01 GB**.
- **Docker Compose Orchestration:**
  - One-command orchestration (`docker compose up --build`).
  - Named Docker volume (`truthlens_db_data`) persisting SQLite history across container rebuilds.
  - Read-only bind mount for `backend/models` artifacts.
  - Startup dependency: frontend waits for backend healthcheck to pass before accepting traffic.

### Slide 9: Honest Limitations
- **Domain Shift:** Trained and evaluated strictly on English hotel reviews from the Ott et al. (2011) corpus. Generalization to retail consumer product reviews (e.g., electronics, cosmetics, apparel) has not been established and may exhibit domain shift without retraining or domain adaptation.
- **Language Scope:** Monolingual English only; non-English and code-mixed (e.g., Hinglish) reviews are not supported by the TF-IDF vocabulary.
- **Heuristics Disclaimer:** Tier-1 rules and sarcasm detection are deterministic heuristics whose precision and recall have not been measured on an annotated test benchmark. They are defensive guardrails and moderation flags, not proof of fraud.
- **In-Memory State:** Tier-1 velocity tracking is maintained in-memory per worker process and resets upon server restart.

### Slide 10: Future Roadmap & Conclusion
- **Transformer Fine-Tuning:** Integration of contextual models (e.g., RoBERTa or domain-adapted transformers) for nuanced semantic understanding.
- **LLM-Generated Content Detection:** Perplexity and burstiness detectors targeting synthetic text generated by modern commercial LLMs.
- **Distributed Architecture:** Migrating in-memory Tier-1 tracking to Redis sliding windows and decoupling batch jobs via Celery/RabbitMQ for enterprise-scale traffic.
- **Browser Extension:** Chrome extension for on-page review verification on retail e-commerce platforms.

---

## 2. Three-Minute Live Demo Script

| Time | Target Screen | Action / What to Click | Spoken Narration |
| :---: | :--- | :--- | :--- |
| **0:00 – 0:30** | `/` (Landing) | Start at root landing page. Point out "API online" badge and navigation cards. Click **"Analyze a review"**. | *"Welcome to TruthLens. Here is our landing page showcasing live system status and core capabilities. Let's begin by analyzing an individual review."* |
| **0:30 – 1:00** | `/analyze` | Paste promotional fake text: *"OMG this is the BEST hotel EVER! Amazing quality, life changing, book it NOW! 5 stars!"* Click **Analyze Review**. | *"Notice the live classification output: TruthLens flags this as 'Likely Fake'. We show the live confidence gauge, the evidence tokens highlighted by our explanation engine, and the heuristic flags detecting exaggerated sentiment and formatting anomalies."* |
| **1:00 – 1:30** | `/analyze` | Paste genuine review with balanced critique: *"We stayed 3 nights in room 214. The bathroom was clean but the air conditioner was loud and wifi failed in the evening."* Click **Analyze Review**. | *"Now we test a balanced genuine review with specific details. TruthLens classifies this as 'Likely Genuine'. Show the live confidence score and how our pipeline evaluates balanced critique without mistaking negative sentiment for deception."* |
| **1:30 – 2:00** | `/analyze` | Open **Advanced — reviewer context**. Enter `reviews_last_minute: 9`. Click **Analyze Review**. | *"Here is our Phase 3.5 Tier-1 filter. A reviewer submitting 9 reviews per minute trips our VELOCITY_EXCEEDED hard rule. Point out that the system resolves this via rule heuristics (`decision_source: tier1_rules`) without executing ML model inference, saving CPU compute."* |
| **2:00 – 2:30** | `/batch` | Navigate to `/batch`. Drag and drop `batch_sample.csv`. Show results table and filters. | *"In the Batch tab, we upload a multi-row CSV. Point out the live processing progress, summary metric cards (total, fake, genuine), filter tabs, and the CSV export option."* |
| **2:30 – 3:00** | `/model-lab` & `/history` | Show Model Lab metrics and ROC curves, then open `/history` to demonstrate audit logging. | *"Finally, Model Lab provides live transparency into our SVM and Naive Bayes metrics directly from metrics.json. The History tab maintains a persistent SQLite audit log of every scan with search and verdict filtering."* |

---

## 3. Fourteen Technical Viva Questions & Model Answers

### Q1: Why use TF-IDF instead of simple word counts or Bag of Words?
**Answer:** Simple Bag-of-Words counts raw frequency, causing common non-informative words to dominate. TF-IDF penalizes words that appear ubiquitously across documents while rewarding terms that are uniquely characteristic of specific documents, highlighting distinctive deceptive or genuine lexical markers.

### Q2: What is the fundamental difference between Naive Bayes and Support Vector Machines for text classification?
**Answer:** Naive Bayes is a generative, probabilistic model that assumes conditional feature independence given the class label. SVM is a discriminative model that constructs an optimal maximum-margin hyperplane in high-dimensional feature space without making independence assumptions, yielding stronger classification boundaries on overlapping text features.

### Q3: What is a Confusion Matrix and what do False Positives vs. False Negatives mean in this project?
**Answer:** A confusion matrix tabulates predicted vs. actual class labels:
- **True Negative (TN):** Genuine review correctly identified as genuine (136 on test set for production SVM).
- **False Positive (FP):** Genuine review falsely flagged as fake (24 on test set; damages honest seller reputation).
- **False Negative (FN):** Deceptive review missed and labelled genuine (12 on test set; misleads consumers).
- **True Positive (TP):** Deceptive review correctly identified as fake (148 on test set).

### Q4: Why is probability calibration (Platt scaling) used for the SVM classifier?
**Answer:** An SVM (`SVC`) optimizes a geometric margin and outputs uncalibrated decision function distances, not probabilities. Wrapping the estimator in `CalibratedClassifierCV(method="sigmoid")` fits a logistic sigmoid mapping (Platt scaling) using cross-validation to produce calibrated probability estimates between 0 and 1 for the UI confidence meter. Note that while Platt scaling provides well-calibrated empirical probability estimates for ranking and confidence display, it does not guarantee exact theoretical Bayesian posterior probabilities.

### Q5: How was data leakage strictly prevented during pipeline training?
**Answer:** Preprocessing transformations, TF-IDF vectorizers, and feature scalers were fitted *only* on training splits within 5-fold stratified cross-validation. The 320-sample test set was held out completely until final evaluation and only transformed using the pre-fitted estimators.

### Q6: Why are negation words preserved in stopword filtering?
**Answer:** Standard stopword lists discard words like `not`, `no`, `never`, and `without`. In sentiment and fake review analysis, negations invert polarity (e.g., *"not clean"* vs. *"clean"*). Stripping them destroys grammatical context and misleads the classifier.

### Q7: Why does the Tier-1 rule filter execute before the machine learning model?
**Answer:** Obvious automated flood behavior (e.g., a single user posting >5 reviews in a minute or submitting duplicate review text) can be intercepted immediately. Executing deterministic heuristic rules first catches high-frequency abuse early and skips unnecessary text preprocessing, feature vectorization, and CPU ML inference. Note that heuristic flags are operational risk safeguards, not definitive proof of fraud.

### Q8: Why doesn't the sarcasm detection flag automatically change the fake verdict?
**Answer:** Sarcasm is a rhetorical tone, not proof of fraud. Genuine paying customers frequently use sarcasm when angry or disappointed (e.g., *"Great phone, broke in one day"*). Flagging sarcasm provides an informational risk indicator for human moderation without erroneously altering the ML model's prediction or penalizing genuine buyers.

### Q9: How does token attribution work in TruthLens, and what is the role of the auxiliary Linear SVM?
**Answer:** The production classifier uses an RBF kernel, whose non-linear decision boundary cannot be decomposed into a single vector of static per-token weights. TruthLens therefore trains an auxiliary Linear SVM companion model (`LinearSVC`) specifically for `/api/explain`. In Docker Compose, `ENABLE_SHAP=false` is set by default to keep the service fast and lightweight; when SHAP is disabled, `/api/explain` falls back to direct linear coefficient attribution ($w_i \cdot x_i$) on this auxiliary model (or log-probability differences for Naive Bayes). Token explanations thus approximate linear feature contributions rather than representing exact mathematical Shapley values of the production RBF boundary.

### Q10: What are the primary limitations of the current TruthLens implementation?
**Answer:** 
1. **Domain Sensitivity:** Trained and evaluated on Chicago hotel reviews (Ott et al., 2011); generalization to retail consumer product reviews (electronics, clothing, etc.) has not been established.
2. **Language Scope:** Monolingual English only; non-English and Hinglish text are not supported by the TF-IDF vocabulary.
3. **In-Memory Tracking:** Tier-1 velocity counters are tracked in-memory per worker process and reset on process restart.
4. **Heuristic Nature of Rules:** Tier-1 and sarcasm filters are deterministic heuristics without measured precision/recall benchmarks; they are risk indicators, not proof of fraud.
5. **Approximated Probabilities:** Platt-calibrated values are empirical probability approximations, not guaranteed exact Bayesian posteriors.

### Q11: How does TruthLens avoid server startup race conditions in Docker Compose?
**Answer:** The backend container defines a native Docker health check probing `/api/health`. The frontend container uses `depends_on` with `condition: service_healthy`, ensuring Next.js starts only after FastAPI has loaded all `.pkl` models and initialized the SQLite schema.

### Q12: Why is Next.js built with `output: "standalone"` in Docker?
**Answer:** `output: "standalone"` traces the Next.js application dependency graph and bundles only the necessary production server files, public assets, and minimal node_modules, omitting dev dependencies and unnecessary build tooling. This produces a lean 226 MB production image for the frontend container (compared to the 1.01 GB backend image that bundles Python, scikit-learn, and pre-cached NLTK corpora).

### Q13: Why is star rating not used as an explicit feature in the ML model?
**Answer:** Deceptive reviews frequently mimic 5-star promotional ratings or 1-star competitor sabotage. Including star ratings directly as an ML feature creates bias and encourages overfitting. Instead, star rating is compared against VADER text sentiment to detect divergence heuristics.

### Q14: How would you scale the TruthLens architecture for millions of daily reviews?
**Answer:** 
1. Decouple inference using asynchronous task queues (e.g., Celery with Redis or RabbitMQ).
2. Move Tier-1 velocity tracking from in-memory process dictionaries to a distributed Redis sliding window.
3. Deploy stateless FastAPI backend instances behind a load balancer (NGINX or Traefik).
4. Serve the model using high-throughput CPU model serving runtimes such as ONNX Runtime or Triton Inference Server.
