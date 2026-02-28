"""Mock tool handlers for the agent playground.

Each handler takes (args, fixtures) and returns a dict that becomes the tool response.
Fixtures is a dict like {"user_profile": {...}, "transactions": [...]}
"""

from datetime import datetime
from typing import Any

from app.services.code_sandbox import execute_agent_code


def execute_tool(tool_name: str, args: dict, fixtures: dict, context: dict | None = None) -> Any:
    handlers = {
        # New tool names (matching production patterns)
        "getTransactionHistory": _fetch_transactions,
        "getTransactionHistoryAggregations": _fetch_transactions_aggregations,
        "getUserProfile": _get_user_profile,
        "codeExecution": _execute_code,
        # Legacy tool names (backward compat)
        "fetch_transactions": _fetch_transactions,
        "get_user_profile": _get_user_profile,
        "execute_code": _execute_code,
    }
    handler = handlers.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}

    if tool_name in ("execute_code", "codeExecution"):
        return handler(args, fixtures, context or {})
    return handler(args, fixtures)


def _apply_filters(transactions: list, args: dict) -> list:
    """Apply common filters to a transaction list."""
    filtered = list(transactions)

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

    return filtered


def _fetch_transactions(args: dict, fixtures: dict) -> Any:
    transactions = fixtures.get("transactions", [])
    if not transactions:
        return {"transactions": [], "count": 0}

    filtered = _apply_filters(transactions, args)

    # Apply group_by (legacy support)
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

    # Sort
    sort_by = args.get("sort_by", "date")
    sort_order = args.get("sort_order", "desc")
    try:
        filtered.sort(key=lambda t: t.get(sort_by, ""), reverse=(sort_order == "desc"))
    except TypeError:
        pass

    # Apply responseLimit
    response_limit = args.get("responseLimit")
    if response_limit is not None:
        response_limit = int(response_limit)
        filtered = filtered[:response_limit]

    return {"transactions": filtered, "count": len(filtered)}


def _fetch_transactions_aggregations(args: dict, fixtures: dict) -> Any:
    """Handle getTransactionHistoryAggregations - returns sums, counts, averages."""
    transactions = fixtures.get("transactions", [])
    if not transactions:
        return {"result": 0, "count": 0}

    filtered = _apply_filters(transactions, args)
    amounts = [t.get("amount", 0) for t in filtered]

    agg_type = args.get("aggregation_type", "sum")

    if args.get("group_by"):
        group_key = args["group_by"]
        groups: dict[str, list] = {}
        for t in filtered:
            key = str(t.get(group_key, "unknown"))
            groups.setdefault(key, []).append(t)

        grouped_result = []
        for key, items in groups.items():
            item_amounts = [t.get("amount", 0) for t in items]
            grouped_result.append({
                group_key: key,
                "count": len(items),
                "total_amount": round(sum(item_amounts), 2),
                "average_amount": round(sum(item_amounts) / len(item_amounts), 2) if item_amounts else 0,
                "min_amount": round(min(item_amounts), 2) if item_amounts else 0,
                "max_amount": round(max(item_amounts), 2) if item_amounts else 0,
            })
        return {"groups": grouped_result, "total_count": len(filtered)}

    if not amounts:
        return {"result": 0, "count": 0}

    result = 0
    if agg_type == "sum":
        result = round(sum(amounts), 2)
    elif agg_type == "count":
        result = len(amounts)
    elif agg_type == "average":
        result = round(sum(amounts) / len(amounts), 2)
    elif agg_type == "min":
        result = round(min(amounts), 2)
    elif agg_type == "max":
        result = round(max(amounts), 2)

    return {"result": result, "count": len(amounts)}


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
