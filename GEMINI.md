# GEMINI.md — Gemini CLI Agent Rules

## Project: Prompt Engineering Workbench

Shared project rules: @docs/AGENT_RULES.md — READ THIS along with the files below.
Full design spec: @docs/workbench-spec.md — READ THIS FIRST if you lose context.

## Tech Stack
- Backend: FastAPI + aiosqlite + google-genai (Python, venv in backend/.venv)
- Frontend: React + TypeScript + Vite + Tailwind + Monaco Editor + Zustand
- DB: SQLite at ./workbench.db
- Model: gemini-2.5-pro via google-genai SDK

## Key Commands
- Both (dev): pnpm dev
- Frontend only: pnpm nx run frontend:dev
- Backend only: pnpm nx run backend:dev
- All tests: pnpm test
- Frontend tests: pnpm nx run frontend:test
- Backend tests: pnpm nx run backend:test
- Build: pnpm build
- Install backend deps: pnpm nx run backend:install

## Conventions
- All IDs: uuid4 strings
- JSON fields in SQLite: stored as TEXT
- Gemini: automatic_function_calling DISABLED, we control the loop
- CORS: allow localhost:5173
- No Docker, no external services, no auth

## Testing — MANDATORY
Every code change must include tests. See `docs/AGENT_RULES.md` for the full testing policy.
Always run `pnpm test` before committing. Never commit broken tests.

## Documentation — MANDATORY
Update `docs/BACKEND_COMPONENTS.md`, `docs/FRONTEND_COMPONENTS.md`, `docs/SYSTEM_OVERVIEW.md`,
and `docs/BUILD_PROGRESS.md` when adding or changing features.

## Context Management — MANDATORY (Gemini CLI specific)
- After completing each significant phase of work, STOP and do the following:
  1. Git commit all work with a clear message
  2. Write a brief status summary to `docs/BUILD_PROGRESS.md`
  3. Run `/memory refresh` to reload context files
  4. Re-read `GEMINI.md`, `docs/AGENT_RULES.md`, `docs/workbench-spec.md`,
     and `docs/BUILD_PROGRESS.md` before continuing
- If at any point context is getting large or you're losing track, do the same: commit, update BUILD_PROGRESS.md, run `/memory refresh`, re-read files.
- Use `/memory show` to inspect what context is currently loaded.
- NEVER continue to a new phase without committing the previous one.

## Resuming After Interruption
If starting a new session:
1. Read this file (GEMINI.md)
2. Read docs/AGENT_RULES.md
3. Read docs/workbench-spec.md
4. Read docs/BUILD_PROGRESS.md
5. Check git log --oneline -20
6. Continue from where the last session left off
