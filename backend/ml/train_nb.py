"""Naive Bayes training with a 5-fold grid search over ``alpha``."""
from __future__ import annotations

from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.naive_bayes import MultinomialNB

from .config import CV_FOLDS, RANDOM_STATE

ALPHA_GRID = [0.01, 0.05, 0.1, 0.3, 0.5, 1.0, 2.0]


def _cv():
    return StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)


def train_naive_bayes(X_train, y_train):
    """Return ``(fitted_model, best_params, best_cv_f1)``."""
    search = GridSearchCV(
        estimator=MultinomialNB(),
        param_grid={"alpha": ALPHA_GRID},
        scoring="f1",
        cv=_cv(),
        n_jobs=1,  # low-RAM machine
        refit=True,
        return_train_score=False,
    )
    search.fit(X_train, y_train)
    params = {"alpha": float(search.best_params_["alpha"])}
    return search.best_estimator_, params, float(search.best_score_)
