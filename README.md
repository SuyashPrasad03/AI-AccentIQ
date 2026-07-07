# AI Pronunciation Coach

An AI-powered pronunciation coaching platform that analyses spoken English, scores phoneme-level accuracy, and generates personalised practice exercises.

> **Phase 1 — Foundation Skeleton** | See [docs/architecture.md](docs/architecture.md) for the system design (Phase 12 deliverable).

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TypeScript → Vercel |
| Backend | FastAPI (Python 3.11) → Render |
| Relational DB | MySQL 8.0 |
| Document DB | MongoDB 7.0 |
| Audio | FFmpeg · WhisperX · Phonemizer |
| LLM | OpenRouter → Gemini |
| Auth | JWT + email OTP |

---

## Local Setup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Compose)
- Git

### 1 — Clone and configure

```bash
git clone <repo-url>
cd pronunciation-coach

# Copy the example env file and fill in any values you want to override.
# The defaults work for local dev without any changes.
cp .env.example .env
```

Key variables to set for full functionality (optional for Phase 1):

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | LLM feedback + practice generation (Phases 6–9) |
| `SMTP_PASSWORD` | Transactional email for OTP (Phase 2); leave blank to use console fallback |

### 2 — Start the stack

```bash
docker compose up --build
```

This starts four containers:

| Container | Port | Description |
|---|---|---|
| `pronunciation_backend` | `8000` | FastAPI backend |
| `pronunciation_frontend` | `5173` | Vite dev server |
| `pronunciation_mysql` | `3306` | MySQL 8.0 |
| `pronunciation_mongo` | `27017` | MongoDB 7.0 |

### 3 — Verify

Open [http://localhost:5173](http://localhost:5173) — you should see a green "All Systems Operational" health page.

Or check the API directly:

```bash
curl http://localhost:8000/health
# → {"status":"ok","mysql":"connected","mongo":"connected"}
```

API docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

### 4 — Running backend tests locally

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

### 5 — Stopping / resetting

```bash
# Stop containers
docker compose down

# Full reset (removes DB volumes — loses all data)
docker compose down -v
```

---

## Project Structure

```
pronunciation-coach/
├── .github/workflows/    CI pipeline (lint + test on every push)
├── docs/                 Architecture document (Phase 12)
├── frontend/             React + Vite
│   └── src/
│       ├── api/          Typed API client functions
│       ├── features/     Feature-sliced UI modules
│       └── App.tsx       Root component (health page in Phase 1)
├── backend/
│   ├── app/
│   │   ├── core/         Settings, logging, exceptions
│   │   ├── db/           MySQL (SQLAlchemy) + MongoDB (Motor) clients
│   │   ├── modules/      Feature modules (auth, upload, scoring, etc.)
│   │   └── main.py       App factory
│   ├── alembic/          Database migrations
│   └── Dockerfile
├── scripts/              One-off utility scripts
├── docker-compose.yml
└── .env.example          All env vars documented with comments
```

---

## Development Workflow

- **Backend hot-reload**: Uvicorn `--reload` is on by default in Docker dev mode. Editing any `.py` file restarts instantly.
- **Frontend HMR**: Vite's hot module replacement works out of the box.
- **Database migrations**: Add a new Alembic migration:
  ```bash
  docker compose exec backend alembic revision --autogenerate -m "your description"
  docker compose exec backend alembic upgrade head
  ```
- **Linting** (backend): `ruff check backend/`
- **Linting** (frontend): `npm run lint` inside `frontend/`

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Current | Foundation, DevOps skeleton, health check |
| 2 | 🔜 | Auth, anonymous quota, DPDP consent |
| 3 | 🔜 | Audio upload, validation, preprocessing |
| 4 | 🔜 | WhisperX transcription + forced alignment |
| 5 | 🔜 | Phoneme scoring engine |
| 6 | 🔜 | AI feedback — "Explain My Mistake" |
| 7 | 🔜 | Personalised practice generator |
| 8 | 🔜 | Progress comparison & analytics |
| 9 | 🔜 | RAG-powered in-app assistant |
| 10 | 🔜 | DPDP compliance hardening |
| 11 | 🔜 | Security hardening + production deploy |
| 12 | 🔜 | Architecture doc + submission packaging |

---

## Environment Variables

See [`.env.example`](.env.example) — every variable is documented with a one-line comment.

---

## CI

GitHub Actions runs on every push:
- **Backend**: `ruff` lint → `pytest` unit tests
- **Frontend**: ESLint → `tsc` type-check → Vite build

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
