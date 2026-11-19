
# TruthLens — AI-Based Fake Product Review Detection

<p align="center">
  <strong>Detect Suspicious Reviews. Understand the Signals. Make Smarter Decisions.</strong>
</p>

<p align="center">
  <a href="https://ai-based-fake-product-review-detect.vercel.app/">
    <strong>🚀 LIVE DEMO</strong>
  </a>
  &nbsp; | &nbsp;
  <a href="https://ai-based-fake-product-review-detection-b4hz.onrender.com/docs">
    <strong>📚 API DOCUMENTATION</strong>
  </a>
  &nbsp; | &nbsp;
  <a href="https://github.com/rohitgujjjar05feb-cloud/AI-Based-Fake-Product-Review-Detection">
    <strong>💻 SOURCE CODE</strong>
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-Next.js-black?logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Language-Python-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Language-TypeScript-blue?logo=typescript" alt="TypeScript">
  <img src="https://img.shields.io/badge/Machine%20Learning-scikit--learn-orange?logo=scikitlearn" alt="Scikit-learn">
  <img src="https://img.shields.io/badge/Deployment-Vercel-black?logo=vercel" alt="Vercel">
  <img src="https://img.shields.io/badge/Deployment-Render-46E3B7?logo=render" alt="Render">
</p>

**Author: Team TruthLens**

TruthLens is an AI-powered web application designed to analyze online product reviews and estimate whether a review resembles a **fake or genuine review**.

It combines Natural Language Processing (NLP), TF-IDF feature extraction, sentiment analysis, and machine learning algorithms to identify suspicious review patterns.

The application provides predictions, confidence scores, sentiment information, red flags, and explainability features through a modern and responsive web interface.

---

## 🌐 Live Deployment

| Component | Status | Link |
|---|---|---|
| Frontend | Live | [Open TruthLens](https://ai-based-fake-product-review-detect.vercel.app/) |
| Backend API | Deployed | [Render Backend](https://ai-based-fake-product-review-detection-b4hz.onrender.com/) |
| API Documentation | Available | [FastAPI Swagger Docs](https://ai-based-fake-product-review-detection-b4hz.onrender.com/docs) |
| Health Check | Available | [API Health](https://ai-based-fake-product-review-detection-b4hz.onrender.com/api/health) |
| GitHub Repository | Available | [View Source Code](https://github.com/rohitgujjjar05feb-cloud/AI-Based-Fake-Product-Review-Detection) |

**Deployment Architecture:**
- Frontend: Vercel
- Backend: Render
- Database: SQLite

> Note: The backend uses Render's free hosting service. It may spin down after inactivity, so the first request can take some time to respond. The free filesystem is ephemeral, so SQLite history may not persist across restarts or redeployments.

---

## 📌 Table of Contents

1. [Problem Statement](#-problem-statement)
2. [Project Objectives](#-project-objectives)
3. [Key Features](#-key-features)
4. [Technology Stack](#-technology-stack)
5. [System Architecture](#-system-architecture)
6. [Machine Learning Workflow](#-machine-learning-workflow)
7. [Dataset and Model Performance](#-dataset-and-model-performance)
8. [Project Structure](#-project-structure)
9. [Installation and Setup](#-installation-and-setup)
10. [Docker Deployment](#-docker-deployment)
11. [API Endpoints](#-api-endpoints)
12. [Advanced Features](#-advanced-features)
13. [Limitations](#-limitations)
14. [Future Scope](#-future-scope)
15. [Team Workflow](#-team-workflow)
16. [Troubleshooting](#-troubleshooting)

---

## 🎯 Problem Statement

Online reviews play an important role in customer purchasing decisions. However, fake, misleading, exaggerated, and deceptive reviews can influence customers and reduce trust in online platforms.

Manually checking thousands of reviews is difficult and time-consuming.

TruthLens addresses this problem by using NLP and machine learning techniques to analyze review text and identify patterns associated with deceptive or genuine reviews.

## 🎯 Project Objectives

- Identify suspicious and potentially deceptive review patterns.
- Classify reviews as fake or genuine using machine learning.
- Analyze the sentiment expressed in reviews.
- Display prediction confidence and relevant text signals.
- Support analysis of multiple reviews through CSV upload.
- Provide explainability to help users understand model predictions.
- Offer a simple, responsive, and user-friendly interface.

---

## ✨ Key Features

### 1. Single Review Analysis
- Enter a review and analyze it instantly.
- Get a Fake/Genuine prediction.
- View the model confidence score.
- Analyze review sentiment.
- Identify suspicious text patterns and red flags.

### 2. Explainable AI
- Highlights important words influencing predictions.
- Provides word-level explanations.
- Helps users understand why a model may classify a review as fake or genuine.

### 3. Multiple Machine Learning Models
- Multinomial Naive Bayes.
- Support Vector Machine (SVM).
- Best (Auto) model selection.

### 4. Batch Review Analysis
- Upload multiple reviews using a CSV file.
- Analyze reviews in batches.
- View summary results.
- Filter analysis results.
- Export results as CSV.

### 5. Model Lab
- View model performance metrics.
- Accuracy, Precision, Recall, and F1-score.
- ROC-AUC.
- Confusion matrices.
- ROC curves.
- Compare TF-IDF and TF-IDF with sentiment features.

### 6. Analysis History
- View previous review analyses.
- Search and filter history.
- Delete individual records.
- Clear analysis history.

### 7. Advanced Detection Features
- Tier-1 rule-based spam filtering.
- Sarcasm risk identification.
- SHAP-based explanations for the linear SVM.
- Log-probability explanations for Naive Bayes.

### 8. Modern User Interface
- Responsive Next.js interface.
- Dark and light themes.
- Animated user interface.
- Interactive analysis dashboard.
- How It Works pipeline visualization.

---

## 🛠 Technology Stack

| Category | Technologies |
|---|---|
| Frontend | Next.js 14+, TypeScript |
| Styling | Tailwind CSS |
| Animations | Framer Motion |
| Charts | Recharts |
| Backend | Python, FastAPI |
| API Validation | Pydantic v2 |
| Database | SQLite, SQLAlchemy |
| Machine Learning | Scikit-learn |
| NLP | TF-IDF, NLTK |
| Sentiment Analysis | VADER |
| ML Algorithms | Multinomial Naive Bayes, SVM |
| Explainability | SHAP |
| Testing | Pytest, Playwright |
| Containerization | Docker, Docker Compose |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |
| Version Control | Git, GitHub |

---

## 🏗 System Architecture

```text
              USER
                |
                v
       NEXT.JS FRONTEND
         (Vercel Hosting)
                |
                v
          FASTAPI BACKEND
          (Render Hosting)
                |
                v
       TEXT PREPROCESSING
                |
                v
       TF-IDF FEATURE EXTRACTION
                |
                v
       MACHINE LEARNING MODELS
          /             \
         v               v
   NAIVE BAYES           SVM
          \             /
           v           v
          PREDICTION
                |
       +--------+--------+
       |        |        |
       v        v        v
   SENTIMENT CONFIDENCE EXPLANATION
       |        |        |
       +--------+--------+
                |
                v
        RESULTS DASHBOARD
```

**Important:** Training and inference use the same text-cleaning function and fitted preprocessing artifacts to maintain consistency.

For detailed diagrams, refer to:
- `docs/HLD.md`
- `docs/LLD.md`
- `docs/PROJECT_STRUCTURE.md`

---

## 🤖 Machine Learning Workflow

TruthLens follows a text-classification workflow:

1. Review text is received from the frontend.
2. Text preprocessing and cleaning are performed.
3. TF-IDF converts text into numerical features.
4. Machine learning models process the extracted features.
5. Naive Bayes and SVM generate predictions.
6. Sentiment analysis is performed using VADER.
7. Confidence and explanation information are prepared.
8. Results are returned through the FastAPI backend.
9. The frontend displays the analysis.

### Algorithms Used

**TF-IDF (Term Frequency–Inverse Document Frequency)**

Converts text into numerical features based on the importance of words.

**Multinomial Naive Bayes**

A probabilistic classification algorithm commonly used for text classification.

**Support Vector Machine (SVM)**

A supervised machine learning algorithm that finds a decision boundary between classes.

**VADER Sentiment Analysis**

Analyzes sentiment polarity and helps identify positive, negative, or neutral language.

---

## 📊 Dataset and Model Performance

### Dataset

The project uses the **Deceptive Opinion Spam Corpus** by Ott et al. (2011).

- Approximately 1,600 English hotel reviews.
- Approximately 800 deceptive reviews.
- Approximately 800 truthful reviews.

### Model Evaluation

For the latest measured results, refer to:

[`docs/MODEL_REPORT.md`](docs/MODEL_REPORT.md)

The report contains the model evaluation metrics and supporting results.

Important: The training dataset consists of hotel reviews, whereas the application is intended for product-review analysis. Therefore, performance may vary when analyzing reviews from different domains.

Predictions should be treated as model-based estimates, not absolute proof of deception.

---

## 📁 Project Structure

```text
AI-Based-Fake-Product-Review-Detection/
│
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   └── main.py
│   │
│   ├── ml/
│   ├── models/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── docs/
│   ├── HLD.md
│   ├── LLD.md
│   ├── API.md
│   ├── MODEL_REPORT.md
│   └── PRESENTATION_NOTES.md
│
├── prompts/
├── scripts/
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## 💻 Installation and Setup

### Prerequisites

Install the following:

- Git
- Python 3.11 or 3.12
- Node.js 20+
- npm
- VS Code or another suitable IDE

### Step 1: Clone the Repository

```bash
git clone https://github.com/rohitgujjjar05feb-cloud/AI-Based-Fake-Product-Review-Detection.git
```

Navigate into the project:

```bash
cd AI-Based-Fake-Product-Review-Detection
```

### Step 2: Backend Setup

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate it.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Download required NLTK resources:

```bash
python scripts/download_nltk.py
```

Start the backend:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Backend URL:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

### Step 3: Frontend Setup

Open a second terminal in the project root.

Navigate to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a file named `.env.local` inside the frontend folder.

Add:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=false
```

Start the frontend:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

The application should now connect to your local FastAPI backend.

---

## 🐳 Docker Deployment

Docker is supported for running the application services together.

From the project root:

```bash
docker compose up --build
```

Access the application:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

To stop the containers:

```bash
docker compose down
```

---

## 🔌 API Endpoints

Base URL:

```text
https://ai-based-fake-product-review-detection-b4hz.onrender.com
```

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/predict` | Analyze a single review |
| POST | `/api/predict/batch` | Analyze multiple reviews using CSV |
| POST | `/api/explain` | Generate review explanations |
| GET | `/api/models` | Get available models |
| GET | `/api/models/metrics` | Get model performance metrics |
| GET | `/api/history` | Retrieve analysis history |
| DELETE | `/api/history/{id}` | Delete a history record |
| DELETE | `/api/history` | Clear analysis history |
| GET | `/api/health` | Check backend health |

Explore and test the endpoints:

[Open Interactive Swagger API Documentation](https://ai-based-fake-product-review-detection-b4hz.onrender.com/docs)

---

## 🔬 Advanced Features

| Feature | Description |
|---|---|
| Tier-1 Rule Filter | Detects configured spam patterns such as repeated text and review flooding. |
| Sarcasm Risk Flag | Identifies selected positive-opening/negative-outcome patterns for human review. |
| SHAP Explanations | Provides word-level explanations for the linear SVM. |
| Naive Bayes Explanation | Uses log-probability-based explanations. |

### Environment Switches

| Variable | Purpose |
|---|---|
| `ENABLE_TIER1` | Enable or disable Tier-1 filtering |
| `ENABLE_SARCASM` | Enable or disable sarcasm risk detection |
| `ENABLE_SHAP` | Enable or disable SHAP explanations |

These features are configurable and their heuristic components should not be treated as independently validated classifiers.

---

## ⚠️ Limitations

- The current classifier is trained on approximately 1,600 English hotel reviews.
- Product-review performance may differ because of domain shift.
- Hindi and Hinglish review classification is not currently supported.
- The model analyzes text patterns; it cannot verify actual purchases.
- Star ratings and reviewer account history are not model inputs.
- Tier-1 filtering and sarcasm detection are heuristic features whose accuracy has not been independently measured on a labelled dataset.
- Sarcasm detection is a warning for human review, not a fake-review verdict.
- SHAP explanations apply to the linear SVM; Naive Bayes uses a different explanation method.
- The free hosting setup may have cold-start delays and non-persistent SQLite history.

---

## 🚀 Future Scope

Potential improvements include:

- Training on larger, labelled product-review datasets.
- Supporting Hindi and Hinglish using multilingual models such as MuRIL or XLM-RoBERTa.
- Improving domain generalization across shopping categories.
- Evaluating heuristic features on labelled datasets.
- Adding reviewer behaviour analysis where appropriate data is available.
- Improving LLM-generated review detection.
- Adding persistent cloud database storage.
- Improving scalability, monitoring, and production deployment.

---

## 👥 Team Workflow

The project was developed through five major phases and an additional advanced-features phase.

| Phase | Contribution |
|---|---|
| Phase 1 | Frontend UI and mock integration |
| Phase 2 | Machine Learning pipeline |
| Phase 3 | FastAPI backend development |
| Phase 3.5 | Advanced detection and explainability features |
| Phase 4 | Frontend/backend integration and testing |
| Phase 5 | Docker, documentation, and packaging |

The repository contains phase-specific prompts, scripts, and documentation for the development workflow.

---

## 🛠 Troubleshooting

| Problem | Solution |
|---|---|
| API appears offline | Check whether the Render backend is awake and responding. Retry after waiting. |
| CORS error | Verify that `CORS_ORIGINS` includes the exact deployed frontend URL. |
| Frontend uses mock data | Verify `NEXT_PUBLIC_USE_MOCK=false` in Vercel and redeploy. |
| API URL error | Verify `NEXT_PUBLIC_API_URL` in Vercel and redeploy. |
| Missing NLTK resources | Run `python scripts/download_nltk.py`. |
| Model loading error | Install the pinned backend dependencies. |
| Port already in use | Stop the existing process or use another available port. |
| Slow first request | Render Free may spin down after inactivity. Wait for the backend to wake up. |

---

## 📚 References

1. Ott, M., Choi, Y., Cardie, C., & Hancock, J. T. (2011). *Finding Deceptive Opinion Spam by Any Stretch of the Imagination.*
2. Scikit-learn Documentation — https://scikit-learn.org/
3. FastAPI Documentation — https://fastapi.tiangolo.com/
4. Next.js Documentation — https://nextjs.org/docs
5. NLTK Documentation — https://www.nltk.org/
6. VADER Sentiment Analysis — https://github.com/cjhutto/vaderSentiment

---

<p align="center">
  <strong>Built with ❤️ by Team TruthLens</strong>
  <br>
  AI-Based Fake Product Review Detection
  <br><br>
  <a href="https://ai-based-fake-product-review-detect.vercel.app/">
    🚀 Try TruthLens Live
  </a>
</p>
