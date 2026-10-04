# Command Center

**An AI-assisted academic workload optimizer for students.**

Command Center lets you enter assignments, exams, and projects with deadlines and estimated effort. It calculates whether your workload is realistically feasible, detects deadline collisions, prioritizes tasks with a transparent deterministic algorithm, and generates a practical daily execution plan.

The application is fully functional without an AI API key. AI features (natural-language task extraction, workload risk narration) are optional and activate automatically when `OPENAI_API_KEY` is set.

---

## Features

- **Task management** — add, edit, and delete tasks with name, course, deadline, estimated effort, priority, and description
- **Dashboard** — live metrics: total tasks, required hours, available hours, surplus/deficit, and upcoming deadlines
- **Deterministic priority scoring** — transparent formula with visible component breakdown per task
- **Overload detection** — flags when total required hours exceed available time before the last deadline
- **Collision detection** — flags individual tasks whose effort cannot fit in the time remaining before their deadline
- **Daily execution plan** — ordered day-by-day schedule that respects your available hours per day
- **Optional AI assistance** — paste syllabus text to extract tasks, or get a plain-English workload risk summary (requires `OPENAI_API_KEY`)

---

## Prerequisites

- Python 3.10+
- pip
- Docker (optional, for containerized deployment)
- OpenAI API key (optional, for AI features)

---

## Quick Start

```bash
git clone https://github.com/your-username/command-center.git
cd command-center
pip install -r requirements.txt
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Docker

```bash
docker compose up --build
```

Open [http://localhost:8501](http://localhost:8501). Task data is persisted to `./data/tasks.json` on the host via a volume mount. The `./data/` directory is created automatically on first run and is excluded from git.

---

## Enabling AI Features

Set `OPENAI_API_KEY` before starting the app:

```bash
export OPENAI_API_KEY=sk-...   # macOS / Linux
$env:OPENAI_API_KEY="sk-..."   # Windows PowerShell

streamlit run app.py
```

For Docker, uncomment the `OPENAI_API_KEY` line in `docker-compose.yml`. The app is fully functional without a key — the AI tab simply does not appear.

---

## Project Structure

```
command-center/
├── app.py                   # Streamlit entry point; sidebar settings + tab wiring
├── core/
│   ├── task_manager.py      # Task & Settings dataclasses, CRUD, JSON persistence
│   ├── scheduler.py         # Priority scoring, daily plan generation
│   └── workload.py          # Aggregate metrics, collision & overload detection
├── ui/
│   ├── dashboard.py         # Dashboard tab renderer
│   ├── tasks.py             # Task list display + add/edit/delete form
│   ├── plan_view.py         # Daily execution plan tab renderer
│   └── ai_panel.py          # AI assistant tab renderer
├── ai/
│   └── assistant.py         # OpenAI wrapper with graceful fallback
├── tests/
│   ├── test_task_manager.py
│   ├── test_scheduler.py
│   ├── test_workload.py
│   └── test_ai_assistant.py
├── Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

`core/` is pure Python — no Streamlit dependency — so every business-logic function is independently unit-testable. `ui/` imports from `core/` and renders results; it performs no calculations. `ai/` is isolated behind an import guard and never raises to its callers.

All persistent state lives in a single `tasks.json` file (path overridable via `TASKS_FILE` env var). No database, no authentication, no microservices.

---

## Scoring Formula

Each task receives a deterministic priority score used for scheduling:

```
score = (priority_weight × 0.4) + (urgency_normalized × 0.4) + (effort_normalized × 0.2)
```

| Component | Description |
|---|---|
| `priority_weight` | Raw integer — High=3, Medium=2, Low=1 |
| `urgency_normalized` | `1 / (days_until_deadline + 1)` divided by the maximum urgency across all tasks (max-normalization) |
| `effort_normalized` | `estimated_effort_hours / max(effort_hours)` across all tasks (max-normalization) |

Scores above 1.0 are valid (a single High-priority task scores exactly 1.8). They are used only for relative ordering, never as probabilities.

---

## Running Tests

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest tests/ -v
```

28 tests across `core/` and `ai/` modules. No Streamlit session or API key required.

---

## CI

GitHub Actions runs two jobs on every push and pull request:

1. **test** — installs dependencies, runs `pytest tests/ -v` on Python 3.11
2. **docker** — builds the Docker image (only if tests pass)

No `OPENAI_API_KEY` is set in CI; all AI tests exercise the graceful fallback path.

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `TASKS_FILE` | `tasks.json` | Path to the JSON file used for task persistence |
| `OPENAI_API_KEY` | *(unset)* | Enables AI features when set to a valid OpenAI key |

---

## License

MIT

## How Kiro Was Used

Kiro was used as an agentic development environment throughout
the project lifecycle rather than only for code completion.

### Requirements
Kiro generated and refined the functional requirements and
acceptance criteria.

### Design
Kiro iteratively reviewed the architecture and identified
issues including urgency normalization, invalid workload
limits, and dependency versioning.

### Implementation
Kiro implemented the application from the approved design.

### Testing
Kiro generated and executed the test suite, resulting in
28 passing tests covering the core scheduling, workload,
persistence, and collision-detection logic.

### Review & Refinement
Kiro performed code/design review and addressed identified
HIGH and MEDIUM findings before final validation.

### DevOps
Kiro helped create the Docker configuration and GitHub Actions
CI workflow.