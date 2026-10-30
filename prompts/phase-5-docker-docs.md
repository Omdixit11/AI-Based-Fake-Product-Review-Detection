# PHASE 5 PROMPT: Docker, Docs and Packaging

> Give this ENTIRE file to your Antigravity agent. It is Phase 5 of 5. Read `README.md` and `docs/LLD.md` first.

---

## 0. TEAM CONTEXT (read first, these rules override anything below)

- This is the **TruthLens** monorepo. The folder skeleton already exists. Do NOT recreate the structure; fill in only your phase.
- Five people work in strict order. You do **ONLY Phase 5**. Earlier phases are finished and already in git. Do not rewrite or "improve" their work.
- **PROTECTED files, never edit:** README.md, docs/HLD.md, docs/LLD.md, docs/PROJECT_STRUCTURE.md, everything in prompts/, everything in .githooks/, scripts/check_phase.py, scripts/protected.sha256. A git pre-commit hook blocks commits that touch them.
- **You MAY create or change:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `.dockerignore` files, `scripts/generate_report.py`, `docs/MODEL_REPORT.md`, `docs/API.md`, `docs/PRESENTATION_NOTES.md`, `docs/screenshots/*`.
- **You must NOT change:** application behavior (no feature changes), `backend/ml/`, `backend/models/`, and the protected files. **Never edit the root `README.md`, `docs/HLD.md` or `docs/LLD.md`.**
- Never use `git push --force`. Never commit secrets, `node_modules`, `.venv`, or the raw dataset.

### 0.1 Start checklist (run these first)

```bash
git checkout main
git pull origin main --tags
git config core.hooksPath .githooks
python scripts/check_phase.py --ready 5
git checkout -b phase-5-docker-docs
```
If `check_phase.py --ready 5` prints NOT READY, **stop and tell me**. Do not try to fix earlier phases.

### 0.2 Adjustments for this repo (these override anything below that conflicts)

None for this phase.

---

---

## 1. GOAL

Package the finished app so a stranger (teacher, evaluator, teammate) can run it in under 10 minutes, and produce the project documents needed for a college submission. **Do not change application behavior.**

---

## 2. DELIVERABLES

### A. Containerization
- `backend/Dockerfile`: `python:3.11-slim`, install `backend/requirements.txt`, download NLTK data at build time (`python scripts/download_nltk.py` or equivalent), copy `backend/`, run `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Build context is the repo root.
- `frontend/Dockerfile`: multi-stage build, Next.js `output: "standalone"`, non-root user, `NEXT_PUBLIC_API_URL` passed as a build arg (browser calls `http://localhost:8000`).
- `docker-compose.yml`: services `backend` (8000) and `frontend` (3000); named volume for the SQLite history file; `backend/models/` mounted read-only; healthcheck on `/api/health`; frontend `depends_on` backend healthy; `CORS_ORIGINS=http://localhost:3000`; `NEXT_PUBLIC_USE_MOCK=false`.
- `.dockerignore` for backend and frontend (exclude `node_modules`, `.next`, `.venv`, `__pycache__`, `backend/data/raw`).
- Verify with `docker compose up --build`.

### B. Report generator
`scripts/generate_report.py` reads `backend/models/metrics.json` and writes `docs/MODEL_REPORT.md`: dataset summary, short explanations of TF-IDF, Naive Bayes, SVM and VADER, a metrics table for each model and feature set, a plain-language comparison, and a conclusion on the best model. Only real numbers from the file. Run it and commit the generated report.

### C. API reference
`docs/API.md`: every endpoint with request and response examples (use the real responses from the running API, not invented ones), error format, and curl examples.

### D. Screenshots
Using Playwright against the running app (real API), save these exact files to `docs/screenshots/`:
`landing.png`, `analyze-fake.png`, `analyze-genuine.png`, `batch.png`, `model-lab.png`, `history.png`, `how-it-works.png`, `analyze-light.png` (light theme), `analyze-mobile.png` (360px width).
The root README already links to these names, so the names must match exactly.

### E. Presentation helper
`docs/PRESENTATION_NOTES.md`: a 10-slide outline, a 3-minute demo script (what to click and say, in order), and 12 likely viva questions with short, accurate answers (why TF-IDF, Naive Bayes vs SVM, confusion matrix, why calibrate the SVM, how data leakage is avoided, limitations, and similar).

---

## 3. RULES

1. Do not invent metrics, benchmarks or features. Everything must match the real code and the real `metrics.json`.
2. Keep ports, commands and file names consistent with `README.md` (read it, do not edit it).
3. Keep the writing simple and clear; the reader is a student.
4. Actually run the stack and tell me exactly what worked and what did not.

---

## FINISH CHECKLIST (every item must be true before you hand off)

- `docker compose up --build` starts backend (`:8000`) and frontend (`:3000`); `/api/health` returns ok and the web app works in the browser. If Docker is unavailable in your environment, say so clearly and verify everything else.
- `python scripts/generate_report.py` writes `docs/MODEL_REPORT.md` from the real `backend/models/metrics.json`.
- `docs/API.md`, `docs/PRESENTATION_NOTES.md` and all 9 screenshots exist with the exact names below.
- Root `README.md`, `docs/HLD.md` and `docs/LLD.md` are untouched (`git status` proves it).
- `python scripts/check_phase.py 5` prints **OK. All checks passed.**
- `git status` shows no changes to protected files (README.md, docs/HLD.md, docs/LLD.md, prompts/, scripts/check_phase.py).

## GIT HAND-OFF (run exactly, in this order)

```bash
git add -A
git commit -m "phase 5: docker, reports, screenshots, presentation notes"
git checkout main
git pull origin main
git merge --no-ff phase-5-docker-docs -m "Merge phase 5"
python scripts/check_phase.py 5
git push origin main
git tag phase-5-complete
git push origin phase-5-complete
```
If the push is rejected, do NOT force push. Run `git pull --rebase origin main`, re-run the check, and push again. If there is a conflict you cannot resolve safely, stop and ask me.

When done, tell me: the final commit hash, a 5-line summary of what you built, and anything unfinished.

After the phase-5 tag, also run: `git tag v1.0.0 && git push origin v1.0.0` (final release).
