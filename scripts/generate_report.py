#!/usr/bin/env python3
"""
TruthLens Model Report Generator.

Reads backend/models/metrics.json and writes docs/MODEL_REPORT.md with:
- Dataset summary derived dynamically from metrics.json
- Feature extraction & algorithm explanations (TF-IDF, Naive Bayes, SVM, VADER)
- Performance metrics table for all models and feature sets
- Plain-language comparative analysis with dynamic calculations
- Phase 3.5 heuristic notes (Tier-1 and Sarcasm have no measured accuracy)
- Production model conclusion based on best_model and active_feature_set

Only real values from metrics.json are used. All metrics, kernel descriptions,
comparisons, rankings, and conclusions are derived dynamically from the source JSON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS_FILE = ROOT / "backend" / "models" / "metrics.json"
OUTPUT_FILE = ROOT / "docs" / "MODEL_REPORT.md"


def load_metrics() -> dict:
    if not METRICS_FILE.exists():
        print(f"Error: metrics file not found at {METRICS_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def format_pct(val: float) -> str:
    """Format a ratio as a percentage string (e.g. 0.8875 -> '88.75%')."""
    return f"{val * 100:.2f}%"


def get_kernel_name(params: dict) -> str:
    """Extract and format the kernel name from hyperparameters if present."""
    k = params.get("kernel")
    if not k:
        return ""
    k_str = str(k).strip()
    return "RBF" if k_str.lower() == "rbf" else k_str.capitalize()


def get_model_name(model_key: str, params: dict, short: bool = False) -> str:
    """Derive human-readable model name incorporating kernel information."""
    kernel = get_kernel_name(params)
    if model_key == "nb":
        return "Multinomial NB" if short else "Multinomial Naive Bayes"
    if model_key == "svm":
        if kernel:
            return f"SVM ({kernel} kernel)" if short else f"Support Vector Machine ({kernel} kernel)"
        return "SVM" if short else "Support Vector Machine"
    return model_key.upper()


def get_cm_counts(block: dict) -> tuple[int, int, int, int, int]:
    """Extract (tn, fp, fn, tp, total) from confusion_matrix: [[tn, fp], [fn, tp]]."""
    cm = block.get("confusion_matrix", [[0, 0], [0, 0]])
    tn = int(cm[0][0]) if len(cm) > 0 and len(cm[0]) > 0 else 0
    fp = int(cm[0][1]) if len(cm) > 0 and len(cm[0]) > 1 else 0
    fn = int(cm[1][0]) if len(cm) > 1 and len(cm[1]) > 0 else 0
    tp = int(cm[1][1]) if len(cm) > 1 and len(cm[1]) > 1 else 0
    total = tn + fp + fn + tp
    return tn, fp, fn, tp, total


def format_fs_label(fs_key: str) -> str:
    """Format feature set key to a human-readable title."""
    if fs_key == "tfidf_only":
        return "TF-IDF only"
    if fs_key == "tfidf_sentiment":
        return "TF-IDF + Sentiment"
    return fs_key.replace("_", " ").title()


def get_model_section_header(model_key: str, params: dict, fs_label: str, is_prod: bool) -> str:
    """Format clean section headers without redundant nested parentheses."""
    kernel = get_kernel_name(params)
    prod_tag = " - Production Default" if is_prod else ""
    if model_key == "nb":
        return f"### Multinomial NB ({fs_label}){prod_tag}"
    if model_key == "svm":
        if kernel:
            return f"### SVM ({kernel} kernel, {fs_label}){prod_tag}"
        return f"### SVM ({fs_label}){prod_tag}"
    return f"### {model_key.upper()} ({fs_label}){prod_tag}"


def generate_markdown(m: dict) -> str:
    ds = m.get("dataset", {})
    models = m.get("models", {})
    best_model_key = m.get("best_model", "svm")
    active_fs = m.get("active_feature_set", "tfidf_only")

    # Dataset properties derived from metrics.json
    ds_name = ds.get("name", "Deceptive Opinion Spam Corpus")
    total_size = ds.get("size", 0)
    train_size = ds.get("train_size", 0)
    test_size = ds.get("test_size", 0)
    fake_pct = ds.get("fake_percent", 0.0)
    genuine_pct = max(0.0, 100.0 - fake_pct)
    avg_words = ds.get("avg_words", 0.0)
    train_pct = (train_size / total_size * 100.0) if total_size else 0.0
    test_pct = (test_size / total_size * 100.0) if total_size else 0.0

    # Collect all model/feature-set entries for tables, rankings, and comparisons
    model_order = [k for k in ["nb", "svm"] if k in models] + [k for k in models if k not in ["nb", "svm"]]
    fs_order = ["tfidf_only", "tfidf_sentiment"]

    all_configs = []
    for m_k in model_order:
        fs_dict = models.get(m_k, {})
        ordered_fs = [fs for fs in fs_order if fs in fs_dict] + [fs for fs in fs_dict if fs not in fs_order]
        for fs_k in ordered_fs:
            blk = fs_dict[fs_k]
            params = blk.get("best_params", {})
            m_name = get_model_name(m_k, params, short=True)
            m_title = get_model_name(m_k, params, short=False)
            fs_title = format_fs_label(fs_k)
            tn, fp, fn, tp, tot = get_cm_counts(blk)
            all_configs.append({
                "model_key": m_k,
                "feature_set": fs_k,
                "name": f"{m_name} with {fs_title}",
                "short_name": f"{m_name} ({fs_title})",
                "model_title": m_title,
                "model_name": m_name,
                "feature_set_label": fs_title,
                "params": params,
                "accuracy": float(blk.get("accuracy", 0.0)),
                "precision": float(blk.get("precision", 0.0)),
                "recall": float(blk.get("recall", 0.0)),
                "f1": float(blk.get("f1", 0.0)),
                "roc_auc": float(blk.get("roc_auc", 0.0)),
                "tn": tn,
                "fp": fp,
                "fn": fn,
                "tp": tp,
                "total": tot,
            })

    # Dynamically calculate maximums and top configurations
    max_acc = max(c["accuracy"] for c in all_configs) if all_configs else 0.0
    max_rec = max(c["recall"] for c in all_configs) if all_configs else 0.0
    max_auc = max(c["roc_auc"] for c in all_configs) if all_configs else 0.0
    max_f1 = max(c["f1"] for c in all_configs) if all_configs else 0.0

    top_acc_configs = [c for c in all_configs if abs(c["accuracy"] - max_acc) < 1e-6]
    top_rec_configs = [c for c in all_configs if abs(c["recall"] - max_rec) < 1e-6]
    top_auc_configs = [c for c in all_configs if abs(c["roc_auc"] - max_auc) < 1e-6]

    # Locate production configuration
    prod_cfg = next(
        (c for c in all_configs if c["model_key"] == best_model_key and c["feature_set"] == active_fs),
        all_configs[0] if all_configs else None,
    )

    prod_model_title = prod_cfg["model_title"] if prod_cfg else "Support Vector Machine"
    prod_model_short = prod_cfg["model_name"] if prod_cfg else "SVM"
    prod_fs_label = prod_cfg["feature_set_label"] if prod_cfg else format_fs_label(active_fs)
    prod_acc = prod_cfg["accuracy"] if prod_cfg else 0.0
    prod_prec = prod_cfg["precision"] if prod_cfg else 0.0
    prod_recall = prod_cfg["recall"] if prod_cfg else 0.0
    prod_f1 = prod_cfg["f1"] if prod_cfg else 0.0
    prod_roc_auc = prod_cfg["roc_auc"] if prod_cfg else 0.0
    prod_tn = prod_cfg["tn"] if prod_cfg else 0
    prod_fp = prod_cfg["fp"] if prod_cfg else 0
    prod_fn = prod_cfg["fn"] if prod_cfg else 0
    prod_tp = prod_cfg["tp"] if prod_cfg else 0
    prod_total = prod_cfg["total"] if prod_cfg else 0
    prod_correct = prod_tp + prod_tn

    # Dynamic accuracy comparison of production vs maximum
    matches_max_acc = abs(prod_acc - max_acc) < 1e-6
    if matches_max_acc:
        if len(top_acc_configs) == 1:
            prod_acc_comp_str = f"The production configuration achieves the highest test accuracy across all evaluated models at **{format_pct(prod_acc)}**."
        else:
            other_acc_names = [c["name"] for c in top_acc_configs if c["name"] != prod_cfg["name"]]
            prod_acc_comp_str = f"The production configuration achieves **{format_pct(prod_acc)}** test accuracy, matching the maximum accuracy observed across all evaluated models (tied with {', '.join(other_acc_names)})."
    else:
        diff_pp = (max_acc - prod_acc) * 100.0
        top_acc_names = [c["name"] for c in top_acc_configs]
        prod_acc_comp_str = f"The production configuration achieves **{format_pct(prod_acc)}** test accuracy, which is {diff_pp:.2f} percentage points below the top-performing configuration ({format_pct(max_acc)} achieved by {', '.join(top_acc_names)})."

    # Dynamic recall comparison of production vs maximum
    matches_max_rec = abs(prod_recall - max_rec) < 1e-6
    if matches_max_rec:
        if len(top_rec_configs) == 1:
            prod_rec_comp_str = f"It achieves the highest test recall across all evaluated models at **{format_pct(prod_recall)}**, minimizing false negatives to {prod_fn} undetected deceptive reviews."
        else:
            other_rec_names = [c["name"] for c in top_rec_configs if c["name"] != prod_cfg["name"]]
            prod_rec_comp_str = f"It achieves **{format_pct(prod_recall)}** test recall, matching the highest recall observed across all evaluated models (tied with {', '.join(other_rec_names)})."
    else:
        rec_diff_pp = (max_rec - prod_recall) * 100.0
        top_rec_names = [c["name"] for c in top_rec_configs]
        prod_rec_comp_str = f"It achieves a test recall of **{format_pct(prod_recall)}**, which is {rec_diff_pp:.2f} percentage points below the maximum recall ({format_pct(max_rec)} achieved by {', '.join(top_rec_names)})."

    lines = [
        "# TruthLens Model Evaluation & Performance Report",
        "",
        f"> **Generated from:** `backend/models/metrics.json`  ",
        f"> **Pipeline Run Timestamp:** `{m.get('generated_at', 'N/A')}`  ",
        f"> **Production Best Model:** **{prod_model_title}** (`{best_model_key}`)  ",
        f"> **Production Active Feature Set:** `{active_fs}` ({prod_fs_label})",
        "",
        "---",
        "",
        "## 1. Dataset Overview",
        "",
        f"The TruthLens classification pipeline was evaluated on the **{ds_name}**.",
        "",
        "| Property | Value |",
        "| :--- | :--- |",
        f"| **Corpus Name** | {ds_name} |",
        f"| **Total Labeled Reviews** | {total_size:,} |",
        f"| **Training Set Size** | {train_size:,} ({train_pct:.2f}%) |",
        f"| **Test Set Size** | {test_size:,} ({test_pct:.2f}%) |",
        f"| **Deceptive / Fake Proportion** | {fake_pct:.4f}% |",
        f"| **Genuine / Truthful Proportion** | {genuine_pct:.4f}% |",
        f"| **Average Words per Review** | {avg_words:.3f} words |",
        "",
        f"The evaluation corpus contains {total_size:,} total labeled reviews, partitioned into {train_size:,} training samples ({train_pct:.2f}%) and {test_size:,} held-out test samples ({test_pct:.2f}%). The class distribution is {fake_pct:.2f}% deceptive and {genuine_pct:.2f}% genuine, representing a balanced binary classification task with an average review length of {avg_words:.2f} words.",
        "",
        "---",
        "",
        "## 2. Methodology & Feature Extraction",
        "",
        "### A. Text Preprocessing & Cleaning",
        "- **Lowercasing & Normalization:** Converts review text to lowercase while retaining structural punctuation.",
        "- **Negation Preservation:** Standard stopwords are removed, but negation tokens (`not`, `no`, `never`, `cannot`, `barely`, `without`, etc.) are explicitly retained to preserve sentiment reversals and deceptive veracity indicators.",
        "- **Whitespace & Entity Normalization:** Hyperlinks, email addresses, and redundant whitespace characters are stripped.",
        "",
        "### B. TF-IDF (Term Frequency – Inverse Document Frequency)",
        "TF-IDF features capture n-gram statistical importance across the corpus relative to per-document frequency:",
        "- **N-gram Range:** Unigrams and bigrams `(1, 2)` to capture descriptive phrases (e.g. *'great stay'*, *'never return'*).",
        "- **Sublinear TF Scaling:** Logarithmic frequency scaling `1 + log(tf)` to moderate the impact of high-frequency repeated terms.",
        "- **Document Frequency Bounds:** `min_df=2` (filters isolated singletons) and `max_df=0.9` (filters ubiquitous terms).",
        "- **Feature Budget:** Capped at 20,000 maximum features for efficient vectorization and low memory footprint.",
        "",
        "### C. VADER Sentiment & Lexical Meta-Features",
        "Deceptive reviews frequently exhibit emotional exaggeration or sentiment misalignment. VADER (Valence Aware Dictionary and sEntiment Reasoner) provides rule-based sentiment scores tuned to opinion text:",
        "- Four sentiment scores: Positive (`vader_pos`), Neutral (`vader_neu`), Negative (`vader_neg`), and Normalized Compound (`vader_compound`).",
        "- Six lexical meta-features: Character count, word count, exclamation mark frequency, uppercase word ratio, presence of digits, and average word length.",
        "- All dense meta-features are standardized using `StandardScaler` fitted strictly on the training partition.",
        "",
        "### D. Machine Learning Classifiers",
        "1. **Multinomial Naive Bayes (NB):** Probabilistic classifier based on Bayes' theorem under feature independence assumptions. Highly efficient for high-dimensional sparse text vectors, tuned across Laplace smoothing parameter `alpha`.",
        "2. **Support Vector Machine (SVM):** Maximum-margin classification using `sklearn.svm.SVC` tuned via grid search over regularization parameter `C`, kernel function (`linear` or `rbf`), and kernel coefficient `gamma`. To produce calibrated class posterior probabilities for confidence scoring, the fitted model is calibrated with `CalibratedClassifierCV` (sigmoid Platt scaling). An auxiliary linear model (`LinearSVC`) is separately fitted to supply direct linear weights for token highlight explanations.",
        "",
        "---",
        "",
        "## 3. Comprehensive Performance Metrics",
        "",
        f"Below are the verified empirical test metrics evaluated on the held-out test partition ({test_size} reviews):",
        "",
        "| Model | Feature Set | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Best Hyperparameters |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    # Dynamically populate table rows from actual JSON entries
    for c in all_configs:
        acc_str = format_pct(c["accuracy"])
        prec_str = format_pct(c["precision"])
        rec_str = format_pct(c["recall"])
        f1_str = format_pct(c["f1"])
        auc_str = f"{c['roc_auc']:.4f}"
        params_str = json.dumps(c["params"], sort_keys=True)
        lines.append(
            f"| **{c['model_name']}** | {c['feature_set_label']} | **{acc_str}** | {prec_str} | {rec_str} | {f1_str} | {auc_str} | `{params_str}` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Confusion Matrix Analysis",
        "",
        "The 2x2 confusion matrix maps `[[True Negative, False Positive], [False Negative, True Positive]]`:",
        "- **Negative (Class 0):** Genuine review",
        "- **Positive (Class 1):** Deceptive / Fake review",
        "",
    ])

    for c in all_configs:
        is_prod = (c["model_key"] == best_model_key and c["feature_set"] == active_fs)
        header = get_model_section_header(c["model_key"], c["params"], c["feature_set_label"], is_prod)
        lines.extend([
            header,
            f"- **True Negatives (Genuine identified as Genuine):** {c['tn']}",
            f"- **False Positives (Genuine misclassified as Fake):** {c['fp']}",
            f"- **False Negatives (Fake misclassified as Genuine):** {c['fn']}",
            f"- **True Positives (Fake identified as Fake):** {c['tp']}",
            f"- **Total Test Samples:** {c['total']}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 5. Comparative Analysis & Model Selection",
        "",
        "### Naive Bayes vs. Support Vector Machine",
    ])

    # Dynamic comparative analysis on TF-IDF
    nb_tfidf = models.get("nb", {}).get("tfidf_only", {})
    svm_tfidf = models.get("svm", {}).get("tfidf_only", {})
    if nb_tfidf and svm_tfidf:
        nb_t_name = get_model_name("nb", nb_tfidf.get("best_params", {}), short=True)
        svm_t_name = get_model_name("svm", svm_tfidf.get("best_params", {}), short=True)
        nb_t_acc = nb_tfidf.get("accuracy", 0.0)
        svm_t_acc = svm_tfidf.get("accuracy", 0.0)
        acc_diff_pp = (svm_t_acc - nb_t_acc) * 100.0
        svm_t_f1 = svm_tfidf.get("f1", 0.0)
        nb_t_f1 = nb_tfidf.get("f1", 0.0)
        svm_t_rec = svm_tfidf.get("recall", 0.0)
        nb_t_rec = nb_tfidf.get("recall", 0.0)
        _, _, svm_t_fn, _, _ = get_cm_counts(svm_tfidf)
        _, _, nb_t_fn, _, _ = get_cm_counts(nb_tfidf)

        # Dynamic accuracy statement: handles better, worse, or tied
        if abs(acc_diff_pp) < 0.001:
            acc_statement = f"On TF-IDF features alone, {svm_t_name} and {nb_t_name} achieve identical test accuracy of {format_pct(svm_t_acc)}."
        elif acc_diff_pp > 0:
            acc_statement = f"On TF-IDF features alone, {svm_t_name} achieves an accuracy of {format_pct(svm_t_acc)}, outperforming {nb_t_name} ({format_pct(nb_t_acc)}) by **{acc_diff_pp:.2f} percentage points**."
        else:
            acc_statement = f"On TF-IDF features alone, {nb_t_name} achieves an accuracy of {format_pct(nb_t_acc)}, outperforming {svm_t_name} ({format_pct(svm_t_acc)}) by **{abs(acc_diff_pp):.2f} percentage points**."

        # Dynamic F1 statement: handles better, worse, or tied
        f1_diff = svm_t_f1 - nb_t_f1
        if abs(f1_diff) < 0.0001:
            f1_statement = f"Both models achieve an identical F1-score of **{format_pct(svm_t_f1)}**."
        elif f1_diff > 0:
            f1_statement = f"{svm_t_name} achieves a higher F1-score of **{format_pct(svm_t_f1)}** vs. **{format_pct(nb_t_f1)}** for {nb_t_name}."
        else:
            f1_statement = f"{nb_t_name} achieves a higher F1-score of **{format_pct(nb_t_f1)}** vs. **{format_pct(svm_t_f1)}** for {svm_t_name}."

        # Dynamic recall statement: handles better, worse, or tied
        rec_diff = svm_t_rec - nb_t_rec
        if abs(rec_diff) < 0.0001:
            rec_statement = f"Both models demonstrate identical recall ({format_pct(svm_t_rec)}), each allowing {svm_t_fn} deceptive reviews to pass undetected."
        elif rec_diff > 0:
            rec_statement = f"{svm_t_name} achieves a higher recall ({format_pct(svm_t_rec)} vs. {format_pct(nb_t_rec)}), allowing {svm_t_fn} deceptive reviews to pass undetected compared to {nb_t_fn} for {nb_t_name}."
        else:
            rec_statement = f"{nb_t_name} achieves a higher recall ({format_pct(nb_t_rec)} vs. {format_pct(svm_t_rec)}), allowing {nb_t_fn} deceptive reviews to pass undetected compared to {svm_t_fn} for {svm_t_name}."

        lines.extend([
            "1. **Overall Accuracy & F1-Score:**",
            f"   - {acc_statement} {f1_statement}",
            f"   - {rec_statement} In content moderation, minimizing false negatives is vital to prevent deceptive reviews from misleading consumers.",
        ])

    lines.extend([
        "2. **Impact of Sentiment & Meta-Features:**",
    ])

    # Dynamic impact analysis for NB
    nb_sent = models.get("nb", {}).get("tfidf_sentiment", {})
    if nb_tfidf and nb_sent:
        nb_gain_pp = (nb_sent.get("accuracy", 0.0) - nb_tfidf.get("accuracy", 0.0)) * 100.0
        _, _, nb_s_fn, _, _ = get_cm_counts(nb_sent)
        lines.append(
            f"   - **Multinomial Naive Bayes:** Incorporating VADER sentiment scores and lexical meta-features changes accuracy from {format_pct(nb_tfidf.get('accuracy', 0.0))} to {format_pct(nb_sent.get('accuracy', 0.0))} ({nb_gain_pp:+.2f} percentage points). Recall moves from {format_pct(nb_tfidf.get('recall', 0.0))} to {format_pct(nb_sent.get('recall', 0.0))}, shifting false negatives from {nb_t_fn} to {nb_s_fn}."
        )

    # Dynamic impact analysis for SVM
    svm_sent = models.get("svm", {}).get("tfidf_sentiment", {})
    if svm_tfidf and svm_sent:
        svm_s_name = get_model_name("svm", svm_sent.get("best_params", {}), short=True)
        svm_gain_pp = (svm_sent.get("accuracy", 0.0) - svm_tfidf.get("accuracy", 0.0)) * 100.0
        _, _, svm_s_fn, _, _ = get_cm_counts(svm_sent)
        lines.append(
            f"   - **Support Vector Machine:** Tuning hyperparameters for SVM on TF-IDF selected {svm_t_name}, whereas tuning on TF-IDF + Sentiment selected {svm_s_name}. The sentiment-augmented variant achieves {format_pct(svm_sent.get('accuracy', 0.0))} accuracy ({svm_gain_pp:+.2f} percentage points relative to {svm_t_name}), precision of {format_pct(svm_sent.get('precision', 0.0))} (vs. {format_pct(svm_tfidf.get('precision', 0.0))}), recall of {format_pct(svm_sent.get('recall', 0.0))} (vs. {format_pct(svm_tfidf.get('recall', 0.0))}), and ROC-AUC of {svm_sent.get('roc_auc', 0.0):.4f} (vs. {svm_tfidf.get('roc_auc', 0.0):.4f}), resulting in {svm_s_fn} false negatives compared to {svm_t_fn}."
        )

    if active_fs == "tfidf_only":
        runtime_feature_note = (
            f"Operating on {prod_fs_label} avoids additional runtime feature extraction steps: "
            "VADER sentiment extraction and dense lexical feature standardization are not required, "
            "keeping the prediction workflow direct."
        )
    else:
        runtime_feature_note = (
            f"Operating on {prod_fs_label} includes VADER sentiment scoring and dense lexical "
            "feature extraction alongside TF-IDF features."
        )

    lines.extend([
        "3. **Production Model Selection:**",
        f"   - The production pipeline designates **{prod_model_title}** with **{prod_fs_label}** (`{active_fs}`) as the active classifier based on empirical evaluation.",
        f"   - {prod_acc_comp_str}",
        f"   - {prod_rec_comp_str}",
        f"   - On the held-out test partition of {test_size} reviews, this configuration produced {prod_tp} true positives, {prod_tn} true negatives, {prod_fp} false positives, and {prod_fn} false negatives.",
        f"   - {runtime_feature_note}",
        "",
        "---",
        "",
        "## 6. Advanced Features & Limitations (Phase 3.5)",
        "",
        "> [!IMPORTANT]",
        "> **Tier-1 Rule Filter and Sarcasm Risk Detection are Heuristics:**",
        "> - The Tier-1 rule filter (`VELOCITY_EXCEEDED`, `DUPLICATE_FLOOD`, `VERY_SHORT`, `LINK_OR_CONTACT_SPAM`, `REPEATED_CHARACTERS`) and the sarcasm contrast detector (`SARCASM_SUSPECTED`) are deterministic heuristic safety nets.",
        "> - **Their precision and recall have NOT been measured on an annotated evaluation corpus**, and no statistical accuracy is claimed for these rules.",
        "> - Hard rules intentionally short-circuit the ML classifier (`decision_source: 'tier1_rules'`) to handle deterministic anomalies immediately without executing ML inference.",
        "> - Sarcasm detection operates strictly as an informational risk flag for human moderation; it never mutates the underlying ML verdict.",
        "",
        "### General Model Limitations",
        "1. **Domain Sensitivity:** The evaluation corpus comprises English hotel reviews from the Ott et al. (2011) dataset. Performance on retail consumer product reviews (e.g. electronics, cosmetics, apparel, home goods) has not been established by this dataset and may exhibit domain shift without retraining or domain adaptation.",
        "2. **Language Scope:** The classifier operates exclusively on English text. Non-English and code-mixed reviews are not supported by the TF-IDF vocabulary.",
        "3. **LLM-Generated Content:** The pipeline targets human-written deceptive opinion spam; highly sophisticated LLM-generated synthetic reviews may exhibit lexical fluency that bypasses n-gram frequency markers.",
        "",
        "---",
        "",
        "## 7. Conclusion",
        "",
        f"The TruthLens machine learning pipeline demonstrates strong empirical capability on deceptive text detection. The production system deploys **{prod_model_title}** trained on the **`{active_fs}`** feature set, as defined by `best_model` and `active_feature_set` in `backend/models/metrics.json`.",
        "",
        "### Production Model Performance Summary",
        f"- **Model:** {prod_model_title}",
        f"- **Active Feature Set:** `{active_fs}` ({prod_fs_label})",
        f"- **Test Accuracy:** **{format_pct(prod_acc)}** ({prod_correct} of {test_size} test samples correctly classified)",
        f"- **Precision:** **{format_pct(prod_prec)}** ({prod_tp} true positives out of {prod_tp + prod_fp} positive predictions)",
        f"- **Recall:** **{format_pct(prod_recall)}** ({prod_tp} true positives out of {prod_tp + prod_fn} actual deceptive reviews)",
        f"- **F1-Score:** **{format_pct(prod_f1)}**",
        f"- **ROC-AUC:** **{prod_roc_auc:.4f}**",
        f"- **Confusion Matrix:** {prod_tn} True Negatives, {prod_fp} False Positives, {prod_fn} False Negatives, {prod_tp} True Positives",
        "",
        "### Understanding the Metrics: Accuracy vs. ROC-AUC",
        f"- **Accuracy ({format_pct(prod_acc)}):** Represents the proportion of correct classifications ({prod_correct} of {test_size} test reviews) evaluated using the model's default decision boundary (`predict()`). It reflects operational classification performance on the held-out test partition.",
        f"- **ROC-AUC ({prod_roc_auc:.4f}):** Evaluates threshold-independent discriminative ability across all possible classification boundaries by measuring the trade-off between the true positive rate and the false positive rate. An AUC of {prod_roc_auc:.4f} indicates that a randomly selected deceptive review has a {prod_roc_auc * 100:.2f}% probability of receiving a higher deceptive score than a randomly selected genuine review.",
        "",
        "### Model Selection Context",
    ])

    # Dynamic identification of rankings
    top_acc_names = [f"{c['name']} ({format_pct(c['accuracy'])})" for c in top_acc_configs]
    top_auc_names = [f"{c['name']} ({c['roc_auc']:.4f})" for c in top_auc_configs]
    top_rec_names = [f"{c['name']} ({format_pct(c['recall'])})" for c in top_rec_configs]

    lines.append(f"- **Highest Accuracy Configuration:** The peak test accuracy of {format_pct(max_acc)} was achieved by {', '.join(top_acc_names)}.")
    lines.append(f"- **Highest ROC-AUC Configuration:** {', '.join(top_auc_names)}.")
    lines.append(f"- **Highest Recall Configuration:** {', '.join(top_rec_names)}.")
    lines.append(f"- **Production Configuration:** {prod_cfg['name']} (`{active_fs}`).")

    # Production ranking alignment
    matches_top_acc = any(c["name"] == prod_cfg["name"] for c in top_acc_configs)
    matches_top_auc = any(c["name"] == prod_cfg["name"] for c in top_auc_configs)
    matches_top_rec = any(c["name"] == prod_cfg["name"] for c in top_rec_configs)

    if matches_top_acc and matches_top_auc:
        alignment_summary = "The production configuration matches the top ranking across all evaluated models in both accuracy and ROC-AUC."
    elif matches_top_acc and not matches_top_auc:
        highest_auc_desc = ", ".join(f"{c['name']} ({c['roc_auc']:.4f})" for c in top_auc_configs)
        alignment_summary = f"The production configuration matches the highest test accuracy ({format_pct(max_acc)}), but ranks below the highest ROC-AUC configuration ({highest_auc_desc} vs. {prod_roc_auc:.4f})."
    elif not matches_top_acc and matches_top_auc:
        highest_acc_desc = ", ".join(f"{c['name']} ({format_pct(c['accuracy'])})" for c in top_acc_configs)
        alignment_summary = f"The production configuration matches the highest ROC-AUC ({max_auc:.4f}), but ranks below the highest accuracy configuration ({highest_acc_desc} vs. {format_pct(prod_acc)})."
    else:
        highest_acc_desc = ", ".join(f"{c['name']} ({format_pct(c['accuracy'])})" for c in top_acc_configs)
        highest_auc_desc = ", ".join(f"{c['name']} ({c['roc_auc']:.4f})" for c in top_auc_configs)
        alignment_summary = f"The production configuration ranks below the top configuration in both accuracy ({format_pct(prod_acc)} vs. {highest_acc_desc}) and ROC-AUC ({prod_roc_auc:.4f} vs. {highest_auc_desc})."

    lines.append(f"- **Production Ranking Alignment:** {alignment_summary}")

    # Decision synthesis
    if matches_top_acc and matches_top_rec:
        lines.append(
            f"- **Selection Synthesis:** Production designates **{prod_model_title}** with **`{active_fs}`** because it simultaneously matches the peak test accuracy ({format_pct(prod_acc)}) and delivers the highest test recall ({format_pct(prod_recall)}), minimizing undetected deceptive reviews to {prod_fn} false negatives while avoiding additional runtime preprocessing dependencies required by dense sentiment analysis and feature standardization."
        )
    elif matches_top_acc:
        lines.append(
            f"- **Selection Synthesis:** Production designates **{prod_model_title}** with **`{active_fs}`** because it matches peak test accuracy ({format_pct(prod_acc)}) with high recall ({format_pct(prod_recall)}), keeping false negatives low ({prod_fn}) while avoiding additional runtime preprocessing dependencies required by dense sentiment analysis and feature standardization."
        )
    else:
        lines.append(
            f"- **Selection Synthesis:** Production designates **{prod_model_title}** with **`{active_fs}`** balancing accuracy ({format_pct(prod_acc)}), recall ({format_pct(prod_recall)}), and streamlined runtime feature extraction."
        )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    print(f"Reading metrics from {METRICS_FILE}...")
    metrics = load_metrics()
    report = generate_markdown(metrics)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"Successfully generated {OUTPUT_FILE} ({len(report)} bytes).")


if __name__ == "__main__":
    main()
