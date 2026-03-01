"""Mock tool handlers for the agent playground.

Each handler takes (args, fixtures) and returns a dict that becomes the tool response.
Fixtures is a dict like {"user_profile": {...}, "transactions": [...]}
"""

from datetime import datetime
from typing import Any

from app.services.code_sandbox import execute_agent_code


# Tool names that use the code execution handler (need extra context arg)
_CODE_TOOLS = {"execute_code", "codeExecution", "CODE_EXECUTION"}


def execute_tool(tool_name: str, args: dict, fixtures: dict, context: dict | None = None) -> Any:
    handlers = {
        # Production tool names (UPPER_SNAKE_CASE)
        "GET_GPAY_USER_DATA_FOR_FINANCIAL_ASSISTANT": _get_user_profile,
        "GET_TRANSACTION_HISTORY_AGGREGATIONS": _fetch_transactions_aggregations,
        "GET_TRANSACTION_HISTORY": _fetch_transactions,
        "CODE_EXECUTION": _execute_code,
        "GOOGLE_SEARCH": _google_search,
        "GET_CIBIL_DATA": _get_cibil_data,
        # camelCase tool names (backward compat)
        "getTransactionHistory": _fetch_transactions,
        "getTransactionHistoryAggregations": _fetch_transactions_aggregations,
        "getUserProfile": _get_user_profile,
        "codeExecution": _execute_code,
        # Legacy snake_case names
        "fetch_transactions": _fetch_transactions,
        "get_user_profile": _get_user_profile,
        "execute_code": _execute_code,
    }
    handler = handlers.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}

    if tool_name in _CODE_TOOLS:
        return handler(args, fixtures, context or {})
    return handler(args, fixtures)


def _apply_filters(transactions: list, args: dict) -> list:
    """Apply common filters to a transaction list.

    Supports both legacy parameter names (category, date_from) and
    production parameter names (merchantCategories, startDate).
    """
    filtered = list(transactions)

    # Category filter — legacy single value or production array
    category = args.get("category")
    merchant_categories = args.get("merchantCategories", [])
    if category:
        filtered = [t for t in filtered if t.get("category", "").lower() == category.lower()]
    elif merchant_categories:
        cats_lower = [c.lower() for c in merchant_categories]
        filtered = [t for t in filtered if t.get("category", "").lower() in cats_lower]

    # Merchant/counterparty name filter
    merchant_name = args.get("merchant_name") or args.get("counterpartyName")
    if merchant_name:
        name_lower = merchant_name.lower()
        filtered = [
            t for t in filtered
            if name_lower in (t.get("merchant_name", "") or t.get("counterpartyName", "")).lower()
        ]

    # Date range — legacy or production names
    date_from_str = args.get("date_from") or args.get("startDate")
    date_to_str = args.get("date_to") or args.get("endDate")
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
            filtered = [t for t in filtered if _parse_date(t.get("date")) and _parse_date(t["date"]) >= date_from]
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d")
            filtered = [t for t in filtered if _parse_date(t.get("date")) and _parse_date(t["date"]) <= date_to]
        except ValueError:
            pass

    # Transaction direction filter (DEBIT / CREDIT)
    direction = args.get("transactionDirection")
    if direction:
        dir_lower = direction.lower()
        filtered = [t for t in filtered if (t.get("transactionDirection", "") or "").lower() == dir_lower]

    # Payment method filter
    payment_method = args.get("paymentMethod")
    if payment_method:
        pm_lower = payment_method.lower()
        filtered = [
            t for t in filtered
            if pm_lower in str(t.get("paymentMethod", "")).lower()
        ]

    # Amount range
    if args.get("min_amount") is not None:
        filtered = [t for t in filtered if (t.get("amount") or 0) >= float(args["min_amount"])]
    if args.get("max_amount") is not None:
        filtered = [t for t in filtered if (t.get("amount") or 0) <= float(args["max_amount"])]

    return filtered


def _fetch_transactions(args: dict, fixtures: dict) -> Any:
    transactions = fixtures.get("transactions", [])
    if not transactions:
        return {"status": "success", "result": []}

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

    # Apply limit (production: "limit", legacy: "responseLimit")
    response_limit = args.get("limit") or args.get("responseLimit")
    if response_limit is not None:
        response_limit = int(response_limit)
        filtered = filtered[:response_limit]

    return {"status": "success", "result": filtered}


def _fetch_transactions_aggregations(args: dict, fixtures: dict) -> Any:
    """Handle transaction aggregations — returns sums, counts, averages grouped by column."""
    transactions = fixtures.get("transactions", [])
    if not transactions:
        return {"status": "success", "result": []}

    filtered = _apply_filters(transactions, args)

    # Determine grouping — production uses groupByColumns array, legacy uses group_by string
    group_by_cols = args.get("groupByColumns", [])
    legacy_group = args.get("group_by")
    if legacy_group and not group_by_cols:
        group_by_cols = [legacy_group]

    if group_by_cols:
        # Group by the first column (primary grouping)
        group_key = group_by_cols[0]
        groups: dict[str, list] = {}
        for t in filtered:
            key = str(t.get(group_key, "unknown"))
            groups.setdefault(key, []).append(t)

        result = []
        for key, items in groups.items():
            item_amounts = [t.get("amount", 0) for t in items]
            entry = {
                group_key: key,
                "count": len(items),
                "sumAmount": str(round(sum(item_amounts), 2)),
                "averageAmount": str(round(sum(item_amounts) / len(item_amounts), 2)) if item_amounts else "0",
                "minAmount": str(round(min(item_amounts), 2)) if item_amounts else "0",
                "maxAmount": str(round(max(item_amounts), 2)) if item_amounts else "0",
            }
            # Include transactionDirection if filtered
            if args.get("transactionDirection"):
                entry["transactionDirection"] = args["transactionDirection"]
            result.append(entry)
        return {"status": "success", "result": result}

    # No grouping — aggregate all
    amounts = [t.get("amount", 0) for t in filtered]
    if not amounts:
        return {"status": "success", "result": []}

    agg_type = args.get("aggregation_type", "sum")
    value = 0
    if agg_type == "sum":
        value = round(sum(amounts), 2)
    elif agg_type == "count":
        value = len(amounts)
    elif agg_type == "average":
        value = round(sum(amounts) / len(amounts), 2)
    elif agg_type == "min":
        value = round(min(amounts), 2)
    elif agg_type == "max":
        value = round(max(amounts), 2)

    return {"status": "success", "result": value, "count": len(amounts)}


def _get_user_profile(args: dict, fixtures: dict) -> Any:
    profile = fixtures.get("user_profile")
    if not profile:
        return {"status": "error", "error": "No user profile fixture loaded"}
    return {"status": "success", "result": profile}


def _get_cibil_data(args: dict, fixtures: dict) -> Any:
    """Return CIBIL credit data from fixtures or a default mock."""
    cibil = fixtures.get("cibil_data")
    if cibil:
        return {"status": "success", "result": cibil}
    # Default mock when no fixture is loaded
    return {
        "status": "success",
        "result": {
            "creditScore": 750,
            "activeTradeLines": [
                {
                    "institution": "HDFC Bank",
                    "accountType": "Credit Card",
                    "outstandingBalance": 25000,
                    "estimatedInterestRate": 3.5,
                },
            ],
        },
    }


def _google_search(args: dict, fixtures: dict) -> Any:
    """Mock web search — returns a placeholder result."""
    query = args.get("query", "")
    return {
        "status": "success",
        "result": [
            {
                "title": f"Search results for: {query}",
                "snippet": f"Mock search result for '{query}'. In production, this would return real web search results.",
                "uri": "https://example.com/mock-search",
            },
        ],
    }


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
