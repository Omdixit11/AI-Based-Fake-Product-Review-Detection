"""SVM training: grid search, probability calibration and a linear explainer."""
from __future__ import annotations

from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.svm import LinearSVC, SVC

from .config import CV_FOLDS, RANDOM_STATE

# Deliberately small: limited RAM and committed artifacts must stay < 90 MB.
PARAM_GRID = {
    "C": [0.1, 1.0, 3.0],
    "kernel": ["linear", "rbf"],
    "gamma": ["scale", "auto"],
}


def _cv():
    return StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)


def train_svm(X_train, y_train):
    """Return ``(calibrated_model, best_params, best_cv_f1)``.

    The grid search finds the best SVC; the winner is then wrapped in
    ``CalibratedClassifierCV`` so it exposes ``predict_proba``.
    """
    search = GridSearchCV(
        estimator=SVC(cache_size=200, random_state=RANDOM_STATE),
        param_grid=PARAM_GRID,
        scoring="f1",
        cv=_cv(),
        n_jobs=1,  # low-RAM machine
        refit=True,
        return_train_score=False,
    )
    search.fit(X_train, y_train)

    best = search.best_estimator_
    calibrated = CalibratedClassifierCV(
        estimator=best,
        method="sigmoid",
        cv=_cv(),
    )
    calibrated.fit(X_train, y_train)

    best_params = {
        "C": float(search.best_params_["C"]),
        "kernel": str(search.best_params_["kernel"]),
        "gamma": str(search.best_params_["gamma"]),
    }
    return calibrated, best_params, float(search.best_score_)


def train_linear_base(X_train, y_train, C: float = 1.0) -> LinearSVC:
    """Fit a plain linear SVM used by Phase 3 for coefficient explanations.

    Kept separate from the calibrated model so the coefficients are readable.
    """
    model = LinearSVC(
        C=float(C),
        random_state=RANDOM_STATE,
        dual="auto",
        max_iter=5000,
    )
    model.fit(X_train, y_train)
    return model
