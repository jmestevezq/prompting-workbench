Prompt Engineering Workbench
============================

A local-first web app for iterating on agent prompts, autoraters, and
transaction classification prompts. FastAPI backend + React/TypeScript frontend.


Prerequisites
-------------
- Node.js >= 20  (recommended: 22 LTS)
- pnpm >= 9      (the repo pins 9.15.9 via corepack)
- Python >= 3.11 (tested with 3.14)
- Git


Quick Start (New Machine)
-------------------------

  # 1. Clone
  git clone <repo-url> prompt-workbench
  cd prompt-workbench

  # 2. Enable corepack (ships with Node, pins pnpm version)
  corepack enable

  # 3. Install Node dependencies (root + frontend)
  pnpm install

  # 4. Create Python venv and install backend dependencies
  pnpm nx run backend:install

  # 5. Configure environment variables
  cp .env.example .env
  # Edit .env and add your GEMINI_API_KEY
  # Get one at https://aistudio.google.com/apikey

  # 6. Start both servers
  pnpm dev
  # Frontend: http://localhost:5173
  # Backend:  http://localhost:8000

The SQLite database (workbench.db) is created automatically on first backend start.


Detailed Setup by Platform
--------------------------

### macOS (Homebrew)

  brew install node@22 python@3.14
  corepack enable
  # Then follow Quick Start steps 1-6

### Ubuntu / Debian

  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt install -y nodejs python3 python3-venv python3-pip
  corepack enable
  # Then follow Quick Start steps 1-6

### Windows (WSL2 recommended)

  # Inside WSL2 Ubuntu, follow the Ubuntu steps above.
  # Native Windows: use nvm-windows for Node and python.org installer for Python.


Daily Development
-----------------

  pnpm dev                           # start frontend + backend together
  pnpm nx run frontend:dev           # frontend only  (:5173)
  pnpm nx run backend:dev            # backend only   (:8000)


Testing
-------

  pnpm test                          # all tests (frontend + backend)
  pnpm nx run frontend:test          # Vitest  (frontend)
  pnpm nx run backend:test           # Pytest  (backend)

Always run `pnpm test` before committing. Never commit broken tests.


Building
--------

  pnpm build                         # production build (frontend -> frontend/dist/)


Linting
-------

  pnpm lint                          # ESLint (frontend)


Manual Backend Commands
-----------------------

If you prefer running Python commands directly:

  cd backend
  source .venv/bin/activate          # activate the virtual environment
  uvicorn app.main:app --reload --port 8000
  python -m pytest tests/ -v
  deactivate                         # when done


Adding Python Dependencies
--------------------------

  cd backend
  source .venv/bin/activate
  pip install <package>
  pip freeze > requirements.txt
  deactivate


Useful Nx Commands
------------------

  pnpm nx show projects              # list all projects
  pnpm nx show project frontend      # show frontend targets
  pnpm nx show project backend       # show backend targets
  pnpm nx graph                      # open project graph in browser


Environment Variables (.env)
----------------------------

  GEMINI_API_KEY          (required) Your Google Gemini API key
  DB_PATH                 SQLite path         (default: ./workbench.db)
  DEFAULT_MODEL           Gemini model name   (default: gemini-2.5-pro)
  BATCH_CONCURRENCY       Parallel eval runs  (default: 5)
  CODE_EXECUTION_TIMEOUT  Sandbox timeout sec (default: 10)


Project Structure
-----------------

  prompt-workbench/
    .env.example          Environment template
    CLAUDE.md             Claude Code agent instructions
    GEMINI.md             Gemini CLI agent instructions
    nx.json               Nx workspace config
    package.json          Root scripts + Nx devDeps
    pnpm-workspace.yaml   pnpm monorepo config
    docs/                 Specs, component docs, build progress
    backend/              Python FastAPI app
      app/                Application code (routers, services, schemas)
      agents/             Agent definition files (JSON)
      tests/              Pytest tests
      requirements.txt    Python dependencies
      project.json        Nx project config for backend
    frontend/             React + Vite + TypeScript app
      src/                Application code (pages, components, hooks, store)
      vite.config.ts      Vite + Vitest config + API proxy


For Coding Agents (Claude Code, Gemini CLI)
--------------------------------------------

  1. Read CLAUDE.md (or GEMINI.md) first
  2. Read docs/AGENT_RULES.md for conventions and testing policy
  3. Read docs/workbench-spec.md for the full product spec
  4. Read docs/BUILD_PROGRESS.md for current status
  5. Check `git log --oneline -20` for recent work

Key conventions:
  - All IDs are uuid4 strings
  - JSON fields in SQLite stored as TEXT
  - Gemini automatic_function_calling is DISABLED
  - CORS allows localhost:5173
  - Every code change must include tests
  - Update docs/ when adding or changing features


Troubleshooting
---------------

"pnpm: command not found"
  -> Run `corepack enable` (requires Node >= 16.13)
  -> Or install globally: npm install -g pnpm@9

"python3: command not found" / wrong version
  -> macOS: brew install python@3.14
  -> Ubuntu: sudo apt install python3 python3-venv
  -> Check: python3 --version

Backend fails to start with import errors
  -> Make sure venv is set up: pnpm nx run backend:install
  -> Or manually: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

"GEMINI_API_KEY not set" or API errors
  -> Copy .env.example to .env and add your key
  -> Get a key at https://aistudio.google.com/apikey

Frontend proxy errors (CORS / 502)
  -> Make sure backend is running on port 8000
  -> Run `pnpm dev` to start both together

Tests fail on fresh clone
  -> Run `pnpm install` and `pnpm nx run backend:install` first
  -> Make sure .env exists (even without API key, unit tests should pass)
