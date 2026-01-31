# Life OS

**A personal control plane that reasons across your life and safely executes decisions.**

> "Talk once. Decide once. Your system updates itself correctly."

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User (conversational intent)                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  Orchestrator          Intent → Retrieve → Deliberate → Plan     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼───────┐    ┌──────────▼──────────┐   ┌───────▼───────┐
│  LifeGraph    │    │  Multi-Agent Council │   │  Connectors   │
│  (canonical   │    │  Planner · Skeptic   │   │  Gmail, Cal,  │
│   entities &  │    │  Optimizer · Privacy │   │  Notion, etc  │
│   relations)  │    └─────────────────────┘   └───────────────┘
└───────────────┘
```

## Quick Start

### 1. Install

```bash
# Create venv
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# Install
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env: set GEMINI_API_KEY (required for orchestration)
```

### 3. Run API

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Use

```bash
# State intent
curl -X POST http://localhost:8000/intent -H "Content-Type: application/json" -d "{\"intent\": \"Schedule a meeting with Alex next Tuesday at 2pm\"}"

# Approve and execute (after reviewing diffs)
curl -X POST http://localhost:8000/approve -H "Content-Type: application/json" -d "{\"diffs\": [...]}"
```

## Project Layout

```
life-os/
├── config/           # Settings from .env
├── src/
│   ├── lifegraph/    # Canonical schema, graph, storage
│   ├── retrieval/    # Hybrid (vector + graph) retrieval
│   ├── connectors/   # MCP write-back agents (stubs)
│   └── orchestration/# API, flows, multi-agent council
├── .env.example
├── pyproject.toml
└── README.md
```

## LifeGraph Schema

**Entities:** Person, Project, Goal, Task, Event, Decision

**Relations:** `depends_on`, `scheduled_for`, `relates_to`, `blocks`, `assigned_to`, `part_of`

## Safety

- **Append-only by default** — overwrites require explicit approval
- **Two-phase commit** — diff preview before execution
- **Gemini never executes writes** — only proposes plans

## License

MIT
