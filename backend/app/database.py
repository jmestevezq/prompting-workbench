import json
from pathlib import Path
from uuid import uuid4

import aiosqlite

from app.config import settings

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
    tool_definitions JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id),
    system_prompt TEXT NOT NULL,
    tool_definitions JSON,
    version_hash TEXT NOT NULL,
    label TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fixtures (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id),
    fixture_ids JSON,
    prompt_version_id TEXT REFERENCES prompt_versions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS turns (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    turn_index INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    raw_request JSON,
    raw_response JSON,
    tool_calls JSON,
    tool_responses JSON,
    token_usage JSON,
    parent_turn_id TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    name TEXT,
    content TEXT NOT NULL,
    parsed_turns JSON,
    labels JSON NOT NULL,
    source TEXT DEFAULT 'manual',
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS autoraters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
    output_schema JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    autorater_id TEXT REFERENCES autoraters(id),
    prompt_version_hash TEXT,
    transcript_ids JSON NOT NULL,
    eval_tags JSON,
    status TEXT DEFAULT 'pending',
    metrics JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eval_results (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES eval_runs(id),
    transcript_id TEXT REFERENCES transcripts(id),
    predicted_labels JSON NOT NULL,
    ground_truth_labels JSON NOT NULL,
    match BOOLEAN,
    raw_response JSON,
    token_usage JSON
);

CREATE TABLE IF NOT EXISTS golden_transactions (
    id TEXT PRIMARY KEY,
    set_name TEXT NOT NULL,
    input_transactions JSON NOT NULL,
    reference_transactions JSON,
    expected_output JSON NOT NULL,
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classification_prompts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classification_runs (
    id TEXT PRIMARY KEY,
    prompt_id TEXT REFERENCES classification_prompts(id),
    prompt_version_hash TEXT,
    golden_set_name TEXT,
    status TEXT DEFAULT 'pending',
    metrics JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classification_results (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES classification_runs(id),
    golden_id TEXT REFERENCES golden_transactions(id),
    predicted_output JSON NOT NULL,
    match_details JSON,
    raw_response JSON,
    token_usage JSON
);

CREATE TABLE IF NOT EXISTS agent_versions (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id),
    version_label TEXT NOT NULL,
    source TEXT DEFAULT 'file',
    raw_template TEXT,
    variables JSON,
    variable_definitions JSON,
    system_prompt TEXT NOT NULL,
    tool_details JSON,
    widget_details JSON,
    tools JSON,
    is_base INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript(SCHEMA_SQL)
        await db.commit()

        # Migrate: add eval_tags to eval_runs if missing (replaces pass_tags/fail_tags)
        cursor = await db.execute("PRAGMA table_info(eval_runs)")
        cols = {row["name"] for row in await cursor.fetchall()}
        if "eval_tags" not in cols:
            await db.execute("ALTER TABLE eval_runs ADD COLUMN eval_tags JSON")
            await db.commit()

        # Migrate: add agent_folder and active_version_id to agents if missing
        cursor = await db.execute("PRAGMA table_info(agents)")
        agent_cols = {row["name"] for row in await cursor.fetchall()}
        if "agent_folder" not in agent_cols:
            await db.execute("ALTER TABLE agents ADD COLUMN agent_folder TEXT")
            await db.commit()
        if "active_version_id" not in agent_cols:
            await db.execute("ALTER TABLE agents ADD COLUMN active_version_id TEXT REFERENCES agent_versions(id)")
            await db.commit()

        # Auto-load seed data if DB is empty
        cursor = await db.execute("SELECT COUNT(*) FROM agents")
        count = (await cursor.fetchone())[0]
        if count == 0:
            await _load_seed_data(db)
    finally:
        await db.close()


async def _load_seed_data(db: aiosqlite.Connection):
    """Load seed data from seed_data/seed.json if available."""
    seed_path = Path(__file__).resolve().parent.parent / "seed_data" / "seed.json"
    if not seed_path.exists():
        return

    with open(seed_path) as f:
        seed = json.load(f)

    for agent in seed.get("agents", []):
        await db.execute(
            "INSERT INTO agents (id, name, system_prompt, model, tool_definitions) VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), agent["name"], agent["system_prompt"], agent["model"], json.dumps(agent["tool_definitions"])),
        )

    for fixture in seed.get("fixtures", []):
        await db.execute(
            "INSERT INTO fixtures (id, name, type, data) VALUES (?, ?, ?, ?)",
            (str(uuid4()), fixture["name"], fixture["type"], json.dumps(fixture["data"])),
        )

    for transcript in seed.get("transcripts", []):
        await db.execute(
            "INSERT INTO transcripts (id, name, content, labels, source, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()), transcript["name"], transcript["content"],
                json.dumps(transcript["labels"]), transcript.get("source", "manual"),
                json.dumps(transcript.get("tags", [])),
            ),
        )

    await db.commit()
