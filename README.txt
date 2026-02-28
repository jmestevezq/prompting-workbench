Prompt Engineering Workbench
============================

Prerequisites
-------------
- Node.js >= 20
- pnpm >= 9
- Python >= 3.11

First-Time Setup
----------------
1. Clone the repo
2. pnpm install                        # installs root + frontend deps
3. pnpm nx run backend:install         # creates venv + installs Python deps
4. cp .env.example .env                # add your GEMINI_API_KEY

Daily Development
-----------------
pnpm dev                               # starts frontend (:5173) + backend (:8000)
pnpm nx run frontend:dev               # frontend only
pnpm nx run backend:dev                # backend only

Testing
-------
pnpm test                              # all tests (frontend + backend)
pnpm nx run frontend:test              # Vitest (frontend)
pnpm nx run backend:test               # Pytest (backend)

Building
--------
pnpm build                             # production build (frontend)

Linting
-------
pnpm lint                              # ESLint (frontend)

Useful Nx Commands
------------------
pnpm nx show projects                  # list all projects
pnpm nx show project frontend          # show frontend targets
pnpm nx show project backend           # show backend targets
pnpm nx graph                          # open project graph in browser

Project Structure
-----------------
prompt-workbench/
  backend/           Python FastAPI app
    app/             application code
    tests/           Pytest tests
    project.json     Nx project config
  frontend/          React + Vite app
    src/             application code
    vite.config.ts   Vite + Vitest config
  nx.json            Nx workspace config
  package.json       root scripts + Nx devDeps
  pnpm-workspace.yaml
