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

# Production format sample data (GPay India style)
PRODUCTION_TRANSACTIONS = [
    {"transactionId": "TX001", "counterpartyName": "Spencers", "transactionType": "P2M",
     "merchantCategory": "Groceries and Supermarkets", "amount": 1037.10, "date": "2025-11-01",
     "transactionDirection": "DEBIT"},
    {"transactionId": "TX002", "counterpartyName": "Sneha Gupta", "transactionType": "P2P",
     "amount": 1725.94, "date": "2025-11-04", "transactionDirection": "CREDIT"},
    {"transactionId": "TX003", "counterpartyName": "Royal Cafe", "transactionType": "P2M",
     "merchantCategory": "Restaurants", "amount": 851.47, "date": "2025-11-06",
     "transactionDirection": "DEBIT"},
    {"transactionId": "TX004", "counterpartyName": "Amazon India", "transactionType": "P2M",
     "merchantCategory": "Online Marketplaces", "amount": 1740.20, "date": "2025-11-08",
     "transactionDirection": "DEBIT"},
    {"transactionId": "TX005", "counterpartyName": "Rohan Singh", "transactionType": "P2P",
     "amount": 3505.38, "date": "2025-11-07", "transactionDirection": "DEBIT"},
]

PRODUCTION_PROFILE = {
    "currentDate": "2025-11-28",
    "ageYears": 41,
    "location": {"city": "Lucknow", "state": "Uttar Pradesh", "country": "India"},
    "monthlyIncomeRange": {"min": 75000, "max": 125000, "currency": "INR"},
    "creditScore": {"score": 850, "maxScore": 900},
    "bankAccounts": [{"issuerName": "ICICI Bank"}],
    "cards": [
        {"issuerName": "ICICI Bank", "productName": "Platinum Chip Card",
         "cardType": "CREDIT", "cardScheme": "MASTER"},
    ],
}

PRODUCTION_FIXTURES = {
    "transactions": PRODUCTION_TRANSACTIONS,
    "user_profile": PRODUCTION_PROFILE,
}


class TestGetTransactionHistory:
    """Tests for the getTransactionHistory tool."""

    def test_returns_all_transactions_with_no_filters(self):
        result = execute_tool("getTransactionHistory", {}, SAMPLE_FIXTURES)
        assert result["status"] == "success"
        assert len(result["result"]) == 5

    def test_filter_by_category(self):
        result = execute_tool("getTransactionHistory", {"category": "groceries"}, SAMPLE_FIXTURES)
        assert len(result["result"]) == 2
        for tx in result["result"]:
            assert tx["category"] == "groceries"

    def test_filter_by_category_case_insensitive(self):
        result = execute_tool("getTransactionHistory", {"category": "GROCERIES"}, SAMPLE_FIXTURES)
        assert len(result["result"]) == 2

    def test_filter_by_merchant_name(self):
        result = execute_tool("getTransactionHistory", {"merchant_name": "uber"}, SAMPLE_FIXTURES)
        assert len(result["result"]) == 1
        assert result["result"][0]["merchant_name"] == "Uber"

    def test_filter_by_date_range(self):
        result = execute_tool("getTransactionHistory", {
            "date_from": "2026-01-12",
            "date_to": "2026-01-15",
        }, SAMPLE_FIXTURES)
        # Whole Foods (Jan 15), Uber (Jan 14), Safeway (Jan 12)
        assert len(result["result"]) == 3

    def test_filter_by_production_date_params(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "startDate": "2026-01-12",
            "endDate": "2026-01-15",
        }, SAMPLE_FIXTURES)
        assert len(result["result"]) == 3

    def test_filter_by_min_amount(self):
        result = execute_tool("getTransactionHistory", {"min_amount": 50}, SAMPLE_FIXTURES)
        for tx in result["result"]:
            assert tx["amount"] >= 50

    def test_filter_by_max_amount(self):
        result = execute_tool("getTransactionHistory", {"max_amount": 30}, SAMPLE_FIXTURES)
        for tx in result["result"]:
            assert tx["amount"] <= 30

    def test_response_limit(self):
        result = execute_tool("getTransactionHistory", {"responseLimit": 2}, SAMPLE_FIXTURES)
        assert len(result["result"]) == 2

    def test_production_limit_param(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {"limit": 2}, SAMPLE_FIXTURES)
        assert len(result["result"]) == 2

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
        assert result["result"] == []

    def test_missing_transactions_fixture(self):
        result = execute_tool("getTransactionHistory", {}, {})
        assert result["result"] == []

    def test_legacy_tool_name_fetch_transactions(self):
        result = execute_tool("fetch_transactions", {}, SAMPLE_FIXTURES)
        assert "result" in result

    def test_production_tool_name(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {}, SAMPLE_FIXTURES)
        assert result["status"] == "success"
        assert len(result["result"]) == 5

    def test_combined_filters(self):
        result = execute_tool("getTransactionHistory", {
            "category": "groceries",
            "min_amount": 100,
        }, SAMPLE_FIXTURES)
        assert len(result["result"]) == 1
        assert result["result"][0]["merchant_name"] == "Safeway"

    def test_merchant_categories_array_filter(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "merchantCategories": ["groceries", "entertainment"],
        }, SAMPLE_FIXTURES)
        assert len(result["result"]) == 3  # 2 groceries + 1 entertainment


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
        assert result["status"] == "success"
        for group in result["result"]:
            assert "count" in group
            assert "sumAmount" in group
            assert "averageAmount" in group

    def test_production_group_by_columns(self):
        result = execute_tool("GET_TRANSACTION_HISTORY_AGGREGATIONS",
                              {"groupByColumns": ["category"]}, SAMPLE_FIXTURES)
        assert result["status"] == "success"
        assert len(result["result"]) == 3  # groceries, transportation, entertainment

    def test_empty_transactions_returns_empty(self):
        result = execute_tool("getTransactionHistoryAggregations", {}, {"transactions": []})
        assert result["result"] == []

    def test_default_aggregation_is_sum(self):
        result_default = execute_tool("getTransactionHistoryAggregations", {}, SAMPLE_FIXTURES)
        result_sum = execute_tool("getTransactionHistoryAggregations",
                                  {"aggregation_type": "sum"}, SAMPLE_FIXTURES)
        assert result_default["result"] == result_sum["result"]

    def test_production_tool_name(self):
        result = execute_tool("GET_TRANSACTION_HISTORY_AGGREGATIONS",
                              {"aggregation_type": "sum"}, SAMPLE_FIXTURES)
        expected_sum = sum(t["amount"] for t in SAMPLE_TRANSACTIONS)
        assert abs(result["result"] - expected_sum) < 0.01


class TestGetUserProfile:
    """Tests for the getUserProfile tool."""

    def test_returns_user_profile_from_fixture(self):
        result = execute_tool("getUserProfile", {}, SAMPLE_FIXTURES)
        assert result["status"] == "success"
        assert result["result"]["name"] == "Jane Doe"
        assert result["result"]["monthly_budget"] == 3000

    def test_legacy_tool_name(self):
        result = execute_tool("get_user_profile", {}, SAMPLE_FIXTURES)
        assert result["result"]["name"] == "Jane Doe"

    def test_production_tool_name(self):
        result = execute_tool("GET_GPAY_USER_DATA_FOR_FINANCIAL_ASSISTANT", {}, SAMPLE_FIXTURES)
        assert result["status"] == "success"
        assert result["result"]["name"] == "Jane Doe"

    def test_missing_fixture_returns_error(self):
        result = execute_tool("getUserProfile", {}, {})
        assert result["status"] == "error"


class TestGoogleSearch:
    """Tests for the GOOGLE_SEARCH tool."""

    def test_returns_mock_results(self):
        result = execute_tool("GOOGLE_SEARCH", {"query": "HDFC Regalia card benefits"}, {})
        assert result["status"] == "success"
        assert len(result["result"]) > 0
        assert "HDFC Regalia" in result["result"][0]["snippet"]


class TestGetCibilData:
    """Tests for the GET_CIBIL_DATA tool."""

    def test_returns_default_mock(self):
        result = execute_tool("GET_CIBIL_DATA", {}, {})
        assert result["status"] == "success"
        assert "creditScore" in result["result"]
        assert isinstance(result["result"]["creditScore"], int)

    def test_returns_fixture_data(self):
        fixtures = {"cibil_data": {"creditScore": 810, "activeTradeLines": []}}
        result = execute_tool("GET_CIBIL_DATA", {}, fixtures)
        assert result["result"]["creditScore"] == 810


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

    def test_production_tool_name(self):
        result = execute_tool("CODE_EXECUTION",
                              {"code": "print(2+2)"},
                              SAMPLE_FIXTURES)
        assert result["returncode"] == 0
        assert "4" in result["stdout"]


class TestProductionFormatTransactions:
    """Tests for production format transactions with merchantCategory, counterpartyName, etc."""

    def test_filter_by_merchant_category(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "merchantCategories": ["Restaurants"],
        }, PRODUCTION_FIXTURES)
        assert len(result["result"]) == 1
        assert result["result"][0]["counterpartyName"] == "Royal Cafe"

    def test_filter_by_counterparty_name(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "counterpartyName": "Sneha",
        }, PRODUCTION_FIXTURES)
        assert len(result["result"]) == 1
        assert result["result"][0]["counterpartyName"] == "Sneha Gupta"

    def test_filter_by_transaction_direction(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "transactionDirection": "CREDIT",
        }, PRODUCTION_FIXTURES)
        assert len(result["result"]) == 1
        assert result["result"][0]["transactionDirection"] == "CREDIT"

    def test_filter_by_transaction_type_p2p(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "transactionType": "P2P",
        }, PRODUCTION_FIXTURES)
        assert len(result["result"]) == 2  # Sneha Gupta (CREDIT) + Rohan Singh (DEBIT)

    def test_filter_by_transaction_type_p2m(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "transactionType": "P2M",
        }, PRODUCTION_FIXTURES)
        assert len(result["result"]) == 3

    def test_combined_direction_and_type_filter(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "transactionType": "P2P",
            "transactionDirection": "DEBIT",
        }, PRODUCTION_FIXTURES)
        assert len(result["result"]) == 1
        assert result["result"][0]["counterpartyName"] == "Rohan Singh"

    def test_aggregation_by_merchant_category(self):
        result = execute_tool("GET_TRANSACTION_HISTORY_AGGREGATIONS", {
            "groupByColumns": ["merchantCategory"],
            "transactionDirection": "DEBIT",
        }, PRODUCTION_FIXTURES)
        assert result["status"] == "success"
        categories = {r["merchantCategory"] for r in result["result"]}
        assert "Restaurants" in categories
        assert "Groceries and Supermarkets" in categories

    def test_date_filter_with_production_params(self):
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "startDate": "2025-11-05",
            "endDate": "2025-11-07",
        }, PRODUCTION_FIXTURES)
        # Nov 6: Royal Cafe, Nov 7: Rohan Singh
        assert len(result["result"]) == 2

    def test_p2p_transactions_have_no_merchant_category(self):
        """P2P transfers should not have a merchantCategory field."""
        result = execute_tool("GET_TRANSACTION_HISTORY", {
            "transactionType": "P2P",
        }, PRODUCTION_FIXTURES)
        for tx in result["result"]:
            assert "merchantCategory" not in tx

    def test_grouping_by_category_on_production_data(self):
        """Grouping by 'category' should fall back to merchantCategory in production data."""
        result = execute_tool("getTransactionHistory", {
            "group_by": "category",
        }, PRODUCTION_FIXTURES)
        assert "groups" in result
        group_keys = {g["category"] for g in result["groups"]}
        assert "Restaurants" in group_keys


class TestProductionFormatUserProfile:
    """Tests for structured user profile transformation to production format."""

    def test_structured_profile_transforms(self):
        result = execute_tool("GET_GPAY_USER_DATA_FOR_FINANCIAL_ASSISTANT", {}, PRODUCTION_FIXTURES)
        assert result["status"] == "success"
        r = result["result"]
        assert r["ageYears"] == 41
        assert r["location"] == ["Lucknow", "Uttar Pradesh", "India"]
        assert r["monthlyIncomeRange"] == "75000 to 125000 INR"
        assert r["creditScore"] == "850 out of 900"
        assert len(r["bankAccountInfo"]) == 1
        assert r["bankAccountInfo"][0]["issuerName"] == "ICICI Bank"
        assert len(r["cardInfo"]) == 1
        assert r["cardInfo"][0]["productInfo"] == "Platinum Chip Card"
        assert r["cardInfo"][0]["cardSchemeType"] == "MASTER"

    def test_simple_profile_returns_as_is(self):
        """Old-format profiles should pass through without transformation."""
        result = execute_tool("getUserProfile", {}, SAMPLE_FIXTURES)
        assert result["result"]["name"] == "Jane Doe"
        assert result["result"]["monthly_budget"] == 3000

    def test_cibil_built_from_profile(self):
        """CIBIL handler should build response from user_profile when no cibil_data fixture."""
        result = execute_tool("GET_CIBIL_DATA", {}, PRODUCTION_FIXTURES)
        assert result["status"] == "success"
        assert result["result"]["creditScore"] == 850
        assert result["result"]["maxScore"] == 900
        assert len(result["result"]["activeTradeLines"]) == 1
        assert result["result"]["activeTradeLines"][0]["institution"] == "ICICI Bank"
