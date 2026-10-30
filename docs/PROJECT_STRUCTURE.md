# Project structure (final, after all 5 phases)

Legend: [S] = already in the starter repo (protected, never edit) | P1..P5 = created in that phase.

```
truthlens/
├── README.md                          [S] team guide, never edit
├── Makefile                           [S]
├── .gitignore                         [S]
├── .env.example                       [S]  (P4 flips NEXT_PUBLIC_USE_MOCK to false)
├── docker-compose.yml                 P5
├── .githooks/pre-commit               [S] blocks edits to protected files
├── prompts/                           [S] one prompt file per phase
│   ├── phase-1-ui.md
│   ├── phase-2-ml-pipeline.md
│   ├── phase-3-backend-api.md
│   ├── phase-4-integration-testing.md
│   └── phase-5-docker-docs.md
├── scripts/
│   ├── check_phase.py                 [S] phase gatekeeper
│   ├── protected.sha256               [S]
│   ├── download_nltk.py               [S]
│   └── generate_report.py             P5
├── docs/
│   ├── HLD.md                         [S]
│   ├── LLD.md                         [S]
│   ├── PROJECT_STRUCTURE.md           [S]
│   ├── INTEGRATION_REPORT.md          P4
│   ├── MODEL_REPORT.md                P5
│   ├── API.md                         P5
│   ├── PRESENTATION_NOTES.md          P5
│   └── screenshots/*.png              P5
├── backend/
│   ├── requirements.txt               [S] pinned versions
│   ├── pytest.ini                     [S]
│   ├── Dockerfile                     P5
│   ├── data/raw/                      dataset goes here (git-ignored, Member 2 only)
│   ├── models/                        P2 (artifacts + metrics.json ARE committed)
│   ├── ml/                            P2
│   │   ├── config.py  preprocess.py  features.py
│   │   ├── train_nb.py  train_svm.py  evaluate.py  run_pipeline.py
│   ├── app/                           P3
│   │   ├── main.py  config.py  schemas.py
│   │   ├── routers/  predict.py models.py history.py health.py
│   │   ├── services/ predictor.py explain.py flags.py sentiment.py
│   │   └── db/       database.py models.py
│   └── tests/
│       ├── test_ml.py                 P2
│       ├── test_api.py                P3
│       └── test_services.py           P3
└── frontend/                          P1 (Next.js, TypeScript, src/ directory)
    ├── package.json  tailwind.config.ts  playwright.config.ts (P4)  Dockerfile (P5)
    ├── e2e/*.spec.ts                  P4
    └── src/
        ├── app/ (layout, page, analyze, batch, model-lab, history, how-it-works)
        ├── components/ (ui, layout, analyzer, batch, lab, history)
        ├── lib/ (api.ts, mockApi.ts, types.ts, utils.ts)
        └── styles/globals.css
```
