# Life OS: Project Audit & Development Plan

## Project Audit (Current Status)

The "Life OS" project is currently in a functional MVP state with a solid core architecture that aligns well with the provided PRD.

### 1. Core Architecture
- [x] **Connector Layer**: Implemented for Gmail, Calendar, Notion, and Obsidian. Support for mock mode with realistic seeded data is fully functional.
- [x] **Unified Canonical Model**: The "LifeGraph" domain model (`src/lifegraph/schema.py`) includes entities like Person, Project, Goal, Task, Event, Decision, Note, and Communication.
- [x] **Retrieval Layer**: A ranking module exists (`src/retrieval/context_assembler.py`) that uses keyword overlap, recency, and importance to gather context.
- [x] **Multi-Agent Council**: Implementation exists in `AgentCouncil`. It uses Gemini to parse intent, generate multiple plans, and score them.
- [x] **Orchestrator**: The central pipeline (`src/orchestration/run_life_request.py`) handles the full flow from intent to tool operation previews.

### 2. Frontend
- [x] **Polished UI**: Built with Next.js 14, Tailwind CSS, and shadcn/ui.
- [x] **Core Panels**: 
    - Request/Chat panel
    - Context drawer with ranked items
    - Candidate plans with pro/con summaries
    - Recommended plan highlighting
    - Detailed Diff Preview for approval-gated writes
    - Live Audit Log showing execution history

### 3. Tech Stack & Principles
- [x] **Human-in-the-loop**: All writes require explicit user approval.
- [x] **Append-only by default**: Connectors prefer creating/appending over overwriting.
- [x] **Auditability**: Every action is logged in a local SQLite database and visible in the UI.
- [x] **Mock Mode**: Excellent "reset" and seeded data support for demo purposes.

---

## Gaps & Next Steps

While the foundation is strong, the following steps are needed to reach full "Startup MVP" quality and fulfill all PRD requirements.

### Phase 1: Agent & Reasoning Refinement (High Priority)
1. [x] **True Multi-Agent Deliberation**: 
    - *Current State*: A single Gemini call handles the "Council Score".
    - *Goal*: Split the council into separate agent calls (Skeptic, Optimizer, Privacy) as requested. This allows for deeper reasoning and more "deliberate" feedback in the UI.
2. [x] **Improved Planner Diversity**: 
    - Ensure the 3 candidate plans are programmatically or prompt-forced to be distinct (e.g., "Aggressive/Deadline-focused" vs. "Balanced" vs. "Conservative/Recovery").

### Phase 2: Functional Completeness (Medium Priority)
1. **Reversibility (Undo)**: 
    - [x] Implement a "Rollback" mechanism. Since the system is "append-only by default," this would involve deleting the newly created entities or reverting the specific append.
2. **Enhanced Diff Preview**: 
    - [x] Move beyond JSON payload previews. Show a "Visual Diff" (e.g., "Calendar: Add 'Team Lunch' at 12pm") that is more legible for non-technical users.
3. **Advanced Retrieval**:
    - [x] Implement a simple vector-based retrieval if the dataset grows, or improve the heuristic to better handle "importance" vs "recency" tradeoffs. (Dynamic heuristic weighting implemented).

### Phase 3: Polish & UX (Stretch Goals)
1. [x] **LifeGraph Visualization**: 
    - Add a "Graph View" component to show how a Task relates to a Goal or an Email thread.
2. **Real API Integration**: 
    - Add optional OAuth/API Key support for users who want to connect real accounts (keeping mock mode as the default for demos).
3. [x] **Source Confidence Scores**: 
    - Show "why this source was used" in the context drawer.

---

## Next Action Plan (Immediate)

1. [x] **[Backend]** Refactor `AgentCouncil` to support sequential or parallel deliberation from separate agent prompts (Skeptic, Optimizer, Privacy).
2. [x] **[Backend]** Implement a `POST /rollback` endpoint that can undo the last N actions from the audit log.
3. [x] **[Frontend]** Add "Undo" button to the Audit Log UI.
4. [x] **[Backend]** Enhance `generate_diffs.py` to produce more descriptive `preview` strings for the UI.

## Phase 1 & 2 Refinement (Next Tasks)

1. [x] **[Backend]** Parallelize `AgentCouncil` deliberation and planner diversity calls.
2. [x] **[Frontend]** Implement "Visual Diff" component (replaces raw JSON with pretty summary).
3. [x] **[Backend]** Improved Planner Diversity: Ensure 3 distinct strategy calls (Balanced, Aggressive, Conservative).

