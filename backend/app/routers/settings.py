from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    has_api_key: bool
    default_model: str
    batch_concurrency: int
    code_execution_timeout: int


class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    default_model: Optional[str] = None
    batch_concurrency: Optional[int] = None
    code_execution_timeout: Optional[int] = None


@router.get("", response_model=SettingsResponse)
async def get_settings():
    return {
        "has_api_key": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-api-key-here"),
        "default_model": settings.DEFAULT_MODEL,
        "batch_concurrency": settings.BATCH_CONCURRENCY,
        "code_execution_timeout": settings.CODE_EXECUTION_TIMEOUT,
    }


@router.put("", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdate):
    if update.gemini_api_key is not None:
        settings.GEMINI_API_KEY = update.gemini_api_key
    if update.default_model is not None:
        settings.DEFAULT_MODEL = update.default_model
    if update.batch_concurrency is not None:
        settings.BATCH_CONCURRENCY = update.batch_concurrency
    if update.code_execution_timeout is not None:
        settings.CODE_EXECUTION_TIMEOUT = update.code_execution_timeout

    return {
        "has_api_key": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-api-key-here"),
        "default_model": settings.DEFAULT_MODEL,
        "batch_concurrency": settings.BATCH_CONCURRENCY,
        "code_execution_timeout": settings.CODE_EXECUTION_TIMEOUT,
    }
