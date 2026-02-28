"""Tests for mock tool execution.

Focus: behavioral correctness of filtering, aggregation, and dispatch logic.
"""

import pytest
from app.services.mock_tools import execute_tool


SAMPLE_TRANSACTIONS = [
    {"merchant_name": "Whole Foods", "category": "groceries", "amount": 85.50, "date": "2026-01-15"},
    {"merchant_name": "Uber", "category": "transportation", "amount": 22.00, "date": "2026-01-14"},
    {"merchant_name": "Netflix", "category": "entertainment", "amount": 15.99, "date": "2026-01-10"},
    {"merchant_name": "Safeway", "category": "groceries", "amount": 120.00, "date": "2026-01-12"},
    {"merchant_name": "Shell", "category": "transportation", "amount": 55.00, "date": "2026-01-08"},
]

SAMPLE_FIXTURES = {
    "transactions": SAMPLE_TRANSACTIONS,
    "user_profile": {"name": "Jane Doe", "monthly_budget": 3000},
}


class TestGetTransactionHistory:
    """Tests for the getTransactionHistory tool."""

    def test_returns_all_transactions_with_no_filters(self):
        result = execute_tool("getTransactionHistory", {}, SAMPLE_FIXTURES)
        assert "transactions" in result
        assert len(result["transactions"]) == 5
        assert result["count"] == 5

    def test_filter_by_category(self):
        result = execute_tool("getTransactionHistory", {"category": "groceries"}, SAMPLE_FIXTURES)
        assert result["count"] == 2
        for tx in result["transactions"]:
            assert tx["category"] == "groceries"

    def test_filter_by_category_case_insensitive(self):
        result = execute_tool("getTransactionHistory", {"category": "GROCERIES"}, SAMPLE_FIXTURES)
        assert result["count"] == 2

    def test_filter_by_merchant_name(self):
        result = execute_tool("getTransactionHistory", {"merchant_name": "uber"}, SAMPLE_FIXTURES)
        assert result["count"] == 1
        assert result["transactions"][0]["merchant_name"] == "Uber"

    def test_filter_by_date_range(self):
        result = execute_tool("getTransactionHistory", {
            "date_from": "2026-01-12",
            "date_to": "2026-01-15",
        }, SAMPLE_FIXTURES)
        # Whole Foods (Jan 15), Uber (Jan 14), Safeway (Jan 12)
        assert result["count"] == 3

    def test_filter_by_min_amount(self):
        result = execute_tool("getTransactionHistory", {"min_amount": 50}, SAMPLE_FIXTURES)
        for tx in result["transactions"]:
            assert tx["amount"] >= 50

    def test_filter_by_max_amount(self):
        result = execute_tool("getTransactionHistory", {"max_amount": 30}, SAMPLE_FIXTURES)
        for tx in result["transactions"]:
            assert tx["amount"] <= 30

    def test_response_limit(self):
        result = execute_tool("getTransactionHistory", {"responseLimit": 2}, SAMPLE_FIXTURES)
        assert result["count"] == 2

    def test_group_by_category(self):
        result = execute_tool("getTransactionHistory", {"group_by": "category"}, SAMPLE_FIXTURES)
        assert "groups" in result
        # Should have 3 categories: groceries, transportation, entertainment
        assert result["total_count"] == 5
        group_keys = {g["category"] for g in result["groups"]}
        assert "groceries" in group_keys
        assert "transportation" in group_keys

    def test_group_by_includes_totals(self):
        result = execute_tool("getTransactionHistory", {"group_by": "category"}, SAMPLE_FIXTURES)
        for group in result["groups"]:
            assert "count" in group
            assert "total_amount" in group
            assert "transactions" in group

    def test_empty_transactions_fixture(self):
        result = execute_tool("getTransactionHistory", {}, {"transactions": []})
        assert result["count"] == 0
        assert result["transactions"] == []

    def test_missing_transactions_fixture(self):
        result = execute_tool("getTransactionHistory", {}, {})
        assert result["count"] == 0

    def test_legacy_tool_name_fetch_transactions(self):
        result = execute_tool("fetch_transactions", {}, SAMPLE_FIXTURES)
        assert "transactions" in result

    def test_combined_filters(self):
        result = execute_tool("getTransactionHistory", {
            "category": "groceries",
            "min_amount": 100,
        }, SAMPLE_FIXTURES)
        assert result["count"] == 1
        assert result["transactions"][0]["merchant_name"] == "Safeway"


class TestGetTransactionHistoryAggregations:
    """Tests for the getTransactionHistoryAggregations tool."""

    def test_sum_aggregation(self):
        result = execute_tool("getTransactionHistoryAggregations",
                              {"aggregation_type": "sum"}, SAMPLE_FIXTURES)
        expected_sum = sum(t["amount"] for t in SAMPLE_TRANSACTIONS)
        assert abs(result["result"] - expected_sum) < 0.01

    def test_count_aggregation(self):
        result = execute_tool("getTransactionHistoryAggregations",
                              {"aggregation_type": "count"}, SAMPLE_FIXTURES)
        assert result["result"] == 5

    def test_average_aggregation(self):
        result = execute_tool("getTransactionHistoryAggregations",
                              {"aggregation_type": "average"}, SAMPLE_FIXTURES)
        total = sum(t["amount"] for t in SAMPLE_TRANSACTIONS)
        expected_avg = total / len(SAMPLE_TRANSACTIONS)
        assert abs(result["result"] - expected_avg) < 0.01

    def test_min_aggregation(self):
        result = execute_tool("getTransactionHistoryAggregations",
                              {"aggregation_type": "min"}, SAMPLE_FIXTURES)
        assert result["result"] == 15.99

    def test_max_aggregation(self):
        result = execute_tool("getTransactionHistoryAggregations",
                              {"aggregation_type": "max"}, SAMPLE_FIXTURES)
        assert result["result"] == 120.00

    def test_filter_before_aggregation(self):
        result = execute_tool("getTransactionHistoryAggregations", {
            "category": "groceries",
            "aggregation_type": "sum",
        }, SAMPLE_FIXTURES)
        assert abs(result["result"] - (85.50 + 120.00)) < 0.01

    def test_group_by_with_aggregation(self):
        result = execute_tool("getTransactionHistoryAggregations",
                              {"group_by": "category"}, SAMPLE_FIXTURES)
        assert "groups" in result
        for group in result["groups"]:
            assert "count" in group
            assert "total_amount" in group
            assert "average_amount" in group

    def test_empty_transactions_returns_zero(self):
        result = execute_tool("getTransactionHistoryAggregations", {}, {"transactions": []})
        assert result["result"] == 0
        assert result["count"] == 0

    def test_default_aggregation_is_sum(self):
        result_default = execute_tool("getTransactionHistoryAggregations", {}, SAMPLE_FIXTURES)
        result_sum = execute_tool("getTransactionHistoryAggregations",
                                  {"aggregation_type": "sum"}, SAMPLE_FIXTURES)
        assert result_default["result"] == result_sum["result"]


class TestGetUserProfile:
    """Tests for the getUserProfile tool."""

    def test_returns_user_profile_from_fixture(self):
        result = execute_tool("getUserProfile", {}, SAMPLE_FIXTURES)
        assert result["name"] == "Jane Doe"
        assert result["monthly_budget"] == 3000

    def test_legacy_tool_name(self):
        result = execute_tool("get_user_profile", {}, SAMPLE_FIXTURES)
        assert result["name"] == "Jane Doe"

    def test_missing_fixture_returns_error(self):
        result = execute_tool("getUserProfile", {}, {})
        assert "error" in result


class TestUnknownTool:
    """Tests for unknown tool dispatch."""

    def test_unknown_tool_returns_error(self):
        result = execute_tool("nonexistent_tool", {}, SAMPLE_FIXTURES)
        assert "error" in result
        assert "nonexistent_tool" in result["error"]


class TestCodeExecution:
    """Tests for the codeExecution tool."""

    def test_simple_code_executes(self):
        result = execute_tool("codeExecution",
                              {"code": "print('hello world')"},
                              SAMPLE_FIXTURES)
        assert "stdout" in result
        assert "hello world" in result["stdout"]

    def test_transactions_available_in_code_context(self):
        result = execute_tool("codeExecution",
                              {"code": "print(len(transactions))"},
                              SAMPLE_FIXTURES)
        assert result["returncode"] == 0
        assert "5" in result["stdout"]

    def test_code_with_syntax_error_returns_stderr(self):
        result = execute_tool("codeExecution",
                              {"code": "this is not valid python !!!"},
                              SAMPLE_FIXTURES)
        assert result["returncode"] != 0
        assert result["stderr"] != ""

    def test_empty_code_returns_error(self):
        result = execute_tool("codeExecution", {"code": ""}, SAMPLE_FIXTURES)
        assert "error" in result

    def test_no_code_key_returns_error(self):
        result = execute_tool("codeExecution", {}, SAMPLE_FIXTURES)
        assert "error" in result

    def test_legacy_execute_code_name(self):
        result = execute_tool("execute_code",
                              {"code": "print('hi')"},
                              SAMPLE_FIXTURES,
                              context={})
        assert result["returncode"] == 0
