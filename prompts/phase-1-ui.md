# PHASE 1 PROMPT: UI (Frontend, mock mode)

> Give this ENTIRE file to your Antigravity agent. It is Phase 1 of 5. Read `README.md` and `docs/LLD.md` first.

---

## 0. TEAM CONTEXT (read first, these rules override anything below)

- This is the **TruthLens** monorepo. The folder skeleton already exists. Do NOT recreate the structure; fill in only your phase.
- Five people work in strict order. You do **ONLY Phase 1**. Earlier phases are finished and already in git. Do not rewrite or "improve" their work.
- **PROTECTED files, never edit:** README.md, docs/HLD.md, docs/LLD.md, docs/PROJECT_STRUCTURE.md, everything in prompts/, everything in .githooks/, scripts/check_phase.py, scripts/protected.sha256. A git pre-commit hook blocks commits that touch them.
- **You MAY create or change:** everything inside `frontend/`, and the git-ignored file `frontend/.env.local`.
- **You must NOT change:** anything in `backend/`, `.env.example`, `Makefile`, `scripts/`, `docs/`, and the protected files.
- Never use `git push --force`. Never commit secrets, `node_modules`, `.venv`, or the raw dataset.

### 0.1 Start checklist (run these first)

```bash
git checkout main
git pull origin main --tags
git config core.hooksPath .githooks
python scripts/check_phase.py --ready 1
git checkout -b phase-1-ui
```
If `check_phase.py --ready 1` prints NOT READY, **stop and tell me**. Do not try to fix earlier phases.

### 0.2 Adjustments for this repo (these override anything below that conflicts)

1. The repo skeleton already exists. `frontend/` currently contains only `.gitkeep`. Delete `frontend/.gitkeep`, then initialize Next.js INSIDE the existing `frontend/` folder (TypeScript, Tailwind, App Router, **`src/` directory enabled**, ESLint). Do not create a new top-level folder.
2. Use the exact file names from the folder structure below. A checker script looks for them: `src/app/{layout,page}.tsx`, `src/app/{analyze,batch,model-lab,history,how-it-works}/page.tsx`, `src/lib/{types,api,mockApi}.ts`, and `src/components/analyzer/{ConfidenceGauge,VerdictCard,HighlightedText,SentimentMeter}.tsx`.
3. `src/lib/api.ts` must read `process.env.NEXT_PUBLIC_USE_MOCK` and switch between the real client and `mockApi.ts`. Create `frontend/.env.local` from the root `.env.example` with `NEXT_PUBLIC_USE_MOCK=true` (this file is git-ignored). Do NOT edit the root `.env.example`.
4. Ignore rule 4 below about writing a README. **Never edit the root `README.md`.** You may keep the auto-generated `frontend/README.md`.
5. The mock data must look realistic and follow the API contract exactly (see `docs/LLD.md`). The mock `metrics` response must have the same shape as `metrics.json` in `docs/LLD.md`, so Model Lab works unchanged when the real API arrives in Phase 4.

---

---

## 1. GOAL

Build only the **frontend** of a web app called **TruthLens** (working name) that detects fake product reviews. The backend (FastAPI + Naive Bayes/SVM) is built separately, so your job is a premium, distinctive, production-quality UI that talks to a documented API.

The UI must look like a funded startup product, not a student project. Design quality is the top priority.

---

## 2. STACK (fixed)

- Next.js 14+ (App Router), TypeScript
- Tailwind CSS + shadcn/ui primitives (heavily restyled, never default)
- Framer Motion for animation, Recharts for charts, custom SVG for the gauge
- Lucide icons only, no emoji in the UI
- Fonts via `next/font`: Space Grotesk (headings), Inter (body), JetBrains Mono (numbers)

---

## 3. API CONTRACT (the UI consumes this)

Base URL from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

- `POST /api/predict` with `{ review, rating?, model: "best" | "nb" | "svm" }` returns:
```json
{
  "id": 1, "verdict": "fake | genuine", "fake_probability": 0.87, "confidence": 0.87,
  "model_used": "svm",
  "sentiment": { "compound": 0.92, "label": "Positive", "pos": 0.6, "neu": 0.4, "neg": 0.0 },
  "flags": [{ "code": "ALL_CAPS", "label": "Words in ALL CAPS", "severity": "low | medium | high" }],
  "tokens": [{ "token": "amazing", "score": 1.42, "direction": "fake | genuine" }],
  "meta": { "words": 14, "exclamations": 7, "caps_words": 3 },
  "latency_ms": 18, "created_at": "ISO-8601"
}
```
- `POST /api/predict/batch` (multipart CSV, column `review`, optional `rating`) returns rows plus `summary { total, fake_count, fake_percent, avg_confidence }`
- `GET /api/models/metrics` returns per-model `accuracy, precision, recall, f1, roc_auc, confusion_matrix, roc_curve`, plus `best_model`, `dataset { size, fake_percent }`, and results for "tfidf only" vs "tfidf + sentiment"
- `GET /api/history?search=&verdict=&limit=&offset=`, `DELETE /api/history/{id}`, `DELETE /api/history`
- `GET /api/health` returns `{ status, models_loaded, version }`

**Mock mode:** create `lib/api.ts` with a real client and a separate `lib/mockApi.ts`, switched by `NEXT_PUBLIC_USE_MOCK=true`. Mock data lets you build and demo the UI before the backend exists. Mock data must be clearly isolated in `mockApi.ts`, never mixed into components, and the final build must default to the real API. Define all response types in `lib/types.ts`.

---

## 4. PAGES AND FEATURES

1. **Landing `/`**: full-viewport hero with animated aurora background, gradient-highlighted headline, a live mini analyzer (textarea + sample chips), animated stat counters (accuracy, F1, reviews trained on) from `/api/models/metrics`, a features bento grid, and a final CTA.
2. **Analyze `/analyze`** (main page): two columns on desktop.
   - Left: input card with textarea, character counter, optional star rating, model switch (Best / Naive Bayes / SVM), sample review chips, Analyze button (Ctrl+Enter shortcut).
   - Right: result bento with verdict card, confidence gauge, sentiment meter, review text with highlighted words, top 5 contributing tokens, red-flag list, meta stats, and a copy-result button.
3. **Batch `/batch`**: drag-and-drop CSV zone with template download, upload progress, summary cards, donut chart (fake vs genuine), sortable/filterable results table with verdict pills, Export CSV button.
4. **Model Lab `/model-lab`**: metric cards per model, side-by-side comparison bars, confusion matrices, ROC curves, toggle "TF-IDF only vs TF-IDF + sentiment", dataset info card.
5. **History `/history`**: searchable list, verdict filter chips, relative timestamps, expandable rows, delete and clear-all with confirmation.
6. **How it works `/how-it-works`**: animated pipeline (Input, Clean, Tokenize, Lemmatize, TF-IDF + Sentiment, Model, Verdict) with hover explanations, plus plain-language cards for TF-IDF, Naive Bayes, SVM and VADER.
7. **Global shell**: floating glass pill navbar with animated active indicator, theme toggle, API status chip (from `/api/health`), footer, command palette (Ctrl/Cmd+K) for navigation, theme toggle and loading sample reviews, toasts.

---

## 5. DESIGN LANGUAGE: "FORENSIC INTELLIGENCE"

A luxury security/analytics feel, like a high-end fintech or cybersecurity product.

**Dark theme (default, the hero experience)**
- Background `#07080C` with a subtle, slowly drifting radial aurora (indigo, violet, teal at very low opacity), a faint dotted grid and a light grain overlay.
- Glass cards: fill `rgba(255,255,255,0.04)`, 1px border `rgba(255,255,255,0.08)`, backdrop blur 16-24px, radius 20-24px.

**Light theme**: warm off-white `#F7F6F3`, soft shadows, same accent logic. It must look equally polished.

**Color meaning (be strict)**
- Brand gradient: violet to cyan (brand moments only)
- Crimson/coral = Fake, Emerald/mint = Genuine, Amber = warning

**Type and layout**: big confident headline with tight letter-spacing, numbers in JetBrains Mono with tabular figures, 12-column grid, max width ~1240px, 8px spacing scale, bento layouts for results and Model Lab.

**Tokens**: define all colors, radii, shadows and spacing as CSS variables / Tailwind tokens. No one-off hard-coded colors inside components.

---

## 6. SIGNATURE COMPONENTS (custom and polished)

1. **ConfidenceGauge**: custom SVG radial gauge, animated sweep, gradient stroke, count-up number in the center, color shifts mint to coral as fake probability rises.
2. **VerdictCard**: large "Likely Fake" / "Likely Genuine" with a glowing halo and a pulse on reveal.
3. **HighlightedText**: words tinted by score intensity (coral = fake-leaning, mint = genuine-leaning) with hover tooltips showing the score.
4. **SentimentMeter**: gradient track with an animated marker.
5. **Scanner animation**: while waiting for the API, a scanning sweep over the textarea and staged labels (Cleaning, Extracting features, Scoring), then a staggered result reveal. Do not add fake delays beyond about 600 ms.
6. **PipelineVisual**: nodes joined by animated flowing lines.
7. **Charts**: custom dark-friendly Recharts (confusion matrix heatmap, ROC, comparison bars) with entrance animations and tooltips.
8. **Microinteractions**: button press scale, hover glow, magnetic primary CTA, page transitions (soft fade/slide), shimmer skeleton loaders for every async region, illustrated empty states.

---

## 7. QUALITY BAR

- Responsive from 360px to 1920px; keyboard accessible; visible focus states; WCAG AA contrast in both themes.
- Respect `prefers-reduced-motion`; animate only `transform` and `opacity`.
- Every component has default, hover, focus, active, disabled, loading, error and empty states.
- Lighthouse target: Performance 90+, Accessibility 95+. No layout shift. Lazy-load charts.
- Sanitize all rendered user text; never use `dangerouslySetInnerHTML` with user input.
- Do not ship the default shadcn look, default Tailwind blue, or generic purple-gradient "AI template" styling. Everything should look intentionally designed.

---

## 8. FOLDER STRUCTURE

```
frontend/src/
├── app/ (layout.tsx, page.tsx, analyze/, batch/, model-lab/, history/, how-it-works/)
├── components/
│   ├── ui/        (restyled primitives)
│   ├── layout/    (Navbar, Footer, ThemeToggle, StatusChip, CommandPalette)
│   ├── analyzer/  (ReviewInput, VerdictCard, ConfidenceGauge, HighlightedText,
│   │               SentimentMeter, FlagList, ModelSwitch, TopTokens)
│   ├── batch/     (DropZone, ResultsTable, SummaryStats)
│   ├── lab/       (MetricCards, ConfusionMatrix, RocChart, ComparisonBars)
│   └── history/   (HistoryList, HistoryFilters)
├── lib/ (api.ts, mockApi.ts, types.ts, utils.ts)
└── styles/globals.css
```

---

## 9. RULES FOR YOU

1. Build in this order and verify after each step by running the app and showing me a screenshot:
   - Step 1: scaffold, design tokens, fonts, theme provider, shell (navbar, footer, status chip)
   - Step 2: Analyze page with all signature components (using mock mode)
   - Step 3: Batch, Model Lab, History, How it works
   - Step 4: Landing page
   - Step 5: polish, accessibility, responsive pass, switch to the real API client
2. No TODOs or unfinished sections. If something is blocked, tell me exactly what.
3. Keep components small and typed. Prefer readable code over clever code.
4. Add a short `README.md` with setup steps (`npm install`, `npm run dev`, env variables, mock vs real API).

Start with Step 1. Before writing code, summarize your plan in 8 lines and list any assumptions.

---

## FINISH CHECKLIST (every item must be true before you hand off)

- `cd frontend && npm install && npm run build` succeeds with no errors.
- All 6 pages (`/`, `/analyze`, `/batch`, `/model-lab`, `/history`, `/how-it-works`) render in mock mode, in dark and light theme, on desktop and 360px mobile width. Show me screenshots.
- Analyze flow works end to end on mock data: verdict, gauge, highlighted words, tokens, flags, sentiment, model switch.
- Batch upload, History filters/delete, and Model Lab charts work on mock data.
- `src/lib/types.ts` matches the API contract in `docs/LLD.md` exactly.
- `python scripts/check_phase.py 1` prints **OK. All checks passed.**
- `git status` shows no changes to protected files (README.md, docs/HLD.md, docs/LLD.md, prompts/, scripts/check_phase.py).

## GIT HAND-OFF (run exactly, in this order)

```bash
git add -A
git commit -m "phase 1: premium frontend UI (mock mode)"
git checkout main
git pull origin main
git merge --no-ff phase-1-ui -m "Merge phase 1"
python scripts/check_phase.py 1
git push origin main
git tag phase-1-complete
git push origin phase-1-complete
```
If the push is rejected, do NOT force push. Run `git pull --rebase origin main`, re-run the check, and push again. If there is a conflict you cannot resolve safely, stop and ask me.

When done, tell me: the final commit hash, a 5-line summary of what you built, and anything unfinished.
