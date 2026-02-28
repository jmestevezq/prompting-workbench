# CLAUDE.md

## Project: Prompt Engineering Workbench

Full design spec: docs/workbench-spec.md — READ THIS FIRST if you lose context.
Build instructions: docs/setup-guide.md

## Tech Stack
- Backend: FastAPI + aiosqlite + google-genai (Python, venv in backend/.venv)
- Frontend: React + TypeScript + Vite + Tailwind + Monaco Editor + Zustand
- DB: SQLite at ./workbench.db
- Model: gemini-2.5-pro via google-genai SDK

## Key Commands
- Backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
- Frontend: cd frontend && npm run dev
- Both: make dev

## Conventions
- All IDs: uuid4 strings
- JSON fields in SQLite: stored as TEXT
- Gemini: automatic_function_calling DISABLED, we control the loop
- CORS: allow localhost:5173
- No Docker, no external services, no auth

## Context Management — MANDATORY
- After completing each phase (Phase 1 through Phase 7), STOP and do the following:
  1. Git commit all work with message: "Phase N complete: [description]"
  2. Write a brief status summary to `docs/BUILD_PROGRESS.md` listing: what's done, what's next, any TODOs or blockers
  3. Run `/compact` to clear context
  4. After compaction, re-read `CLAUDE.md`, `docs/workbench-spec.md`, and `docs/BUILD_PROGRESS.md` before continuing
- If at any point you feel context is getting large or you're losing track of the plan, do the same: commit, update BUILD_PROGRESS.md, run /compact, re-read files.
- NEVER continue to a new phase without committing the previous one.

## Resuming After Interruption
If starting a new session:
1. Read this file (CLAUDE.md)
2. Read docs/workbench-spec.md
3. Read docs/BUILD_PROGRESS.md
4. Check git log --oneline -20
5. Continue from where the last session left off

