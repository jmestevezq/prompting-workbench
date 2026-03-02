# AI-Powered Fixture Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Gemini-powered generation of user profiles and transactions so users can quickly populate test data without manually writing JSON.

**Architecture:** Two new backend endpoints (`POST /api/fixtures/generate-profile`, `POST /api/fixtures/generate-transactions`) call Gemini with structured prompts including the exact data schema. A new `backend/app/services/fixture_generator.py` service handles prompt construction, Gemini calls, and response validation. The frontend `UserProfiles.tsx` page gains auto-generation on "New Profile" click and a "Generate Transactions" panel alongside the transactions editor.

**Tech Stack:** Existing FastAPI + google-genai backend, React + TypeScript frontend. Uses `response_mime_type: "application/json"` for structured Gemini output.

---

### Task 1: Backend — Fixture Generator Service (Profile)

**Files:**
- Create: `backend/app/services/fixture_generator.py`
- Test: `backend/tests/test_fixture_generator.py`

**Step 1: Write the failing test for profile validation**

```python
# backend/tests/test_fixture_generator.py
"""Tests for AI fixture generation service."""

import pytest
from app.services.fixture_generator import validate_profile, validate_transactions


class TestValidateProfile:
    def test_valid_profile_passes(self):
        profile = {
            "ageYears": 34,
            "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
            "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
            "creditScore": {"score": 750, "maxScore": 900},
            "bankAccounts": [{"issuerName": "HDFC Bank"}],
            "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
        }
        errors = validate_profile(profile)
        assert errors == []

    def test_missing_required_field(self):
        profile = {"ageYears": 34}
        errors = validate_profile(profile)
        assert len(errors) > 0
        assert any("location" in e for e in errors)

    def test_invalid_age_type(self):
        profile = {
            "ageYears": "thirty",
            "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
            "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
            "creditScore": {"score": 750, "maxScore": 900},
            "bankAccounts": [{"issuerName": "HDFC Bank"}],
            "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
        }
        errors = validate_profile(profile)
        assert any("ageYears" in e for e in errors)

    def test_missing_location_subfield(self):
        profile = {
            "ageYears": 34,
            "location": {"city": "Mumbai"},
            "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
            "creditScore": {"score": 750, "maxScore": 900},
            "bankAccounts": [{"issuerName": "HDFC Bank"}],
            "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
        }
        errors = validate_profile(profile)
        assert any("state" in e for e in errors)

    def test_empty_bank_accounts(self):
        profile = {
            "ageYears": 34,
            "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
            "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
            "creditScore": {"score": 750, "maxScore": 900},
            "bankAccounts": [],
            "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
        }
        errors = validate_profile(profile)
        assert any("bankAccounts" in e for e in errors)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.fixture_generator'`

**Step 3: Write the validation implementation**

```python
# backend/app/services/fixture_generator.py
"""AI-powered fixture generation using Gemini."""

import json
import re
from datetime import date, timedelta
from typing import Any

from google.genai import types

from app.config import settings
from app.services.gemini_client import get_client


def validate_profile(data: dict) -> list[str]:
    """Validate a generated user profile matches the expected schema.
    Returns a list of error strings (empty = valid).
    """
    errors = []
    required_fields = ["ageYears", "location", "monthlyIncomeRange", "creditScore", "bankAccounts", "cards"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if "ageYears" in data and not isinstance(data["ageYears"], (int, float)):
        errors.append("ageYears must be a number")

    if "location" in data:
        loc = data["location"]
        if not isinstance(loc, dict):
            errors.append("location must be an object")
        else:
            for sub in ["city", "state", "country"]:
                if sub not in loc:
                    errors.append(f"location missing field: {sub}")

    if "monthlyIncomeRange" in data:
        inc = data["monthlyIncomeRange"]
        if not isinstance(inc, dict):
            errors.append("monthlyIncomeRange must be an object")
        else:
            for sub in ["min", "max", "currency"]:
                if sub not in inc:
                    errors.append(f"monthlyIncomeRange missing field: {sub}")

    if "creditScore" in data:
        cs = data["creditScore"]
        if not isinstance(cs, dict):
            errors.append("creditScore must be an object")
        else:
            for sub in ["score", "maxScore"]:
                if sub not in cs:
                    errors.append(f"creditScore missing field: {sub}")

    if "bankAccounts" in data:
        ba = data["bankAccounts"]
        if not isinstance(ba, list) or len(ba) == 0:
            errors.append("bankAccounts must be a non-empty array")

    if "cards" in data:
        cards = data["cards"]
        if not isinstance(cards, list) or len(cards) == 0:
            errors.append("cards must be a non-empty array")

    return errors


def validate_transactions(data: list) -> list[str]:
    """Validate a list of generated transactions.
    Returns a list of error strings (empty = valid).
    """
    errors = []
    if not isinstance(data, list):
        return ["transactions must be an array"]
    if len(data) == 0:
        return ["transactions array is empty"]

    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    valid_types = {"P2M", "P2P"}
    valid_directions = {"DEBIT", "CREDIT"}

    for i, tx in enumerate(data):
        if not isinstance(tx, dict):
            errors.append(f"Transaction [{i}]: must be an object")
            continue

        required = ["transactionId", "date", "counterpartyName", "transactionType", "amount", "transactionDirection"]
        for field in required:
            if field not in tx:
                errors.append(f"Transaction [{i}]: missing {field}")

        if "date" in tx and not date_pattern.match(str(tx["date"])):
            errors.append(f"Transaction [{i}]: date must be YYYY-MM-DD format")

        if "transactionType" in tx and tx["transactionType"] not in valid_types:
            errors.append(f"Transaction [{i}]: transactionType must be P2M or P2P")

        if "transactionDirection" in tx and tx["transactionDirection"] not in valid_directions:
            errors.append(f"Transaction [{i}]: transactionDirection must be DEBIT or CREDIT")

        if "amount" in tx and not isinstance(tx["amount"], (int, float)):
            errors.append(f"Transaction [{i}]: amount must be a number")

        if tx.get("transactionType") == "P2M" and "merchantCategory" not in tx:
            errors.append(f"Transaction [{i}]: P2M transactions must have merchantCategory")

    return errors
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/fixture_generator.py backend/tests/test_fixture_generator.py
git commit -m "feat: add fixture generator validation functions"
```

---

### Task 2: Backend — Transaction Validation Tests

**Files:**
- Modify: `backend/tests/test_fixture_generator.py`

**Step 1: Add transaction validation tests**

Append to `backend/tests/test_fixture_generator.py`:

```python
class TestValidateTransactions:
    def test_valid_transactions_pass(self):
        txs = [
            {
                "transactionId": "tx001",
                "date": "2026-01-15",
                "counterpartyName": "Spencers",
                "transactionType": "P2M",
                "merchantCategory": "Groceries and Supermarkets",
                "amount": 1037.10,
                "transactionDirection": "DEBIT",
            },
            {
                "transactionId": "tx002",
                "date": "2026-01-16",
                "counterpartyName": "Amit Verma",
                "transactionType": "P2P",
                "amount": 500.00,
                "transactionDirection": "DEBIT",
            },
        ]
        errors = validate_transactions(txs)
        assert errors == []

    def test_empty_list_fails(self):
        errors = validate_transactions([])
        assert "empty" in errors[0].lower()

    def test_not_a_list_fails(self):
        errors = validate_transactions("not a list")
        assert len(errors) > 0

    def test_missing_required_field(self):
        txs = [{"transactionId": "tx001", "date": "2026-01-15"}]
        errors = validate_transactions(txs)
        assert any("counterpartyName" in e for e in errors)

    def test_invalid_date_format(self):
        txs = [{
            "transactionId": "tx001", "date": "15-01-2026",
            "counterpartyName": "Store", "transactionType": "P2M",
            "merchantCategory": "Food", "amount": 100, "transactionDirection": "DEBIT",
        }]
        errors = validate_transactions(txs)
        assert any("date" in e for e in errors)

    def test_invalid_transaction_type(self):
        txs = [{
            "transactionId": "tx001", "date": "2026-01-15",
            "counterpartyName": "Store", "transactionType": "INVALID",
            "merchantCategory": "Food", "amount": 100, "transactionDirection": "DEBIT",
        }]
        errors = validate_transactions(txs)
        assert any("transactionType" in e for e in errors)

    def test_p2m_without_category(self):
        txs = [{
            "transactionId": "tx001", "date": "2026-01-15",
            "counterpartyName": "Store", "transactionType": "P2M",
            "amount": 100, "transactionDirection": "DEBIT",
        }]
        errors = validate_transactions(txs)
        assert any("merchantCategory" in e for e in errors)

    def test_p2p_without_category_is_ok(self):
        txs = [{
            "transactionId": "tx001", "date": "2026-01-15",
            "counterpartyName": "Amit", "transactionType": "P2P",
            "amount": 500, "transactionDirection": "DEBIT",
        }]
        errors = validate_transactions(txs)
        assert errors == []
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py -v`
Expected: All 13 tests PASS

**Step 3: Commit**

```bash
git add backend/tests/test_fixture_generator.py
git commit -m "test: add transaction validation tests"
```

---

### Task 3: Backend — Gemini Generation Functions

**Files:**
- Modify: `backend/app/services/fixture_generator.py`
- Test: `backend/tests/test_fixture_generator.py`

**Step 1: Write the failing test for generate_profile (mocked Gemini)**

Add to `backend/tests/test_fixture_generator.py`:

```python
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
class TestGenerateProfile:
    async def test_returns_name_and_data(self):
        fake_profile = {
            "name": "Rajesh Kumar",
            "profile": {
                "ageYears": 34,
                "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
                "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
                "creditScore": {"score": 750, "maxScore": 900},
                "bankAccounts": [{"issuerName": "HDFC Bank"}],
                "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
            },
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_profile)

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_profile
            result = await generate_profile()

        assert result["name"] == "Rajesh Kumar"
        assert result["data"]["ageYears"] == 34
        assert "location" in result["data"]

    async def test_raises_on_invalid_response(self):
        mock_response = MagicMock()
        mock_response.text = '{"name": "Bad", "profile": {"ageYears": "not a number"}}'

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_profile
            with pytest.raises(ValueError, match="validation"):
                await generate_profile()
```

Also add `import json` at the top of the test file.

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py::TestGenerateProfile -v`
Expected: FAIL — `ImportError: cannot import name 'generate_profile'`

**Step 3: Implement generate_profile**

Add to `backend/app/services/fixture_generator.py`:

```python
PROFILE_GENERATION_PROMPT = """Generate a random, realistic Indian user profile for a financial assistant test fixture.

The profile should be for a person living in India with:
- A realistic Indian name (varied gender and regional background)
- Age between 22 and 65
- A real Indian city and state
- Monthly income range appropriate for their age and city (in INR)
- CIBIL credit score (300-900 range, maxScore always 900)
- 1-3 Indian bank accounts (HDFC, ICICI, SBI, Axis, Kotak, etc.)
- 1-2 cards from Indian issuers (credit or debit, VISA/MASTER/RUPAY)

Return ONLY valid JSON with this exact structure:
{
  "name": "<Full Name>",
  "profile": {
    "ageYears": <number>,
    "location": {"city": "<city>", "state": "<state>", "country": "India"},
    "monthlyIncomeRange": {"min": <number>, "max": <number>, "currency": "INR"},
    "creditScore": {"score": <number>, "maxScore": 900},
    "bankAccounts": [{"issuerName": "<bank>"}],
    "cards": [{"issuerName": "<bank>", "productName": "<product>", "cardType": "CREDIT|DEBIT", "cardScheme": "VISA|MASTER|RUPAY"}]
  }
}"""


async def generate_profile() -> dict:
    """Generate a random user profile using Gemini.
    Returns {"name": str, "data": dict}.
    Raises ValueError if Gemini returns invalid data.
    """
    client = get_client()
    response = await client.aio.models.generate_content(
        model=settings.DEFAULT_MODEL,
        contents=PROFILE_GENERATION_PROMPT,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=1.2,
        ),
    )

    try:
        parsed = json.loads(response.text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}")

    name = parsed.get("name", "Generated Profile")
    profile_data = parsed.get("profile", parsed)

    # If Gemini returned flat structure (no "profile" wrapper), use as-is
    if "ageYears" in parsed and "profile" not in parsed:
        profile_data = {k: v for k, v in parsed.items() if k != "name"}

    errors = validate_profile(profile_data)
    if errors:
        raise ValueError(f"Generated profile failed validation: {'; '.join(errors)}")

    return {"name": name, "data": profile_data}
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py -v`
Expected: All tests PASS (including new async ones)

**Step 5: Commit**

```bash
git add backend/app/services/fixture_generator.py backend/tests/test_fixture_generator.py
git commit -m "feat: add Gemini-powered profile generation"
```

---

### Task 4: Backend — Transaction Generation Function

**Files:**
- Modify: `backend/app/services/fixture_generator.py`
- Modify: `backend/tests/test_fixture_generator.py`

**Step 1: Write the failing test for generate_transactions (mocked Gemini)**

Add to `backend/tests/test_fixture_generator.py`:

```python
@pytest.mark.asyncio
class TestGenerateTransactions:
    async def test_returns_valid_transactions(self):
        fake_txs = [
            {
                "transactionId": "gen001",
                "date": "2026-01-15",
                "counterpartyName": "Spencers",
                "transactionType": "P2M",
                "merchantCategory": "Groceries and Supermarkets",
                "amount": 1037.10,
                "transactionDirection": "DEBIT",
            },
        ]
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_txs)

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_transactions
            result = await generate_transactions(
                prompt="Generate test transactions",
                start_date="2026-01-01",
                end_date="2026-03-02",
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["counterpartyName"] == "Spencers"

    async def test_raises_on_invalid_response(self):
        fake_txs = [{"transactionId": "gen001", "date": "bad-date"}]
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_txs)

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_transactions
            with pytest.raises(ValueError, match="validation"):
                await generate_transactions(
                    prompt="Generate test transactions",
                    start_date="2026-01-01",
                    end_date="2026-03-02",
                )

    async def test_passes_profile_context(self):
        """Verify that profile data is included in the prompt sent to Gemini."""
        fake_txs = [{
            "transactionId": "gen001", "date": "2026-01-15",
            "counterpartyName": "Store", "transactionType": "P2M",
            "merchantCategory": "Groceries", "amount": 100,
            "transactionDirection": "DEBIT",
        }]
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_txs)

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        profile = {"ageYears": 34, "location": {"city": "Mumbai"}}

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_transactions
            await generate_transactions(
                prompt="Generate transactions",
                start_date="2026-01-01",
                end_date="2026-03-02",
                profile_data=profile,
            )

        # Check that the prompt sent to Gemini includes profile info
        call_args = mock_client.aio.models.generate_content.call_args
        prompt_sent = call_args.kwargs.get("contents", call_args.args[0] if call_args.args else "")
        assert "Mumbai" in str(prompt_sent)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py::TestGenerateTransactions -v`
Expected: FAIL — `ImportError: cannot import name 'generate_transactions'`

**Step 3: Implement generate_transactions**

Add to `backend/app/services/fixture_generator.py`:

```python
TRANSACTION_GENERATION_PROMPT = """Generate realistic Indian financial transactions for a test fixture.

{user_context}

{user_prompt}

Date range: {start_date} to {end_date}

Each transaction MUST follow this exact JSON schema:
{{
  "transactionId": "<unique 20-digit string>",
  "date": "<YYYY-MM-DD within the date range>",
  "counterpartyName": "<merchant or person name>",
  "transactionType": "P2M" or "P2P",
  "merchantCategory": "<category string, REQUIRED for P2M, OMIT for P2P>",
  "amount": <positive number with up to 2 decimals, in INR>,
  "transactionDirection": "DEBIT" or "CREDIT"
}}

Rules:
- Use realistic Indian merchant names (Swiggy, Zomato, BigBasket, Flipkart, Amazon India, local shops, etc.)
- P2P transactions use Indian first names as counterpartyName and do NOT have merchantCategory
- CREDIT transactions are salary, refunds, or incoming P2P transfers
- DEBIT transactions are purchases, bills, rent, outgoing P2P
- Spread transactions evenly across the date range
- Amounts should be realistic INR values (groceries: 200-3000, restaurants: 150-2000, rent: 8000-35000, salary: 30000-200000)
- Each transactionId must be unique (20-digit numeric string)
- Common merchantCategory values: "Groceries and Supermarkets", "Restaurants", "Online Marketplaces", "Fuel & Gas Stations", "Pharmacy & Drug Stores", "Fashion and Apparel", "Utilities", "Rent", "Entertainment"

Return ONLY a valid JSON array of transactions. No wrapper object."""


async def generate_transactions(
    prompt: str,
    start_date: str,
    end_date: str,
    profile_data: dict | None = None,
) -> list[dict]:
    """Generate transactions using Gemini.
    Returns a list of transaction dicts.
    Raises ValueError if Gemini returns invalid data.
    """
    user_context = ""
    if profile_data:
        city = profile_data.get("location", {}).get("city", "")
        income = profile_data.get("monthlyIncomeRange", {})
        age = profile_data.get("ageYears", "")
        context_parts = []
        if city:
            context_parts.append(f"User lives in {city}")
        if income:
            context_parts.append(f"Monthly income: {income.get('min', 0)}-{income.get('max', 0)} INR")
        if age:
            context_parts.append(f"Age: {age}")
        user_context = "User context: " + ", ".join(context_parts)

    full_prompt = TRANSACTION_GENERATION_PROMPT.format(
        user_context=user_context,
        user_prompt=prompt,
        start_date=start_date,
        end_date=end_date,
    )

    client = get_client()
    response = await client.aio.models.generate_content(
        model=settings.DEFAULT_MODEL,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=1.0,
        ),
    )

    try:
        parsed = json.loads(response.text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}")

    # Handle wrapper object (e.g. {"transactions": [...]})
    if isinstance(parsed, dict) and "transactions" in parsed:
        parsed = parsed["transactions"]

    if not isinstance(parsed, list):
        raise ValueError("Gemini did not return a JSON array of transactions")

    errors = validate_transactions(parsed)
    if errors:
        raise ValueError(f"Generated transactions failed validation: {'; '.join(errors[:5])}")

    return parsed
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/fixture_generator.py backend/tests/test_fixture_generator.py
git commit -m "feat: add Gemini-powered transaction generation"
```

---

### Task 5: Backend — API Endpoints for Generation

**Files:**
- Modify: `backend/app/routers/fixtures.py`
- Modify: `backend/app/schemas/fixture.py`
- Modify: `backend/tests/test_fixture_generator.py`

**Step 1: Add request/response schemas**

Add to `backend/app/schemas/fixture.py`:

```python
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
```

**Step 2: Write failing test for API endpoints**

Add to `backend/tests/test_fixture_generator.py`:

```python
class TestGenerateProfileEndpoint:
    def test_returns_200_with_valid_profile(self, test_client):
        fake_profile = {
            "name": "Priya Patel",
            "profile": {
                "ageYears": 28,
                "location": {"city": "Pune", "state": "Maharashtra", "country": "India"},
                "monthlyIncomeRange": {"min": 60000, "max": 90000, "currency": "INR"},
                "creditScore": {"score": 780, "maxScore": 900},
                "bankAccounts": [{"issuerName": "SBI"}],
                "cards": [{"issuerName": "SBI", "productName": "SimplySAVE", "cardType": "CREDIT", "cardScheme": "VISA"}],
            },
        }
        with patch("app.routers.fixtures.generate_profile", new_callable=AsyncMock, return_value={"name": "Priya Patel", "data": fake_profile["profile"]}):
            response = test_client.post("/api/fixtures/generate-profile")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Priya Patel"
        assert "data" in body

    def test_returns_502_on_generation_error(self, test_client):
        with patch("app.routers.fixtures.generate_profile", new_callable=AsyncMock, side_effect=ValueError("validation failed")):
            response = test_client.post("/api/fixtures/generate-profile")
        assert response.status_code == 502


class TestGenerateTransactionsEndpoint:
    def test_returns_200_with_valid_transactions(self, test_client):
        fake_txs = [{
            "transactionId": "gen001", "date": "2026-01-15",
            "counterpartyName": "Store", "transactionType": "P2M",
            "merchantCategory": "Groceries", "amount": 100,
            "transactionDirection": "DEBIT",
        }]
        with patch("app.routers.fixtures.generate_transactions", new_callable=AsyncMock, return_value=fake_txs):
            response = test_client.post("/api/fixtures/generate-transactions", json={
                "prompt": "Generate test data",
                "start_date": "2026-01-01",
                "end_date": "2026-03-02",
            })
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert len(body["transactions"]) == 1

    def test_returns_502_on_generation_error(self, test_client):
        with patch("app.routers.fixtures.generate_transactions", new_callable=AsyncMock, side_effect=ValueError("validation failed")):
            response = test_client.post("/api/fixtures/generate-transactions", json={
                "prompt": "Generate test data",
                "start_date": "2026-01-01",
                "end_date": "2026-03-02",
            })
        assert response.status_code == 502
```

**Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py::TestGenerateProfileEndpoint -v`
Expected: FAIL — 404 (endpoint doesn't exist yet)

**Step 4: Add endpoints to fixtures router**

Add to `backend/app/routers/fixtures.py` (after existing imports):

```python
from app.services.fixture_generator import generate_profile, generate_transactions
from app.schemas.fixture import GenerateTransactionsRequest, GenerateProfileResponse, GenerateTransactionsResponse
```

Add endpoints (before the `/{fixture_id}` routes to avoid path conflicts):

```python
@router.post("/generate-profile", response_model=GenerateProfileResponse)
async def generate_profile_endpoint():
    try:
        result = await generate_profile()
        return result
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")


@router.post("/generate-transactions", response_model=GenerateTransactionsResponse)
async def generate_transactions_endpoint(req: GenerateTransactionsRequest):
    try:
        transactions = await generate_transactions(
            prompt=req.prompt,
            start_date=req.start_date,
            end_date=req.end_date,
            profile_data=req.profile_data,
        )
        return {"transactions": transactions, "count": len(transactions)}
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")
```

**Important:** The `/generate-profile` and `/generate-transactions` routes MUST be declared before `/{fixture_id}` in the router, otherwise FastAPI will try to match "generate-profile" as a fixture_id.

**Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_fixture_generator.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add backend/app/routers/fixtures.py backend/app/schemas/fixture.py backend/tests/test_fixture_generator.py
git commit -m "feat: add API endpoints for AI fixture generation"
```

---

### Task 6: Frontend — API Client + Types

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/types.ts`

**Step 1: Add types**

Add to `frontend/src/api/types.ts` after the `FixtureCreate` interface:

```typescript
export interface GenerateTransactionsRequest {
  prompt: string
  start_date: string
  end_date: string
  profile_data?: unknown
}

export interface GenerateProfileResponse {
  name: string
  data: unknown
}

export interface GenerateTransactionsResponse {
  transactions: unknown[]
  count: number
}
```

**Step 2: Add API methods**

Add to the `api` object in `frontend/src/api/client.ts`, inside the `// Fixtures` section:

```typescript
  generateProfile: () => request<GenerateProfileResponse>('/fixtures/generate-profile', { method: 'POST' }),
  generateTransactions: (data: GenerateTransactionsRequest) =>
    request<GenerateTransactionsResponse>('/fixtures/generate-transactions', { method: 'POST', body: JSON.stringify(data) }),
```

Also update the imports at the top to include the new types.

**Step 3: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/types.ts
git commit -m "feat: add frontend API client methods for fixture generation"
```

---

### Task 7: Frontend — Auto-Generate Profile on "New Profile"

**Files:**
- Modify: `frontend/src/pages/UserProfiles.tsx`

**Step 1: Add generating state and modify handleNew**

Changes to `UserProfiles.tsx`:

1. Add state variable for generation loading:
```typescript
const [generatingProfile, setGeneratingProfile] = useState(false)
```

2. Replace `handleNew` to call the generation endpoint:
```typescript
const handleNew = async () => {
  setSelected(null)
  setCreating(true)
  setError('')
  setGeneratingProfile(true)
  setName('Generating...')
  setSimulationDate(todayStr())
  setJsonData('{}')
  setTxJsonData('[]')
  setSelectedTx(null)

  try {
    const result = await api.generateProfile()
    setName(result.name)
    // Remove currentDate from display — managed by date picker
    const data = result.data as Record<string, unknown>
    const { currentDate: _, ...rest } = data
    setJsonData(JSON.stringify(rest, null, 2))
  } catch (e) {
    // Fall back to empty form on failure
    setName('')
    setJsonData('{}')
    setError(e instanceof Error ? `Profile generation failed: ${e.message}` : 'Profile generation failed')
  } finally {
    setGeneratingProfile(false)
  }
}
```

3. Add a loading overlay / indicator in the detail panel. Wrap the detail form section with a conditional:
```typescript
{generatingProfile && (
  <div className="flex items-center gap-3 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
    <div className="h-5 w-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
    <span className="text-sm text-indigo-700 font-medium">Generating random user profile with Gemini...</span>
  </div>
)}
```

4. Disable the "New Profile" button while generating:
```typescript
<button
  onClick={handleNew}
  disabled={generatingProfile}
  className="px-3 py-1 text-xs font-medium bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
>
  {generatingProfile ? 'Generating...' : 'New Profile'}
</button>
```

**Step 2: Verify manually**

Run: `pnpm dev` — click "New Profile", observe loading spinner, then form populated with AI-generated profile.

**Step 3: Commit**

```bash
git add frontend/src/pages/UserProfiles.tsx
git commit -m "feat: auto-generate user profile on New Profile click"
```

---

### Task 8: Frontend — Generate Transactions Panel

**Files:**
- Modify: `frontend/src/pages/UserProfiles.tsx`

**Step 1: Add transaction generation state**

Add state variables:
```typescript
const [txPrompt, setTxPrompt] = useState('')
const [generatingTx, setGeneratingTx] = useState(false)
```

Add a helper for default prompt (uses dynamic dates):
```typescript
const defaultTxPrompt = () => {
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - 3)
  const fmt = (d: Date) => d.toISOString().split('T')[0]
  return `Generate transactions between ${fmt(start)} and ${fmt(end)} for several categories, at least 20 per week, 4 different categories, include salary, flat rent transactions and P2P. Rupee transactions only.`
}
```

Initialize `txPrompt` in `handleNew`:
```typescript
setTxPrompt(defaultTxPrompt())
```

**Step 2: Add the generate transactions handler**

```typescript
const handleGenerateTx = async () => {
  setError('')
  setGeneratingTx(true)
  try {
    const end = new Date()
    const start = new Date()
    start.setMonth(start.getMonth() - 3)
    const fmt = (d: Date) => d.toISOString().split('T')[0]

    let profileData: unknown = undefined
    try {
      profileData = JSON.parse(jsonData)
    } catch {
      // ignore — profile context is optional
    }

    const result = await api.generateTransactions({
      prompt: txPrompt,
      start_date: fmt(start),
      end_date: fmt(end),
      profile_data: profileData,
    })
    setTxJsonData(JSON.stringify(result.transactions, null, 2))
  } catch (e) {
    setError(e instanceof Error ? `Transaction generation failed: ${e.message}` : 'Transaction generation failed')
  } finally {
    setGeneratingTx(false)
  }
}
```

**Step 3: Replace the transactions section in the JSX**

Replace the existing transactions `<div>` (the one with "Transactions (JSON)" label and single JsonEditor) with a two-column layout:

```tsx
<div>
  <label className="block text-sm font-medium text-slate-700 mb-1">
    Transactions (JSON)
    {!selectedTx && !creating && (
      <span className="ml-2 text-xs text-slate-400">No transactions fixture — will be created on save</span>
    )}
  </label>
  <div className="flex gap-4">
    {/* Left: transaction JSON editor */}
    <div className="flex-1">
      <JsonEditor value={txJsonData} onChange={setTxJsonData} height="300px" />
    </div>

    {/* Right: generate transactions panel */}
    {creating && (
      <div className="w-80 flex flex-col border border-slate-200 rounded-lg p-3 bg-slate-50">
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Generate Transactions</h3>
        <textarea
          value={txPrompt}
          onChange={(e) => setTxPrompt(e.target.value)}
          rows={8}
          className="w-full border border-slate-300 rounded px-3 py-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none mb-3"
          placeholder="Describe what transactions to generate..."
        />
        <button
          onClick={handleGenerateTx}
          disabled={generatingTx || !txPrompt.trim()}
          className="w-full px-3 py-2 text-sm font-medium bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {generatingTx ? (
            <>
              <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Generating...
            </>
          ) : (
            'Generate'
          )}
        </button>
        {generatingTx && (
          <p className="mt-2 text-xs text-slate-500 text-center">
            This may take 15-30 seconds...
          </p>
        )}
      </div>
    )}
  </div>
</div>
```

**Step 4: Update max-w constraint**

Change `max-w-2xl` to `max-w-4xl` on the detail container to accommodate the wider two-column layout:
```typescript
<div className="max-w-4xl space-y-4">
```

**Step 5: Verify manually**

Run: `pnpm dev` — click "New Profile", see the generate panel on the right of transactions, edit prompt, click Generate, observe spinner and "This may take 15-30 seconds...", then transactions populate.

**Step 6: Commit**

```bash
git add frontend/src/pages/UserProfiles.tsx
git commit -m "feat: add transaction generation panel with loading indicators"
```

---

### Task 9: Frontend — Tests for UserProfiles Page

**Files:**
- Create: `frontend/src/pages/UserProfiles.test.tsx`

**Step 1: Write component tests**

```tsx
// frontend/src/pages/UserProfiles.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UserProfiles from './UserProfiles'

// Mock the API module
vi.mock('../api/client', () => ({
  api: {
    listFixtures: vi.fn().mockResolvedValue([]),
    generateProfile: vi.fn().mockResolvedValue({
      name: 'Test User',
      data: {
        ageYears: 30,
        location: { city: 'Mumbai', state: 'Maharashtra', country: 'India' },
        monthlyIncomeRange: { min: 50000, max: 80000, currency: 'INR' },
        creditScore: { score: 750, maxScore: 900 },
        bankAccounts: [{ issuerName: 'HDFC Bank' }],
        cards: [{ issuerName: 'HDFC Bank', productName: 'Regalia', cardType: 'CREDIT', cardScheme: 'VISA' }],
      },
    }),
    generateTransactions: vi.fn().mockResolvedValue({
      transactions: [{ transactionId: 'tx1', counterpartyName: 'Store', amount: 100 }],
      count: 1,
    }),
    createFixture: vi.fn().mockResolvedValue({ id: '1', name: 'Test', type: 'user_profile', data: {}, created_at: '' }),
    updateFixture: vi.fn().mockResolvedValue({}),
    deleteFixture: vi.fn().mockResolvedValue(undefined),
  },
}))

import { api } from '../api/client'

describe('UserProfiles', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(api.listFixtures as ReturnType<typeof vi.fn>).mockResolvedValue([])
  })

  it('renders the page with profile list', async () => {
    render(<UserProfiles />)
    expect(screen.getByText('User Profiles')).toBeInTheDocument()
    expect(screen.getByText('New Profile')).toBeInTheDocument()
  })

  it('shows generating indicator when New Profile is clicked', async () => {
    // Make generateProfile take a while
    let resolveProfile: (v: unknown) => void
    ;(api.generateProfile as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((resolve) => { resolveProfile = resolve })
    )

    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    expect(screen.getByText(/generating random user profile/i)).toBeInTheDocument()
  })

  it('populates form after profile generation completes', async () => {
    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test User')).toBeInTheDocument()
    })
  })

  it('shows error on profile generation failure', async () => {
    ;(api.generateProfile as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('API down'))

    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    await waitFor(() => {
      expect(screen.getByText(/profile generation failed/i)).toBeInTheDocument()
    })
  })

  it('shows generate transactions panel when creating', async () => {
    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    await waitFor(() => {
      expect(screen.getByText('Generate Transactions')).toBeInTheDocument()
      expect(screen.getByText('Generate')).toBeInTheDocument()
    })
  })
})
```

**Step 2: Run tests**

Run: `pnpm nx run frontend:test`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add frontend/src/pages/UserProfiles.test.tsx
git commit -m "test: add UserProfiles page tests for AI generation"
```

---

### Task 10: Run Full Test Suite + Verify

**Step 1: Run all tests**

Run: `pnpm test`
Expected: All backend and frontend tests PASS

**Step 2: Manual smoke test**

Run: `pnpm dev`
1. Navigate to User Profiles page
2. Click "New Profile" — observe spinner, then form populates with AI profile
3. See "Generate Transactions" panel on the right
4. Click "Generate" — observe spinner + "This may take 15-30 seconds..." message
5. Transactions JSON editor populates with generated data
6. Click "Create" to save both profile + transactions

**Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address issues from integration testing"
```

---

### Task 11: Update Documentation

**Files:**
- Modify: `docs/BACKEND_COMPONENTS.md`
- Modify: `docs/FRONTEND_COMPONENTS.md`
- Modify: `docs/BUILD_PROGRESS.md`

Add to `docs/BACKEND_COMPONENTS.md`:
- Document `fixture_generator.py` service (generate_profile, generate_transactions, validation functions)
- Document new endpoints: `POST /api/fixtures/generate-profile`, `POST /api/fixtures/generate-transactions`

Add to `docs/FRONTEND_COMPONENTS.md`:
- Document UserProfiles auto-generation flow
- Document Generate Transactions panel

Update `docs/BUILD_PROGRESS.md`:
- Add entry for AI-powered fixture generation feature

**Commit:**
```bash
git add docs/
git commit -m "docs: document AI fixture generation feature"
```
