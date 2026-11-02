"""Central configuration for the TruthLens ML pipeline.

Every path, dataset column mapping and model setting lives here so that
training and inference (Phase 3) cannot drift apart.
"""
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ML_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = BACKEND_DIR / "data" / "raw"
DATASET_PATH = DATA_DIR / "reviews.csv"
MODELS_DIR = BACKEND_DIR / "models"

VECTORIZER_PATH = MODELS_DIR / "vectorizer.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
NB_MODEL_PATH = MODELS_DIR / "nb_model.pkl"
SVM_MODEL_PATH = MODELS_DIR / "svm_model.pkl"
SVM_LINEAR_PATH = MODELS_DIR / "svm_linear_base.pkl"
METRICS_PATH = MODELS_DIR / "metrics.json"

DATASET_NAME = "Deceptive Opinion Spam Corpus (Ott et al., 2011)"

# 1 = fake / deceptive review, 0 = genuine / truthful review.
FAKE_LABEL = 1
GENUINE_LABEL = 0

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5

# Source column names -> the canonical names used by the pipeline.
# The Deceptive Opinion Spam Corpus has no rating column; it is optional.
COLUMN_MAP = {
    "text": "text",
    "label": "deceptive",
    "rating": "rating",
}

# Label strings -> integers. Keys are normalised to lower-case before lookup.
LABEL_MAP = {
    "deceptive": FAKE_LABEL,
    "fake": FAKE_LABEL,
    "cg": FAKE_LABEL,  # gold-standard deceptive reviews in the corpus
    "truthful": GENUINE_LABEL,
    "genuine": GENUINE_LABEL,
    "or": GENUINE_LABEL,  # original (real) reviews in the corpus
}

FEATURE_SETS = ("tfidf_only", "tfidf_sentiment")

# Kept deliberately small: this machine has limited RAM and every artifact
# committed to git must stay well below GitHub's 100 MB limit.
TFIDF_PARAMS = {
    "ngram_range": (1, 2),
    "min_df": 2,
    "max_df": 0.9,
    "sublinear_tf": True,
    "max_features": 20000,
    "strip_accents": "unicode",
    "lowercase": True,
}

VADER_FEATURE_NAMES = ["vader_neg", "vader_neu", "vader_pos", "vader_compound"]
META_FEATURE_NAMES = [
    "char_count",
    "word_count",
    "exclamation_count",
    "uppercase_ratio",
    "has_digit",
    "avg_word_length",
]

# Stopwords are removed, but negations carry the verdict and must survive.
NEGATIONS = frozenset(
    {
        "not", "no", "never", "nor", "none", "nothing", "nobody", "nowhere",
        "neither", "without", "cannot", "can't", "don't", "doesn't", "didn't",
        "isn't", "wasn't", "aren't", "weren't", "won't", "wouldn't",
        "shouldn't", "couldn't", "ain't", "hasn't", "haven't", "hadn't",
        "mustn't", "needn't", "hardly", "barely", "scarcely",
    }
)

MAX_ARTIFACT_MB = 90
DROP_DUPLICATES = True
