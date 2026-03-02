from pydantic import BaseModel, Field
from typing import Optional, Any


class FixtureCreate(BaseModel):
    name: str
    type: str  # 'user_profile', 'transactions', 'reference_transactions'
    data: Any


class FixtureUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    data: Optional[Any] = None


class FixtureResponse(BaseModel):
    id: str
    name: str
    type: str
    data: Any
    created_at: str


class GenerateTransactionsRequest(BaseModel):
    prompt: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    profile_data: Optional[Any] = None


class GenerateProfileResponse(BaseModel):
    name: str
    data: Any


class GenerateTransactionsResponse(BaseModel):
    transactions: Any  # list of transaction dicts
    count: int
