# Command Center

Command Center is an AI-assisted academic workload optimizer for students. It lets you enter assignments, exams, and projects with deadlines and estimated effort, then calculates whether your workload is realistically feasible, detects deadline collisions, and generates a practical daily execution plan.

---

## Prerequisites

- Python 3.10+
- pip
- Docker (optional, for containerized deployment)
- OpenAI API key (optional, for AI-assisted task extraction and risk explanation)

---

## Local Setup

```bash
git clone <repo-url>
cd command-center
pip install -r requirements.txt
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Docker Setup

```bash
docker compose up --build
```

Open [http://localhost:8501](http://localhost:8501). Task data is persisted at `./data/tasks.json` on the host (the `./data/` directory is created automatically on first run and is excluded from git by `.gitignore`).

---

## Enabling AI Features

Set the `OPENAI_API_KEY` environment variable before starting the app:

```bash
export OPENAI_API_KEY=sk-...
streamlit run app.py
```

For Docker, uncomment the `OPENAI_API_KEY` line in `docker-compose.yml`. The app is fully functional without a key — the AI tab simply does not appear.

---

## Architecture

The project uses a flat four-package structure:

| Package | Responsibility |
|---|---|
| `core/` | Pure Python business logic — task CRUD, priority scoring, plan generation, workload metrics. No Streamlit. Independently unit-testable. |
| `ui/` | Streamlit tab renderers. Imports from `core/` and `ai/`; performs no calculations. |
| `ai/` | OpenAI wrapper with graceful fallback. Returns `[]` / `""` on any failure; never raises to callers. |
| `tests/` | pytest tests covering all `core/` and `ai/` modules. No Streamlit session required. |

`app.py` is the Streamlit entry point. It wires the sidebar settings and tab layout, then delegates to `ui/` renderers.

All persistent state lives in a single `tasks.json` file (or the path specified by `TASKS_FILE`). No database, no authentication, no microservices.

---

## Scoring Formula

Each task receives a deterministic priority score used for scheduling:

```
score = (priority_weight × 0.4) + (urgency_normalized × 0.4) + (effort_normalized × 0.2)
```

| Component | Description |
|---|---|
| `priority_weight` | Raw integer: High=3, Medium=2, Low=1 |
| `urgency_normalized` | `1 / (days_until_deadline + 1)` divided by the maximum urgency across all tasks |
| `effort_normalized` | `estimated_effort_hours / max(effort_hours)` across all tasks |

Scores above 1.0 are valid (e.g., a single High-priority task scores exactly 1.8). They are used only for relative ordering, not as probabilities.

---

## Running Tests

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## CI

GitHub Actions runs two jobs on every push and pull request:

1. **test** — installs dependencies, runs `pytest tests/ -v`.
2. **docker** — builds the Docker image (only if tests pass).

No `OPENAI_API_KEY` is set in CI; all AI tests run the fallback path.
