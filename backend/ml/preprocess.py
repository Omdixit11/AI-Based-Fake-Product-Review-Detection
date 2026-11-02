"""Text cleaning and dataset loading.

``clean_text`` is the single source of truth for preprocessing: the API
(Phase 3) imports this exact function, so training and inference always see
the same token stream.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .config import COLUMN_MAP, DATASET_PATH, GENUINE_LABEL, LABEL_MAP, NEGATIONS

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_HTML_RE = re.compile(r"<[^>]+>")
# Everything that is not a lower-case letter, whitespace or apostrophe goes
# (this also removes digits).
_PUNCT_RE = re.compile(r"[^a-z\s']")
_TOKEN_RE = re.compile(r"[a-z']+")
_WS_RE = re.compile(r"\s+")

_MISSING_DATASET_MSG = """\
Dataset not found or not readable: {path}

What to do:
  1. Download the Kaggle "Deceptive Opinion Spam Corpus" dataset.
  2. Save the CSV as:  backend/data/raw/reviews.csv
  3. Required columns:  text, deceptive  (values: "truthful" / "deceptive")
     Optional columns:  hotel, polarity, source
  4. Re-run:  cd backend && python -m ml.run_pipeline
Do NOT train on made-up data."""


@lru_cache(maxsize=1)
def _stopwords() -> frozenset[str]:
    try:
        from nltk.corpus import stopwords
    except LookupError as exc:  # pragma: no cover - environment problem
        raise RuntimeError(
            "NLTK data is missing. Run: python scripts/download_nltk.py"
        ) from exc
    try:
        words = set(stopwords.words("english"))
    except LookupError as exc:  # pragma: no cover - environment problem
        raise RuntimeError(
            "NLTK stopwords are missing. Run: python scripts/download_nltk.py"
        ) from exc
    return frozenset(words - set(NEGATIONS))


@lru_cache(maxsize=1)
def _lemmatizer():
    try:
        from nltk.stem import WordNetLemmatizer

        return WordNetLemmatizer()
    except LookupError as exc:  # pragma: no cover - environment problem
        raise RuntimeError(
            "NLTK WordNet is missing. Run: python scripts/download_nltk.py"
        ) from exc


@lru_cache(maxsize=100_000)
def _lemmatize(token: str) -> str:
    lemmatizer = _lemmatizer()
    noun = lemmatizer.lemmatize(token)
    if noun != token:
        return noun
    return lemmatizer.lemmatize(token, "v")


def clean_text(text: str) -> str:
    """Lower-case, strip URLs/HTML/punctuation/digits, remove stopwords
    (negations are kept) and lemmatize with WordNet.

    Pure and deterministic: the same input always yields the same output.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    text = text.lower().replace("\u2019", "'").replace("\u2018", "'")
    text = _URL_RE.sub(" ", text)
    text = _HTML_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)

    tokens: list[str] = []
    for raw_token in _TOKEN_RE.findall(text):
        token = raw_token.strip("'")
        if not token or not any(ch.isalpha() for ch in token):
            continue
        if token in _stopwords():
            continue
        tokens.append(_lemmatize(token))

    return _WS_RE.sub(" ", " ".join(tokens)).strip()


def _normalise_label(value) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    key = str(value).strip().lower()
    return LABEL_MAP.get(key)


def load_dataset(path: str | Path | None = None, verbose: bool = True) -> pd.DataFrame:
    """Load ``reviews.csv`` and map its columns/labels via ``config``.

    Returns a frame with ``text`` (raw), ``label`` (1 = fake, 0 = genuine) and
    the optional ``rating`` column. Duplicate and empty reviews are dropped.
    Raises if the file is missing, unreadable, has unknown labels, or contains
    only one class.
    """
    resolved = Path(path) if path is not None else DATASET_PATH
    if not resolved.exists():
        raise FileNotFoundError(_MISSING_DATASET_MSG.format(path=resolved))

    try:
        raw = pd.read_csv(resolved)
    except Exception as exc:  # noqa: BLE001 - surface a clear message
        raise ValueError(
            f"Could not read dataset {resolved}: {exc}. "
            "Check that it is a valid CSV with a header row."
        ) from exc

    text_col = COLUMN_MAP["text"]
    label_col = COLUMN_MAP["label"]
    missing = [c for c in (text_col, label_col) if c not in raw.columns]
    if missing:
        raise ValueError(
            f"Dataset is missing column(s) {missing}. Found columns: {list(raw.columns)}. "
            "Adjust COLUMN_MAP in backend/ml/config.py if the dataset uses other names."
        )

    frame = pd.DataFrame({"text": raw[text_col].astype("string")})
    mapped = raw[label_col].map(_normalise_label)
    if mapped.isna().any():
        unknown = sorted(raw.loc[mapped.isna(), label_col].astype(str).unique())
        raise ValueError(
            f"Unknown label value(s) {unknown}. Known labels: {sorted(LABEL_MAP)}. "
            "Adjust LABEL_MAP in backend/ml/config.py."
        )
    frame["label"] = mapped.astype("int64")

    rating_col = COLUMN_MAP.get("rating")
    if rating_col and rating_col in raw.columns:
        frame["rating"] = pd.to_numeric(raw[rating_col], errors="coerce")

    frame["text"] = frame["text"].astype(str).str.strip()
    frame = frame[frame["text"].ne("") & frame["text"].ne("nan")]
    if frame.empty:
        raise ValueError(f"Dataset {resolved} contains no usable reviews.")

    duplicates_dropped = 0
    if len(frame) > 1:
        before = len(frame)
        frame = frame.drop_duplicates(subset=["text"], keep="first")
        duplicates_dropped = before - len(frame)

    counts = frame["label"].value_counts()
    if len(counts) < 2:
        if verbose:
            print(f"Class balance: {counts.to_dict()}")
        raise ValueError(
            "Dataset contains only one class "
            f"({counts.to_dict()}); training a fake-review classifier is impossible. "
            "Please provide a dataset with both 'truthful' and 'deceptive' reviews."
        )

    frame = frame.reset_index(drop=True)
    frame.attrs["duplicates_dropped"] = duplicates_dropped
    if verbose:
        fake = int((frame["label"] == 1).sum())
        genuine = int((frame["label"] == GENUINE_LABEL).sum())
        avg_words = frame["text"].str.split().str.len().mean()
        print(f"Dataset: {resolved}")
        print(f"  rows after cleaning: {len(frame)}")
        print(
            f"  class balance: genuine(0)={genuine}, fake(1)={fake} "
            f"({100.0 * fake / len(frame):.2f}% fake)"
        )
        print(f"  average review length: {avg_words:.1f} words")
    return frame
