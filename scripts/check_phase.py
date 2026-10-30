#!/usr/bin/env python3
"""
Phase gatekeeper for the TruthLens team workflow.

  python scripts/check_phase.py --ready N     -> are phases 1..N-1 complete? (run BEFORE you start phase N)
  python scripts/check_phase.py N             -> is phase N complete?        (run BEFORE you push phase N)
  python scripts/check_phase.py 3 --no-tests  -> skip running pytest (phase 3 only)

Standard library only. Exit code 0 = OK, 1 = problems found.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_ARTIFACT_MB = 90  # GitHub rejects files over 100 MB

PHASE_NAMES = {
    1: "UI (frontend, mock mode)",
    2: "ML pipeline",
    3: "Backend API",
    4: "Integration and testing",
    5: "Docker, docs and packaging",
}

PHASE_FILES = {
    1: [
        "frontend/package.json",
        "frontend/src/app/layout.tsx",
        "frontend/src/app/page.tsx",
        "frontend/src/app/analyze/page.tsx",
        "frontend/src/app/batch/page.tsx",
        "frontend/src/app/model-lab/page.tsx",
        "frontend/src/app/history/page.tsx",
        "frontend/src/app/how-it-works/page.tsx",
        "frontend/src/lib/types.ts",
        "frontend/src/lib/api.ts",
        "frontend/src/lib/mockApi.ts",
        "frontend/src/components/analyzer/ConfidenceGauge.tsx",
        "frontend/src/components/analyzer/VerdictCard.tsx",
        "frontend/src/components/analyzer/HighlightedText.tsx",
        "frontend/src/components/analyzer/SentimentMeter.tsx",
    ],
    2: [
        "backend/ml/config.py",
        "backend/ml/preprocess.py",
        "backend/ml/features.py",
        "backend/ml/train_nb.py",
        "backend/ml/train_svm.py",
        "backend/ml/evaluate.py",
        "backend/ml/run_pipeline.py",
        "backend/tests/test_ml.py",
        "backend/models/vectorizer.pkl",
        "backend/models/scaler.pkl",
        "backend/models/nb_model.pkl",
        "backend/models/svm_model.pkl",
        "backend/models/svm_linear_base.pkl",
        "backend/models/metrics.json",
    ],
    3: [
        "backend/app/main.py",
        "backend/app/config.py",
        "backend/app/schemas.py",
        "backend/app/routers/predict.py",
        "backend/app/routers/models.py",
        "backend/app/routers/history.py",
        "backend/app/routers/health.py",
        "backend/app/services/predictor.py",
        "backend/app/services/explain.py",
        "backend/app/services/flags.py",
        "backend/app/services/sentiment.py",
        "backend/app/db/database.py",
        "backend/app/db/models.py",
        "backend/tests/test_api.py",
        "backend/tests/test_services.py",
    ],
    4: [
        "docs/INTEGRATION_REPORT.md",
        "frontend/playwright.config.ts",
    ],
    5: [
        "backend/Dockerfile",
        "frontend/Dockerfile",
        "docker-compose.yml",
        "scripts/generate_report.py",
        "docs/MODEL_REPORT.md",
        "docs/API.md",
        "docs/PRESENTATION_NOTES.md",
        "docs/screenshots/landing.png",
        "docs/screenshots/analyze-fake.png",
        "docs/screenshots/analyze-genuine.png",
        "docs/screenshots/batch.png",
        "docs/screenshots/model-lab.png",
        "docs/screenshots/history.png",
        "docs/screenshots/how-it-works.png",
        "docs/screenshots/analyze-light.png",
        "docs/screenshots/analyze-mobile.png",
    ],
}


def missing(paths):
    return [p for p in paths if not (ROOT / p).exists()]


def read(rel):
    f = ROOT / rel
    return f.read_text() if f.exists() else ""


def check_protected(problems):
    sums = ROOT / "scripts" / "protected.sha256"
    if not sums.exists():
        problems.append("scripts/protected.sha256 is missing (protected-file list).")
        return
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        rel = rel.strip()
        f = ROOT / rel
        if not f.exists():
            problems.append(f"Protected file deleted: {rel}")
        elif hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != digest:
            problems.append(f"Protected file was modified: {rel}  (restore: git checkout origin/main -- {rel})")


def check_phase1(problems):
    if "NEXT_PUBLIC_USE_MOCK" not in read(".env.example"):
        problems.append(".env.example must contain NEXT_PUBLIC_USE_MOCK")
    api = read("frontend/src/lib/api.ts")
    if api and "NEXT_PUBLIC_USE_MOCK" not in api:
        problems.append("frontend/src/lib/api.ts must switch between real and mock API using NEXT_PUBLIC_USE_MOCK")


def check_phase2(problems):
    models_dir = ROOT / "backend/models"
    for f in models_dir.glob("*"):
        if f.is_file() and f.stat().st_size > MAX_ARTIFACT_MB * 1024 * 1024:
            problems.append(f"{f.name} is larger than {MAX_ARTIFACT_MB} MB (GitHub limit is 100 MB). Reduce max_features or model size.")
    mpath = models_dir / "metrics.json"
    if not mpath.exists():
        return
    try:
        m = json.loads(mpath.read_text())
    except Exception as e:  # noqa: BLE001
        problems.append(f"metrics.json is not valid JSON: {e}")
        return
    for k in ["generated_at", "dataset", "best_model", "active_feature_set", "models"]:
        if k not in m:
            problems.append(f"metrics.json missing key: {k}")
    ds = m.get("dataset", {})
    for k in ["name", "size", "train_size", "test_size", "fake_percent"]:
        if k not in ds:
            problems.append(f"metrics.json dataset missing key: {k}")
    if "synthetic" in str(ds.get("name", "")).lower():
        problems.append("metrics.json was produced from SYNTHETIC data. Train on a real dataset.")
    if m.get("best_model") not in ("nb", "svm"):
        problems.append("metrics.json best_model must be 'nb' or 'svm'")
    if m.get("active_feature_set") not in ("tfidf_only", "tfidf_sentiment"):
        problems.append("metrics.json active_feature_set must be 'tfidf_only' or 'tfidf_sentiment'")
    keys = ["accuracy", "precision", "recall", "f1", "roc_auc", "confusion_matrix", "roc_curve", "best_params"]
    for model in ("nb", "svm"):
        for fs in ("tfidf_only", "tfidf_sentiment"):
            try:
                block = m["models"][model][fs]
            except KeyError:
                problems.append(f"metrics.json missing models.{model}.{fs}")
                continue
            for k in keys:
                if k not in block:
                    problems.append(f"metrics.json models.{model}.{fs} missing key: {k}")
            cm = block.get("confusion_matrix")
            if cm is not None and not (len(cm) == 2 and all(len(r) == 2 for r in cm)):
                problems.append(f"models.{model}.{fs}.confusion_matrix must be 2x2")


def check_phase3(problems, run_tests):
    if not run_tests:
        return
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"], cwd=ROOT / "backend", capture_output=True, text=True)
    if r.returncode != 0:
        out = (r.stdout + r.stderr)[-1500:]
        hint = "\nHint: run  pip install -r backend/requirements.txt  inside your virtual environment." if "No module named" in out else ""
        problems.append("Backend tests failed:\n" + out + hint)


def check_phase4(problems):
    if "NEXT_PUBLIC_USE_MOCK=false" not in read(".env.example").replace(" ", ""):
        problems.append(".env.example must default to NEXT_PUBLIC_USE_MOCK=false after Phase 4")
    e2e = ROOT / "frontend/e2e"
    if not (e2e.exists() and list(e2e.glob("*.spec.ts"))):
        problems.append("No Playwright specs found in frontend/e2e/*.spec.ts")


def run_phase(n, problems, run_tests=True):
    for p in missing(PHASE_FILES[n]):
        problems.append(f"[phase {n}] missing: {p}")
    if n == 1:
        check_phase1(problems)
    elif n == 2:
        check_phase2(problems)
    elif n == 3:
        check_phase3(problems, run_tests)
    elif n == 4:
        check_phase4(problems)


def tag_exists(tag):
    try:
        r = subprocess.run(["git", "tag", "-l", tag], cwd=ROOT, capture_output=True, text=True)
        return tag in r.stdout.split()
    except FileNotFoundError:
        return True


def main():
    args = sys.argv[1:]
    nums = [a for a in args if a.isdigit()]
    if not nums or not 1 <= int(nums[0]) <= 5:
        print(__doc__)
        return 1
    n = int(nums[0])
    ready = "--ready" in args
    run_tests = "--no-tests" not in args
    problems, warnings = [], []

    check_protected(problems)

    if ready:
        print(f"Checking that phases 1..{n - 1} are complete before you start phase {n} ({PHASE_NAMES[n]})")
        for p in range(1, n):
            run_phase(p, problems, run_tests=False)
            if not tag_exists(f"phase-{p}-complete"):
                warnings.append(f"git tag phase-{p}-complete not found locally. Run: git pull --tags")
    else:
        print(f"Checking phase {n}: {PHASE_NAMES[n]}")
        for p in range(1, n):
            run_phase(p, problems, run_tests=False)
        run_phase(n, problems, run_tests=run_tests)

    for w in warnings:
        print("WARNING:", w)
    if problems:
        print("\nNOT READY. Fix these first:")
        for p in problems:
            print("  -", p)
        return 1
    print("\nOK. All checks passed." + ("  You can start your phase." if ready else "  You can push your phase."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
