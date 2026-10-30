# TruthLens Frontend

Next.js 14 (App Router, TypeScript, `src/` directory) + Tailwind CSS +
Framer Motion + Recharts + Lucide.

## Run it

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # production build
```

## Environment

Create `frontend/.env.local` (git-ignored):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=true
```

- `NEXT_PUBLIC_USE_MOCK=true` — the UI runs on realistic mock data from
  `src/lib/mockApi.ts` (no backend needed). This is the Phase 1–3 default.
- `NEXT_PUBLIC_USE_MOCK=false` — the UI calls the real FastAPI backend at
  `NEXT_PUBLIC_API_URL` (used from Phase 4 onward).

The switch happens in `src/lib/api.ts`; mock data is fully isolated in
`src/lib/mockApi.ts` and never leaks into components.

## Pages

| Route | Purpose |
|---|---|
| `/` | Landing: hero, live mini analyzer, stat counters, features bento |
| `/analyze` | Single review analyzer (verdict, gauge, highlights, tokens, flags) |
| `/batch` | CSV batch analysis with summary, table and CSV export |
| `/model-lab` | Training metrics, ROC curves, confusion matrices |
| `/history` | Recorded analyses: search, filter, delete |
| `/how-it-works` | Animated pipeline and plain-language concept cards |

`Ctrl/Cmd+K` opens the command palette. The theme toggle lives in the navbar;
dark is the default theme.
