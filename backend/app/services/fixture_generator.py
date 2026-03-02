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
