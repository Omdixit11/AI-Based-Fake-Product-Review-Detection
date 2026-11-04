"""Tier-1 rule filter: cheap spam gates that run *before* the ML model.

Phase 3.5 feature 1. Everything here is pure Python - no model, no artefacts,
microseconds per call - so it can short-circuit obviously abusive traffic and
save the (comparatively expensive) TF-IDF + SVM round trip.

Two kinds of signal:

* **hard rules** decide on their own and stop the request from ever reaching
  the model (``action = "flag_spam"``). They are about *behaviour* - how often
  this user or this exact text shows up - which the text classifier cannot see.
* **soft signals** are only reported. They never change ``verdict`` or
  ``fake_probability`` and, by design, are **not** merged into the existing
  ``flags`` list (the Phase 3 contract and its 78 tests must stay untouched).

The velocity and duplicate counters are in-memory, per server process, and
reset when the process restarts. That is deliberate: this is a rate gate for a
student project, not a distributed fraud system. ``tracker.reset`` exists so
tests can start from a clean slate.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from collections import OrderedDict, deque
from datetime import datetime, timezone
from typing import Any

from app.config import settings

# --- what each code means in the API response -------------------------------
RULE_LABELS: dict[str, str] = {
    "VELOCITY_EXCEEDED": "Too many reviews from this user in the last minute",
    "DUPLICATE_FLOOD": "The same review text submitted repeatedly",
    "VERY_SHORT": "Very short text",
    "LINK_OR_CONTACT_SPAM": "Contains a link, e-mail address or phone number",
    "REPEATED_CHARACTERS": "Letters stretched out (for example 'goooood')",
}

HARD_CODES: tuple[str, ...] = ("VELOCITY_EXCEEDED", "DUPLICATE_FLOOD")
SOFT_CODES: tuple[str, ...] = (
    "VERY_SHORT",
    "LINK_OR_CONTACT_SPAM",
    "REPEATED_CHARACTERS",
)

RULE_SEVERITY: dict[str, str] = {
    "VELOCITY_EXCEEDED": "high",
    "DUPLICATE_FLOOD": "high",
    "VERY_SHORT": "low",
    "LINK_OR_CONTACT_SPAM": "medium",
    "REPEATED_CHARACTERS": "low",
}

# --- text patterns ----------------------------------------------------------
_URL_RE = re.compile(r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|net|org|in|shop|store|co\.uk)\b", re.I)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# A phone-ish run of characters that still has to carry at least 8 digits, so
# "room 214" or "3 nights" never look like a number.
_PHONEISH_RE = re.compile(r"[+(]?[\d][\d\s().\-]{6,}\d")
# Letters only - "room 1000" is a room number, not stretched-out typing.
_REPEAT_RE = re.compile(r"([A-Za-z\u0900-\u097F])\1{3,}")
_WS_RE = re.compile(r"\s+")


def _rule(code: str, kind: str) -> dict[str, str]:
    """One rule hit, shaped exactly like the ``tier1.rules`` items."""
    return {
        "code": code,
        "label": RULE_LABELS.get(code, code),
        "severity": RULE_SEVERITY.get(code, "low"),
        "kind": kind,
    }


def normalise_text(text: str) -> str:
    """Lowercase + collapse whitespace: the identity used for duplicate checks."""
    return _WS_RE.sub(" ", (text or "").strip()).lower()


def text_hash(text: str) -> str:
    return hashlib.sha1(normalise_text(text).encode("utf-8")).hexdigest()


def _to_epoch(moment: datetime | None) -> float | None:
    """Epoch seconds for a client-supplied ``posted_at`` (naive means UTC)."""
    if moment is None:
        return None
    try:
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return float(moment.timestamp())
    except (OverflowError, OSError, ValueError):
        return None


# --------------------------------------------------------------- static rules
def soft_signals(review: str) -> list[dict[str, str]]:
    """Text-only signals. Reported, never decisive, never added to ``flags``."""
    text = review or ""
    found: list[dict[str, str]] = []

    if len(text.split()) < settings.tier1_min_words:
        found.append(_rule("VERY_SHORT", "soft"))
    if _EMAIL_RE.search(text) or _URL_RE.search(text) or _has_phone_number(text):
        found.append(_rule("LINK_OR_CONTACT_SPAM", "soft"))
    if _REPEAT_RE.search(text):
        found.append(_rule("REPEATED_CHARACTERS", "soft"))
    return found


def _has_phone_number(text: str) -> bool:
    for match in _PHONEISH_RE.finditer(text):
        if len(re.sub(r"\D", "", match.group())) >= 8:
            return True
    return False


# -------------------------------------------------------------------- tracker
class Tier1Tracker:
    """Sliding-window counters for user velocity and duplicate floods.

    Thread-safe (one lock, FastAPI may serve requests from several worker
    threads) and memory-bounded: when more than ``max_keys`` distinct users or
    texts have been seen, the least recently seen one is dropped.
    """

    def __init__(self, max_keys: int | None = None) -> None:
        self._lock = threading.Lock()
        self._by_user: "OrderedDict[str, deque[float]]" = OrderedDict()
        self._by_hash: "OrderedDict[str, deque[float]]" = OrderedDict()
        self._max_keys = max_keys

    # internals ------------------------------------------------------------
    def _max(self) -> int:
        return max(1, int(self._max_keys or settings.tier1_max_tracked_keys))

    @staticmethod
    def _prune(window: deque[float], moment: float, seconds: float) -> None:
        while window and moment - window[0] > seconds:
            window.popleft()

    def _record(
        self, store: "OrderedDict[str, deque[float]]", key: str, moment: float, seconds: float
    ) -> int:
        """Append ``moment`` under ``key`` and return how many are in the window."""
        window = store.get(key)
        if window is None:
            window = deque()
            store[key] = window
            while len(store) > self._max():  # drop the oldest tracked key
                store.popitem(last=False)
        else:
            store.move_to_end(key)
        self._prune(window, moment, seconds)
        window.append(moment)
        return len(window)

    # public ---------------------------------------------------------------
    def observe_user(self, user_id: str, moment: float) -> int:
        seconds = float(settings.tier1_velocity_window_seconds)
        with self._lock:
            return self._record(self._by_user, user_id, moment, seconds)

    def observe_text(self, hashed: str, moment: float) -> int:
        seconds = float(settings.tier1_duplicate_window_seconds)
        with self._lock:
            return self._record(self._by_hash, hashed, moment, seconds)

    def reset(self) -> None:
        with self._lock:
            self._by_user.clear()
            self._by_hash.clear()

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"users": len(self._by_user), "texts": len(self._by_hash)}


#: Shared tracker used by ``POST /api/predict``. Batch analysis builds its own
#: per-upload tracker so a CSV can never contaminate server-side state.
tracker = Tier1Tracker()


# ------------------------------------------------------------------ evaluate
def evaluate(
    review: str,
    metadata: dict[str, Any] | None = None,
    *,
    tracker_obj: Tier1Tracker | None = None,
) -> dict[str, Any]:
    """Run every Tier-1 rule for one review.

    ``metadata`` is the optional request block (``user_id`` / ``posted_at`` /
    ``reviews_last_minute``); ``None`` or an empty dict is perfectly normal and
    simply means the behaviour rules have nothing to work with.

    Returns the ``tier1`` response block plus two internal keys that the router
    uses (``hard_rules`` / ``soft_rules`` as code lists).
    """
    active = tracker_obj or tracker
    meta = metadata or {}
    moment = _to_epoch(meta.get("posted_at"))
    if moment is None:
        moment = time.time()

    user_id = meta.get("user_id")
    reviews_last_minute = meta.get("reviews_last_minute")

    rules: list[dict[str, str]] = []
    velocity_count = 0

    # 1. Velocity - the client-reported figure wins, otherwise our own window.
    #    ``reviews_last_minute`` alone is enough evidence, no user_id required.
    if user_id:
        velocity_count = active.observe_user(str(user_id), moment)
    if reviews_last_minute is not None:
        velocity_count = max(int(reviews_last_minute) + 1, velocity_count)
        fired = int(reviews_last_minute) > settings.tier1_max_reviews_per_minute
    else:
        fired = velocity_count > settings.tier1_max_reviews_per_minute
    if fired:
        rules.append(_rule("VELOCITY_EXCEEDED", "hard"))

    # 2. Duplicate flood - the same normalised text N times in 10 minutes.
    duplicate_count = active.observe_text(text_hash(review or ""), moment)
    if duplicate_count >= settings.tier1_duplicate_threshold:
        rules.append(_rule("DUPLICATE_FLOOD", "hard"))

    hard = [rule["code"] for rule in rules]
    soft = soft_signals(review)
    rules.extend(soft)

    triggered = bool(hard)
    return {
        "triggered": triggered,
        "action": "flag_spam" if triggered else "pass",
        "rules": rules,
        # internal, never serialised (the response model drops unknown keys):
        "hard_rules": hard,
        "soft_rules": [rule["code"] for rule in soft],
        "velocity_count": velocity_count,
        "duplicate_count": duplicate_count,
    }


def as_response_block(result: dict[str, Any]) -> dict[str, Any]:
    """Strip the internal keys: exactly what ``tier1`` looks like in the JSON."""
    return {
        "triggered": result["triggered"],
        "action": result["action"],
        "rules": result["rules"],
    }


def empty_result() -> dict[str, Any]:
    """Neutral block used if Tier-1 ever produced nothing for a response."""
    return {"triggered": False, "action": "pass", "rules": []}


def short_circuited(result: dict[str, Any]) -> bool:
    """True when a hard rule decided the outcome and the model must not run."""
    return result["action"] == "flag_spam"
