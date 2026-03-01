# Agent Rules — Prompt Engineering Workbench

> This file contains shared rules for all AI coding agents (Claude Code, Gemini CLI, etc.).
> Agent-specific config files (CLAUDE.md, GEMINI.md) reference this file and add tool-specific instructions.

## Project

Full design spec: docs/workbench-spec.md — READ THIS FIRST if you lose context.

## Tech Stack

- Backend: FastAPI + aiosqlite + google-genai (Python, venv in backend/.venv)
- Frontend: React + TypeScript + Vite + Tailwind + Monaco Editor + Zustand
- DB: SQLite at ./workbench.db
- Model: gemini-2.5-pro via google-genai SDK

## Key Commands

| Task | Command |
|---|---|
| Dev (both) | `pnpm dev` |
| Frontend only | `pnpm nx run frontend:dev` |
| Backend only | `pnpm nx run backend:dev` |
| All tests | `pnpm test` |
| Frontend tests | `pnpm nx run frontend:test` |
| Backend tests | `pnpm nx run backend:test` |
| Build | `pnpm build` |
| Install backend deps | `pnpm nx run backend:install` |

## Conventions

- All IDs: uuid4 strings
- JSON fields in SQLite: stored as TEXT
- Gemini: automatic_function_calling DISABLED, we control the loop
- CORS: allow localhost:5173
- No Docker, no external services, no auth

## Testing — MANDATORY

**Every code change must include tests.** Do not consider a feature or fix complete until tests are written and passing.

### Rules

1. **New backend service or function** → add unit tests in `backend/tests/test_<module>.py`
2. **New backend API endpoint** → add integration tests covering success, 404, and validation failure cases
3. **New frontend component** → add a `.test.tsx` file covering rendering, props, and user interactions
4. **New frontend page** → add tests for initial render, data loading (mocked), and key interactions
5. **Bug fix** → add a regression test that would have caught the bug before the fix

### Test Frameworks

- Backend: pytest + httpx (via FastAPI TestClient) in `backend/tests/`
- Frontend: Vitest + @testing-library/react in co-located `.test.tsx` files

### Running Tests Before Committing

Always run the full test suite before committing:
```bash
pnpm test
```

If tests fail, fix them before committing. Never commit broken tests.

## Documentation — MANDATORY

When adding or changing features, update the relevant docs:

- `docs/BACKEND_COMPONENTS.md` — for backend service/router changes
- `docs/FRONTEND_COMPONENTS.md` — for new components or pages
- `docs/SYSTEM_OVERVIEW.md` — for architecture changes
- `docs/BUILD_PROGRESS.md` — after completing significant work

## Resuming After Interruption

If starting a new session:
1. Read CLAUDE.md (or GEMINI.md)
2. Read `docs/AGENT_RULES.md` (this file)
3. Read `docs/workbench-spec.md`
4. Read `docs/BUILD_PROGRESS.md`
5. Check `git log --oneline -20`
6. Continue from where the last session left off
