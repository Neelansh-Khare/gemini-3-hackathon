# Life OS

**A personal control plane that reasons across your life and safely executes decisions.**

> "Talk once. Decide once. Your system updates itself correctly."

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Next.js workspace (chat, context, plans, diffs)     │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST
┌───────────────────────────────▼─────────────────────────────────┐
│  FastAPI — Intent → ContextPacket → Council → ToolOperation[]    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼───────┐    ┌──────────▼──────────┐   ┌───────▼───────┐
│  LifeGraph    │    │  Multi-Agent Council │   │  Connectors   │
│  (canonical   │    │  Planner · combined  │   │  Gmail, Cal,  │
│   model)      │    │  Skeptic/Opt/Privacy │   │  Notion, Obs  │
└───────────────┘    └─────────────────────┘   │  (mock + seed)│
                                               └───────────────┘
```

- **Connectors:** `gmail`, `calendar`, `notion`, `obsidian` — mock implementations with seeded demo data; read + approval-gated writes.
- **Retrieval:** `context_assembler` ranks items from all four sources (relevance, importance, recency).
- **Council:** Multi-plan planner + combined scoring; without `GEMINI_API_KEY`, deterministic seeded plans.
- **Executor:** Produces `tool_operations` (preview); writes run only after `POST /approve`.
- **Audit:** SQLite append-only log at `data/audit.db`.

## Quick Start

### Python (always use a venv)

Do **not** `pip install -e .` into your global Python. If you did, run:

```powershell
.\scripts\clean_global_life_os.ps1
```

Install into the project venv:

```powershell
.\scripts\install.ps1
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
chmod +x scripts/install.sh
./scripts/install.sh
source .venv/bin/activate
```

### Configure

```bash
cp .env.example .env
# Optional: GEMINI_API_KEY — enables live Gemini planner/executor; otherwise mock plans apply.
```

### Run API

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Run frontend (Next.js 14 + Tailwind + zod + Radix/shadcn-style UI)

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The UI drives the **PRD demo flow**: request → context drawer → candidate plans → recommended plan → diff preview → approve / reject / execute selected → audit log.

### API examples

```bash
curl -X POST http://localhost:8000/intent -H "Content-Type: application/json" -d "{\"intent\": \"Plan my next week around meetings and follow-ups\"}"

curl -X POST http://localhost:8000/approve -H "Content-Type: application/json" -d "{\"tool_operations\": [...]}"
curl http://localhost:8000/audit
```

## Project layout

```
├── config/              # pydantic-settings
├── src/
│   ├── domain/          # PRD types (ContextPacket, CandidatePlan, ToolOperation, AuditEntry, …)
│   ├── lifegraph/       # Entities, graph, SQLite storage, normalize
│   ├── connectors/      # gmail, calendar, notion, obsidian (+ seed data)
│   ├── retrieval/       # context_assembler
│   ├── diff/            # tool op helpers
│   ├── audit/           # audit log
│   └── orchestration/   # council, run_life_request, FastAPI
├── frontend/            # Next.js 14 app
├── scripts/             # install.ps1, clean_global_life_os.ps1, …
└── pyproject.toml
```

## LifeGraph schema

**Entities:** Person, Project, Goal, Task, Event, Decision, Note, Communication

**Relations:** `depends_on`, `scheduled_for`, `relates_to`, `blocks`, `assigned_to`, `part_of`, `owned_by`, `mentioned_in`

## Safety

- **Human-in-the-loop** — no writes without `POST /approve`.
- **Append-only bias** — connector mocks prefer append; Gmail: **drafts only**, no send.
- **Gemini does not execute writes** — only proposes plans / tool ops.
- **Mock mode** — works without `GEMINI_API_KEY` using seeded candidate plans.

## License

MIT
