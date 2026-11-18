# TruthLens Model Evaluation & Performance Report

> **Generated from:** `backend/models/metrics.json`  
> **Pipeline Run Timestamp:** `2026-11-02T13:34:48.517691+00:00`  
> **Production Best Model:** **Support Vector Machine (RBF kernel)** (`svm`)  
> **Production Active Feature Set:** `tfidf_only` (TF-IDF only)

---

## 1. Dataset Overview

The TruthLens classification pipeline was evaluated on the **Deceptive Opinion Spam Corpus (Ott et al., 2011)**.

| Property | Value |
| :--- | :--- |
| **Corpus Name** | Deceptive Opinion Spam Corpus (Ott et al., 2011) |
| **Total Labeled Reviews** | 1,596 |
| **Training Set Size** | 1,276 (79.95%) |
| **Test Set Size** | 320 (20.05%) |
| **Deceptive / Fake Proportion** | 50.1253% |
| **Genuine / Truthful Proportion** | 49.8747% |
| **Average Words per Review** | 148.718 words |

The evaluation corpus contains 1,596 total labeled reviews, partitioned into 1,276 training samples (79.95%) and 320 held-out test samples (20.05%). The class distribution is 50.13% deceptive and 49.87% genuine, representing a balanced binary classification task with an average review length of 148.72 words.

---

## 2. Methodology & Feature Extraction

### A. Text Preprocessing & Cleaning
- **Lowercasing & Normalization:** Converts review text to lowercase while retaining structural punctuation.
- **Negation Preservation:** Standard stopwords are removed, but negation tokens (`not`, `no`, `never`, `cannot`, `barely`, `without`, etc.) are explicitly retained to preserve sentiment reversals and deceptive veracity indicators.
- **Whitespace & Entity Normalization:** Hyperlinks, email addresses, and redundant whitespace characters are stripped.

### B. TF-IDF (Term Frequency – Inverse Document Frequency)
TF-IDF features capture n-gram statistical importance across the corpus relative to per-document frequency:
- **N-gram Range:** Unigrams and bigrams `(1, 2)` to capture descriptive phrases (e.g. *'great stay'*, *'never return'*).
- **Sublinear TF Scaling:** Logarithmic frequency scaling `1 + log(tf)` to moderate the impact of high-frequency repeated terms.
- **Document Frequency Bounds:** `min_df=2` (filters isolated singletons) and `max_df=0.9` (filters ubiquitous terms).
- **Feature Budget:** Capped at 20,000 maximum features for efficient vectorization and low memory footprint.

### C. VADER Sentiment & Lexical Meta-Features
Deceptive reviews frequently exhibit emotional exaggeration or sentiment misalignment. VADER (Valence Aware Dictionary and sEntiment Reasoner) provides rule-based sentiment scores tuned to opinion text:
- Four sentiment scores: Positive (`vader_pos`), Neutral (`vader_neu`), Negative (`vader_neg`), and Normalized Compound (`vader_compound`).
- Six lexical meta-features: Character count, word count, exclamation mark frequency, uppercase word ratio, presence of digits, and average word length.
- All dense meta-features are standardized using `StandardScaler` fitted strictly on the training partition.

### D. Machine Learning Classifiers
1. **Multinomial Naive Bayes (NB):** Probabilistic classifier based on Bayes' theorem under feature independence assumptions. Highly efficient for high-dimensional sparse text vectors, tuned across Laplace smoothing parameter `alpha`.
2. **Support Vector Machine (SVM):** Maximum-margin classification using `sklearn.svm.SVC` tuned via grid search over regularization parameter `C`, kernel function (`linear` or `rbf`), and kernel coefficient `gamma`. To produce calibrated class posterior probabilities for confidence scoring, the fitted model is calibrated with `CalibratedClassifierCV` (sigmoid Platt scaling). An auxiliary linear model (`LinearSVC`) is separately fitted to supply direct linear weights for token highlight explanations.

---

## 3. Comprehensive Performance Metrics

Below are the verified empirical test metrics evaluated on the held-out test partition (320 reviews):

| Model | Feature Set | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Best Hyperparameters |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Multinomial NB** | TF-IDF only | **85.62%** | 83.93% | 88.12% | 85.98% | 0.9325 | `{"alpha": 0.1}` |
| **Multinomial NB** | TF-IDF + Sentiment | **87.81%** | 86.23% | 90.00% | 88.07% | 0.9351 | `{"alpha": 0.1}` |
| **SVM (RBF kernel)** | TF-IDF only | **88.75%** | 86.05% | 92.50% | 89.16% | 0.9432 | `{"C": 3.0, "gamma": "scale", "kernel": "rbf"}` |
| **SVM (Linear kernel)** | TF-IDF + Sentiment | **88.75%** | 87.35% | 90.62% | 88.96% | 0.9477 | `{"C": 3.0, "gamma": "scale", "kernel": "linear"}` |

---

## 4. Confusion Matrix Analysis

The 2x2 confusion matrix maps `[[True Negative, False Positive], [False Negative, True Positive]]`:
- **Negative (Class 0):** Genuine review
- **Positive (Class 1):** Deceptive / Fake review

### Multinomial NB (TF-IDF only)
- **True Negatives (Genuine identified as Genuine):** 133
- **False Positives (Genuine misclassified as Fake):** 27
- **False Negatives (Fake misclassified as Genuine):** 19
- **True Positives (Fake identified as Fake):** 141
- **Total Test Samples:** 320

### Multinomial NB (TF-IDF + Sentiment)
- **True Negatives (Genuine identified as Genuine):** 137
- **False Positives (Genuine misclassified as Fake):** 23
- **False Negatives (Fake misclassified as Genuine):** 16
- **True Positives (Fake identified as Fake):** 144
- **Total Test Samples:** 320

### SVM (RBF kernel, TF-IDF only) - Production Default
- **True Negatives (Genuine identified as Genuine):** 136
- **False Positives (Genuine misclassified as Fake):** 24
- **False Negatives (Fake misclassified as Genuine):** 12
- **True Positives (Fake identified as Fake):** 148
- **Total Test Samples:** 320

### SVM (Linear kernel, TF-IDF + Sentiment)
- **True Negatives (Genuine identified as Genuine):** 139
- **False Positives (Genuine misclassified as Fake):** 21
- **False Negatives (Fake misclassified as Genuine):** 15
- **True Positives (Fake identified as Fake):** 145
- **Total Test Samples:** 320

---

## 5. Comparative Analysis & Model Selection

### Naive Bayes vs. Support Vector Machine
1. **Overall Accuracy & F1-Score:**
   - On TF-IDF features alone, SVM (RBF kernel) achieves an accuracy of 88.75%, outperforming Multinomial NB (85.62%) by **3.13 percentage points**. SVM (RBF kernel) achieves a higher F1-score of **89.16%** vs. **85.98%** for Multinomial NB.
   - SVM (RBF kernel) achieves a higher recall (92.50% vs. 88.12%), allowing 12 deceptive reviews to pass undetected compared to 19 for Multinomial NB. In content moderation, minimizing false negatives is vital to prevent deceptive reviews from misleading consumers.
2. **Impact of Sentiment & Meta-Features:**
   - **Multinomial Naive Bayes:** Incorporating VADER sentiment scores and lexical meta-features changes accuracy from 85.62% to 87.81% (+2.19 percentage points). Recall moves from 88.12% to 90.00%, shifting false negatives from 19 to 16.
   - **Support Vector Machine:** Tuning hyperparameters for SVM on TF-IDF selected SVM (RBF kernel), whereas tuning on TF-IDF + Sentiment selected SVM (Linear kernel). The sentiment-augmented variant achieves 88.75% accuracy (+0.00 percentage points relative to SVM (RBF kernel)), precision of 87.35% (vs. 86.05%), recall of 90.62% (vs. 92.50%), and ROC-AUC of 0.9477 (vs. 0.9432), resulting in 15 false negatives compared to 12.
3. **Production Model Selection:**
   - The production pipeline designates **Support Vector Machine (RBF kernel)** with **TF-IDF only** (`tfidf_only`) as the active classifier based on empirical evaluation.
   - The production configuration achieves **88.75%** test accuracy, matching the maximum accuracy observed across all evaluated models (tied with SVM (Linear kernel) with TF-IDF + Sentiment).
   - It achieves the highest test recall across all evaluated models at **92.50%**, minimizing false negatives to 12 undetected deceptive reviews.
   - On the held-out test partition of 320 reviews, this configuration produced 148 true positives, 136 true negatives, 24 false positives, and 12 false negatives.
   - Operating on TF-IDF only avoids additional runtime feature extraction steps: VADER sentiment extraction and dense lexical feature standardization are not required, keeping the prediction workflow direct.

---

## 6. Advanced Features & Limitations (Phase 3.5)

> [!IMPORTANT]
> **Tier-1 Rule Filter and Sarcasm Risk Detection are Heuristics:**
> - The Tier-1 rule filter (`VELOCITY_EXCEEDED`, `DUPLICATE_FLOOD`, `VERY_SHORT`, `LINK_OR_CONTACT_SPAM`, `REPEATED_CHARACTERS`) and the sarcasm contrast detector (`SARCASM_SUSPECTED`) are deterministic heuristic safety nets.
> - **Their precision and recall have NOT been measured on an annotated evaluation corpus**, and no statistical accuracy is claimed for these rules.
> - Hard rules intentionally short-circuit the ML classifier (`decision_source: 'tier1_rules'`) to handle deterministic anomalies immediately without executing ML inference.
> - Sarcasm detection operates strictly as an informational risk flag for human moderation; it never mutates the underlying ML verdict.

### General Model Limitations
1. **Domain Sensitivity:** The evaluation corpus comprises English hotel reviews from the Ott et al. (2011) dataset. Performance on retail consumer product reviews (e.g. electronics, cosmetics, apparel, home goods) has not been established by this dataset and may exhibit domain shift without retraining or domain adaptation.
2. **Language Scope:** The classifier operates exclusively on English text. Non-English and code-mixed reviews are not supported by the TF-IDF vocabulary.
3. **LLM-Generated Content:** The pipeline targets human-written deceptive opinion spam; highly sophisticated LLM-generated synthetic reviews may exhibit lexical fluency that bypasses n-gram frequency markers.

---

## 7. Conclusion

The TruthLens machine learning pipeline demonstrates strong empirical capability on deceptive text detection. The production system deploys **Support Vector Machine (RBF kernel)** trained on the **`tfidf_only`** feature set, as defined by `best_model` and `active_feature_set` in `backend/models/metrics.json`.

### Production Model Performance Summary
- **Model:** Support Vector Machine (RBF kernel)
- **Active Feature Set:** `tfidf_only` (TF-IDF only)
- **Test Accuracy:** **88.75%** (284 of 320 test samples correctly classified)
- **Precision:** **86.05%** (148 true positives out of 172 positive predictions)
- **Recall:** **92.50%** (148 true positives out of 160 actual deceptive reviews)
- **F1-Score:** **89.16%**
- **ROC-AUC:** **0.9432**
- **Confusion Matrix:** 136 True Negatives, 24 False Positives, 12 False Negatives, 148 True Positives

### Understanding the Metrics: Accuracy vs. ROC-AUC
- **Accuracy (88.75%):** Represents the proportion of correct classifications (284 of 320 test reviews) evaluated using the model's default decision boundary (`predict()`). It reflects operational classification performance on the held-out test partition.
- **ROC-AUC (0.9432):** Evaluates threshold-independent discriminative ability across all possible classification boundaries by measuring the trade-off between the true positive rate and the false positive rate. An AUC of 0.9432 indicates that a randomly selected deceptive review has a 94.32% probability of receiving a higher deceptive score than a randomly selected genuine review.

### Model Selection Context
- **Highest Accuracy Configuration:** The peak test accuracy of 88.75% was achieved by SVM (RBF kernel) with TF-IDF only (88.75%), SVM (Linear kernel) with TF-IDF + Sentiment (88.75%).
- **Highest ROC-AUC Configuration:** SVM (Linear kernel) with TF-IDF + Sentiment (0.9477).
- **Highest Recall Configuration:** SVM (RBF kernel) with TF-IDF only (92.50%).
- **Production Configuration:** SVM (RBF kernel) with TF-IDF only (`tfidf_only`).
- **Production Ranking Alignment:** The production configuration matches the highest test accuracy (88.75%), but ranks below the highest ROC-AUC configuration (SVM (Linear kernel) with TF-IDF + Sentiment (0.9477) vs. 0.9432).
- **Selection Synthesis:** Production designates **Support Vector Machine (RBF kernel)** with **`tfidf_only`** because it simultaneously matches the peak test accuracy (88.75%) and delivers the highest test recall (92.50%), minimizing undetected deceptive reviews to 12 false negatives while avoiding additional runtime preprocessing dependencies required by dense sentiment analysis and feature standardization.
