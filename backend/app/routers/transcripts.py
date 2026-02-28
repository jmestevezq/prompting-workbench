import json
from uuid import uuid4
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas.transcript import (
    TranscriptCreate, TranscriptUpdate, TranscriptResponse, TranscriptImport,
)

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


@router.get("", response_model=list[TranscriptResponse])
async def list_transcripts(tag: str | None = None, source: str | None = None):
    db = await get_db()
    try:
        query = "SELECT * FROM transcripts"
        params = []
        conditions = []

        if source:
            conditions.append("source = ?")
            params.append(source)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        results = [_row_to_transcript(row) for row in rows]

        # Filter by tag in Python since tags is JSON
        if tag:
            results = [r for r in results if r.get("tags") and tag in r["tags"]]

        return results
    finally:
        await db.close()


@router.post("", response_model=TranscriptResponse, status_code=201)
async def create_transcript(transcript: TranscriptCreate):
    db = await get_db()
    try:
        transcript_id = str(uuid4())
        await db.execute(
            "INSERT INTO transcripts (id, name, content, parsed_turns, labels, source, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                transcript_id,
                transcript.name,
                transcript.content,
                json.dumps(transcript.parsed_turns) if transcript.parsed_turns else None,
                json.dumps(transcript.labels),
                transcript.source,
                json.dumps(transcript.tags),
            ),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,))
        row = await cursor.fetchone()
        return _row_to_transcript(row)
    finally:
        await db.close()


@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(transcript_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transcript not found")
        return _row_to_transcript(row)
    finally:
        await db.close()


@router.put("/{transcript_id}", response_model=TranscriptResponse)
async def update_transcript(transcript_id: str, update: TranscriptUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Transcript not found")

        fields = []
        values = []
        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if update.content is not None:
            fields.append("content = ?")
            values.append(update.content)
        if update.parsed_turns is not None:
            fields.append("parsed_turns = ?")
            values.append(json.dumps(update.parsed_turns))
        if update.labels is not None:
            fields.append("labels = ?")
            values.append(json.dumps(update.labels))
        if update.tags is not None:
            fields.append("tags = ?")
            values.append(json.dumps(update.tags))

        if fields:
            values.append(transcript_id)
            await db.execute(f"UPDATE transcripts SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()

        cursor = await db.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,))
        row = await cursor.fetchone()
        return _row_to_transcript(row)
    finally:
        await db.close()


@router.delete("/{transcript_id}", status_code=204)
async def delete_transcript(transcript_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM transcripts WHERE id = ?", (transcript_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Transcript not found")
        await db.execute("DELETE FROM transcripts WHERE id = ?", (transcript_id,))
        await db.commit()
    finally:
        await db.close()


@router.post("/import", response_model=list[TranscriptResponse], status_code=201)
async def import_transcripts(data: TranscriptImport):
    db = await get_db()
    try:
        results = []
        for transcript in data.transcripts:
            transcript_id = str(uuid4())
            await db.execute(
                "INSERT INTO transcripts (id, name, content, parsed_turns, labels, source, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    transcript_id,
                    transcript.name,
                    transcript.content,
                    json.dumps(transcript.parsed_turns) if transcript.parsed_turns else None,
                    json.dumps(transcript.labels),
                    transcript.source or "imported",
                    json.dumps(transcript.tags),
                ),
            )
            cursor = await db.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,))
            row = await cursor.fetchone()
            results.append(_row_to_transcript(row))
        await db.commit()
        return results
    finally:
        await db.close()


def _row_to_transcript(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "content": row["content"],
        "parsed_turns": json.loads(row["parsed_turns"]) if row["parsed_turns"] else None,
        "labels": json.loads(row["labels"]) if row["labels"] else {},
        "source": row["source"],
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "created_at": row["created_at"] or "",
    }
