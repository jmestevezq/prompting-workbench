"""Mock tool handlers for the agent playground.

Each handler takes (args, fixtures) and returns a dict that becomes the tool response.
Fixtures is a dict like {"user_profile": {...}, "transactions": [...]}
"""

from datetime import datetime
from typing import Any

from app.services.code_sandbox import execute_agent_code


def execute_tool(tool_name: str, args: dict, fixtures: dict, context: dict | None = None) -> Any:
    handlers = {
        "fetch_transactions": _fetch_transactions,
        "get_user_profile": _get_user_profile,
        "execute_code": _execute_code,
    }
    handler = handlers.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}

    if tool_name == "execute_code":
        return handler(args, fixtures, context or {})
    return handler(args, fixtures)


def _fetch_transactions(args: dict, fixtures: dict) -> Any:
    transactions = fixtures.get("transactions", [])
    if not transactions:
        return {"transactions": [], "count": 0}

    filtered = list(transactions)

    # Apply filters
    if args.get("category"):
        filtered = [t for t in filtered if t.get("category", "").lower() == args["category"].lower()]
    if args.get("merchant_name"):
        filtered = [t for t in filtered if t.get("merchant_name", "").lower() == args["merchant_name"].lower()]
    if args.get("date_from"):
        try:
            date_from = datetime.strptime(args["date_from"], "%Y-%m-%d")
            filtered = [t for t in filtered if _parse_date(t.get("date")) and _parse_date(t["date"]) >= date_from]
        except ValueError:
            pass
    if args.get("date_to"):
        try:
            date_to = datetime.strptime(args["date_to"], "%Y-%m-%d")
            filtered = [t for t in filtered if _parse_date(t.get("date")) and _parse_date(t["date"]) <= date_to]
        except ValueError:
            pass
    if args.get("min_amount") is not None:
        filtered = [t for t in filtered if (t.get("amount") or 0) >= float(args["min_amount"])]
    if args.get("max_amount") is not None:
        filtered = [t for t in filtered if (t.get("amount") or 0) <= float(args["max_amount"])]

    # Apply group_by
    if args.get("group_by"):
        group_key = args["group_by"]
        groups: dict[str, list] = {}
        for t in filtered:
            key = str(t.get(group_key, "unknown"))
            groups.setdefault(key, []).append(t)

        grouped_result = []
        for key, items in groups.items():
            total = sum(t.get("amount", 0) for t in items)
            grouped_result.append({
                group_key: key,
                "count": len(items),
                "total_amount": round(total, 2),
                "transactions": items,
            })
        return {"groups": grouped_result, "total_count": len(filtered)}

    return {"transactions": filtered, "count": len(filtered)}


def _get_user_profile(args: dict, fixtures: dict) -> Any:
    profile = fixtures.get("user_profile")
    if not profile:
        return {"error": "No user profile fixture loaded"}
    return profile


def _execute_code(args: dict, fixtures: dict, context: dict) -> Any:
    code = args.get("code", "")
    if not code:
        return {"error": "No code provided"}

    # Build execution context with available data
    exec_context = {
        "transactions": fixtures.get("transactions", []),
        "user_profile": fixtures.get("user_profile", {}),
    }
    exec_context.update(context)

    from app.config import settings
    return execute_agent_code(code, exec_context, timeout=settings.CODE_EXECUTION_TIMEOUT)


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None
