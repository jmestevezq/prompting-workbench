import json
from uuid import uuid4
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas.fixture import FixtureCreate, FixtureUpdate, FixtureResponse

router = APIRouter(prefix="/api/fixtures", tags=["fixtures"])


@router.get("", response_model=list[FixtureResponse])
async def list_fixtures():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM fixtures ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_fixture(row) for row in rows]
    finally:
        await db.close()


@router.post("", response_model=FixtureResponse, status_code=201)
async def create_fixture(fixture: FixtureCreate):
    db = await get_db()
    try:
        fixture_id = str(uuid4())
        await db.execute(
            "INSERT INTO fixtures (id, name, type, data) VALUES (?, ?, ?, ?)",
            (fixture_id, fixture.name, fixture.type, json.dumps(fixture.data)),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM fixtures WHERE id = ?", (fixture_id,))
        row = await cursor.fetchone()
        return _row_to_fixture(row)
    finally:
        await db.close()


@router.get("/{fixture_id}", response_model=FixtureResponse)
async def get_fixture(fixture_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM fixtures WHERE id = ?", (fixture_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fixture not found")
        return _row_to_fixture(row)
    finally:
        await db.close()


@router.put("/{fixture_id}", response_model=FixtureResponse)
async def update_fixture(fixture_id: str, update: FixtureUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM fixtures WHERE id = ?", (fixture_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Fixture not found")

        fields = []
        values = []
        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if update.type is not None:
            fields.append("type = ?")
            values.append(update.type)
        if update.data is not None:
            fields.append("data = ?")
            values.append(json.dumps(update.data))

        if fields:
            values.append(fixture_id)
            await db.execute(f"UPDATE fixtures SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()

        cursor = await db.execute("SELECT * FROM fixtures WHERE id = ?", (fixture_id,))
        row = await cursor.fetchone()
        return _row_to_fixture(row)
    finally:
        await db.close()


@router.delete("/{fixture_id}", status_code=204)
async def delete_fixture(fixture_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM fixtures WHERE id = ?", (fixture_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Fixture not found")
        await db.execute("DELETE FROM fixtures WHERE id = ?", (fixture_id,))
        await db.commit()
    finally:
        await db.close()


def _row_to_fixture(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "data": json.loads(row["data"]) if row["data"] else None,
        "created_at": row["created_at"] or "",
    }
