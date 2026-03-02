"""AI-powered fixture generation using Gemini."""

import json
import re
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
