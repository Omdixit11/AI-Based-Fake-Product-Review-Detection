# Thin wrappers. On Windows without make, run the underlying commands directly.
PHASE ?= 1

setup:            ## install backend + frontend deps and NLTK data
	cd backend && pip install -r requirements.txt
	python scripts/download_nltk.py
	@if [ -f frontend/package.json ]; then cd frontend && npm install; fi

train:            ## Phase 2 command: run the ML pipeline
	cd backend && python -m ml.run_pipeline

dev-backend:      ## run FastAPI on :8000
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:     ## run Next.js on :3000
	cd frontend && npm run dev

test:             ## backend tests (frontend/e2e tests are run by Phase 4)
	cd backend && python -m pytest tests -q

ready:            ## confirm previous phases are complete before you start:  make ready PHASE=2
	python scripts/check_phase.py --ready $(PHASE)

check:            ## confirm YOUR phase is complete before you push:  make check PHASE=2
	python scripts/check_phase.py $(PHASE)

docker-up:
	docker compose up --build

docker-down:
	docker compose down
