# PHASE 4 PROMPT: Integration and Testing

> Give this ENTIRE file to your Antigravity agent. It is Phase 4 of 5. Read `README.md` and `docs/LLD.md` first.

---

## 0. TEAM CONTEXT (read first, these rules override anything below)

- This is the **TruthLens** monorepo. The folder skeleton already exists. Do NOT recreate the structure; fill in only your phase.
- Five people work in strict order. You do **ONLY Phase 4**. Earlier phases are finished and already in git. Do not rewrite or "improve" their work.
- **PROTECTED files, never edit:** README.md, docs/HLD.md, docs/LLD.md, docs/PROJECT_STRUCTURE.md, everything in prompts/, everything in .githooks/, scripts/check_phase.py, scripts/protected.sha256. A git pre-commit hook blocks commits that touch them.
- **You MAY create or change:** `frontend/**` (adapters, fixes, e2e tests), `backend/app/**` (only minimal contract fixes), `frontend/e2e/**`, `frontend/playwright.config.ts`, `docs/INTEGRATION_REPORT.md`, and `.env.example` (only to set `NEXT_PUBLIC_USE_MOCK=false`).
- **You must NOT change:** `backend/ml/`, `backend/models/` (never retrain), `Makefile`, and the protected files.
- Never use `git push --force`. Never commit secrets, `node_modules`, `.venv`, or the raw dataset.

### 0.1 Start checklist (run these first)

```bash
git checkout main
git pull origin main --tags
git config core.hooksPath .githooks
python scripts/check_phase.py --ready 4
git checkout -b phase-4-integration
```
If `check_phase.py --ready 4` prints NOT READY, **stop and tell me**. Do not try to fix earlier phases.

### 0.2 Adjustments for this repo (these override anything below that conflicts)

1. In `.env.example` change `NEXT_PUBLIC_USE_MOCK=true` to `NEXT_PUBLIC_USE_MOCK=false`, and create/update the git-ignored `frontend/.env.local` with `NEXT_PUBLIC_USE_MOCK=false` and `NEXT_PUBLIC_API_URL=http://localhost:8000`.
2. Playwright: create `frontend/playwright.config.ts` (with `webServer` entries for backend and frontend if practical) and put specs in `frontend/e2e/*.spec.ts`. Install the browser with `npx playwright install chromium`.
3. Your final report MUST be saved as `docs/INTEGRATION_REPORT.md` (bug table, contract mismatch table, test results, performance numbers, remaining issues). A checker script looks for this file.
4. Do not edit the root `README.md`. Do not touch `backend/ml/` or retrain. Fix problems with the smallest possible change.
5. If Lighthouse cannot run in your environment, say so in the report. That does not block the phase. Everything else in the checklist does.

---

---

## 1. GOAL

Connect the Next.js frontend to the real FastAPI backend, remove dependence on mock data, and prove the whole system works end to end. You are the integrator and QA engineer. Find and fix real problems, and report honestly what you found.

---

## 2. TASKS

**A. Switch to the real API**
1. Set `NEXT_PUBLIC_USE_MOCK=false` and `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`, and document both in `.env.example`.
2. Make sure the backend CORS allows `http://localhost:3000`.
3. Start backend and frontend together and walk through every page with real data.

**B. Contract check**
Compare `frontend/src/lib/types.ts` with the actual backend responses for `/api/predict`, `/api/predict/batch`, `/api/models/metrics`, `/api/history` and `/api/health`. List every mismatch (field names, nullability, missing fields). Fix the side that is wrong. Prefer changing the frontend adapter unless the backend clearly breaks the documented contract. Show me a short mismatch table of what you changed.

**C. Feature walkthrough (verify each, with screenshots)**
1. Analyze: a clearly fake review and a clearly genuine review both give sensible verdicts; highlighted words, tokens, flags, sentiment and gauge all render from real data.
2. Model switch: Best, Naive Bayes and SVM each work and `model_used` changes.
3. Batch: upload a 50-row CSV, check summary, table filter/sort, and CSV export. Also try a bad CSV (missing `review` column) and confirm a friendly error.
4. History: new analyses appear, search and filter work, delete and clear-all work.
5. Model Lab: charts show the real numbers from `metrics.json`, and the "TF-IDF only vs TF-IDF + sentiment" toggle works.
6. Landing stats match `metrics.json`.
7. Health chip: turns to an error state when the backend is stopped, and recovers when it is back.

**D. Edge cases**
Test and fix: empty input, 1-word review, 5,000-char review, non-English text, emoji, HTML/script tags in the review (must render as plain text, no XSS), very long single word, API down, API slow (loading state), and rapid repeated clicks on Analyze.

**E. Automated tests**
- Add a Playwright end-to-end test: open `/analyze`, enter a sample review, click Analyze, expect a verdict and a gauge value.
- Add a second Playwright test for batch upload.
- Run the backend `pytest` suite and the frontend tests together with one command (`make test` if a Makefile exists, otherwise a script).

**F. Performance and quality**
- Measure single prediction latency (target under 100 ms server-side) and a 1,000-row batch (target under 10 s). Report real numbers.
- Run Lighthouse on `/`, `/analyze` and `/model-lab` in both themes. Targets: Performance 90+, Accessibility 95+. Fix issues you can; list what remains.
- Check responsive layouts at 360px, 768px and 1440px.

---

## 3. RULES

1. Do not hide failures. If something does not work, report it with the cause, then fix it or tell me clearly why you could not.
2. Do not add mock data or hard-coded responses to make tests pass.
3. Do not change the ML metrics or retrain models unless you find a real bug, and tell me if you do.
4. Keep fixes minimal and targeted; do not rewrite working modules.

---

## 4. FINAL REPORT (required format)

Give me:
1. A table of bugs found, cause, and fix status (fixed / not fixed).
2. The contract mismatch table from section B.
3. Test results (backend, frontend, Playwright) with pass/fail counts.
4. Performance numbers and Lighthouse scores.
5. A short list of remaining known issues.

Start with an 8-line plan and the exact commands you will use to start both services.

---

## FINISH CHECKLIST (every item must be true before you hand off)

- Backend (`:8000`) and frontend (`:3000`) run together and every page works with REAL data (mock off).
- Contract mismatches are fixed and listed.
- Playwright specs exist in `frontend/e2e/` and pass; backend `pytest` passes.
- `.env.example` defaults to `NEXT_PUBLIC_USE_MOCK=false`.
- `docs/INTEGRATION_REPORT.md` exists and is honest about anything unfixed.
- `python scripts/check_phase.py 4` prints **OK. All checks passed.**
- `git status` shows no changes to protected files (README.md, docs/HLD.md, docs/LLD.md, prompts/, scripts/check_phase.py).

## GIT HAND-OFF (run exactly, in this order)

```bash
git add -A
git commit -m "phase 4: integration, e2e tests and fixes"
git checkout main
git pull origin main
git merge --no-ff phase-4-integration -m "Merge phase 4"
python scripts/check_phase.py 4
git push origin main
git tag phase-4-complete
git push origin phase-4-complete
```
If the push is rejected, do NOT force push. Run `git pull --rebase origin main`, re-run the check, and push again. If there is a conflict you cannot resolve safely, stop and ask me.

When done, tell me: the final commit hash, a 5-line summary of what you built, and anything unfinished.
