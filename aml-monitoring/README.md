# AML Transaction Monitoring System

> Graph Neural Network–powered Anti-Money Laundering detection with explainable alerts and an interactive dashboard.

[![CI](https://github.com/YOUR_ORG/aml-monitoring/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/aml-monitoring/actions)

---

## Elevator Pitch

An end-to-end AML monitoring platform that generates realistic synthetic transaction networks (smurfing, layering, circular flows), trains a **GraphSAGE GNN** to detect suspicious entity clusters, produces **SHAP-explained case narratives** in regulator-ready format, and serves everything through a **FastAPI + PostgreSQL** backend and a polished **React** dashboard — launched with one Docker command.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Compose                        │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  PostgreSQL  │◄───│   FastAPI    │◄───│    React     │   │
│  │  (pgdata vol)│    │  + Uvicorn   │    │  + Tailwind  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                             │                               │
│                     ┌───────┴────────┐                      │
│                     │   ML Pipeline  │                      │
│                     │                │                      │
│                     │ NetworkX Graph │                      │
│                     │ ↓              │                      │
│                     │ 18-dim Node    │                      │
│                     │ Features       │                      │
│                     │ ↓              │                      │
│                     │ GraphSAGE GNN  │                      │
│                     │ (PyG / PyTorch)│                      │
│                     │ ↓              │                      │
│                     │ XGBoost SHAP   │                      │
│                     │ Surrogate      │                      │
│                     └────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Technology |
|---|---|
| Data generation | Python + NetworkX |
| ML | PyTorch + PyTorch Geometric (GraphSAGE) |
| Explainability | XGBoost surrogate + SHAP TreeExplainer |
| Baselines | Logistic Regression + rule-based heuristics |
| API | FastAPI + Pydantic + SQLAlchemy |
| Database | PostgreSQL 15 |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Visualisation | react-force-graph-2d + Recharts |
| DevOps | Docker Compose + GitHub Actions |

---

## Quick Start

### Prerequisites
- Docker ≥ 24 and Docker Compose v2
- ~4 GB RAM free

```bash
git clone https://github.com/YOUR_ORG/aml-monitoring.git
cd aml-monitoring
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---|---|
| **Dashboard** | http://localhost:5173 |
| **API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |

### Running the Demo

1. Open http://localhost:5173
2. Click **Run Demo**
3. Wait ~2 minutes (generation + training)
4. Explore alerts → click **View Case →** → see narrative + SHAP chart
5. Visit **Graph Explorer** to visualise clusters

---

## Dataset Modes

| Mode | Entities | Transactions | Patterns | Training time |
|---|---|---|---|---|
| `demo` | 1,000 | ~5,000 | 6 smurfing + 10 layering + 5 circular | **< 2 min (CPU)** |
| `full` | 15,000 | ~150,000 | 90 + 140 + 70 | 15–40 min (CPU) |

### Full run via CLI
```bash
docker compose exec api python scripts/full_run.py
```

---

## Node Features (18-dim)

| Feature | Description |
|---|---|
| `total_sent` / `total_received` | Log-scaled aggregate transaction volume |
| `num_sent` / `num_received` | Log-scaled transaction counts |
| `avg_sent` / `avg_received` | Log-scaled average transaction sizes |
| `max_sent` / `max_received` | Log-scaled peak transaction |
| `in_out_ratio` | Receives relative to sends (≈1 = pass-through) |
| `geo_diversity` | Unique countries transacted with |
| `channel_diversity` | Unique payment channels used |
| `unique_counterparties` | Log-scaled distinct counterparty count |
| `burstiness` | Coefficient of variation of inter-transaction intervals |
| `risk_flag_count` | Accumulated structuring/high-risk flags |
| `degree_centrality` | Graph degree centrality |
| `in_degree_centrality` | In-degree centrality |
| `entity_type_enc` | 0=individual, 1=business, 2=mule, 3=shell |
| `country_risk` | 1 if domiciled in high-risk jurisdiction |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/stats` | Overview counts + model metrics |
| `POST` | `/generate?size=demo\|full` | Generate synthetic data |
| `POST` | `/train?mode=demo\|full` | Train GNN model |
| `GET` | `/alerts?limit=&offset=` | Paginated alerts |
| `GET` | `/clusters/top?limit=` | Top suspicious clusters |
| `GET` | `/cases/{id}` | Full case detail + SHAP |
| `GET` | `/graph/cluster/{id}` | Subgraph for visualisation |
| `GET` | `/metrics` | Latest model run metrics |

---

## Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu
pip install torch-geometric==2.4.0
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev      # proxies /api → http://localhost:8000
```

---

## Running Tests

```bash
# In container
docker compose exec api pytest app/tests/ -v

# Locally
cd backend && pytest app/tests/ -v
```

---

## Deployment

### Frontend → GitHub Pages

```bash
cd frontend
# Set the API URL in .env.production if your backend is remote
echo "VITE_API_URL=https://your-backend.onrender.com" > .env.production
npm run build
# Push dist/ to gh-pages branch
```

### Backend → Render

1. Push to GitHub
2. Create a new **Web Service** at render.com pointing to this repo
3. Set **Root Directory** = `backend`
4. Add the `render.yaml` (included) — Render auto-provisions a Postgres database
5. Set `DATABASE_URL` from the provisioned database in environment variables

---

## Resume Bullets

```
• Designed an end-to-end AML detection platform using PyTorch Geometric GraphSAGE
  for node-level fraud detection on synthetic networks of 100K+ transactions, achieving
  high precision/recall on a class-imbalanced (5% positive) dataset.

• Engineered 18-dimensional entity features (centrality, burstiness, geo-diversity,
  in/out ratios) from transaction graphs; GNN consistently outperforms logistic
  regression and rule-based baselines across precision, recall, and F1.

• Implemented SHAP explainability via an XGBoost surrogate trained on GNN embeddings,
  producing per-feature attributions and regulator-ready SAR-style case narratives for
  every alert.

• Containerised full-stack system (FastAPI + React + PostgreSQL) with Docker Compose,
  GitHub Actions CI/CD, and one-command local deployment.
```

---

## License

MIT
