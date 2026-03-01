"""Tests for the matching layer.

Focus: behavior and correctness of match strategies and transaction list comparison.
"""

import pytest
from app.services.matchers import (
    ExactCategoryMatch,
    get_matcher,
    match_transaction_lists,
)


class TestExactCategoryMatch:
    def test_matching_categories(self):
        matcher = ExactCategoryMatch()
        result = matcher.match(
            {"category": "food", "amount": 50},
            {"category": "food", "amount": 60},
        )
        assert result["match"] is True
        assert result["predicted_category"] == "food"
        assert result["expected_category"] == "food"

    def test_mismatched_categories(self):
        matcher = ExactCategoryMatch()
        result = matcher.match(
            {"category": "entertainment"},
            {"category": "food"},
        )
        assert result["match"] is False
        assert result["predicted_category"] == "entertainment"
        assert result["expected_category"] == "food"

    def test_case_sensitive_match(self):
        matcher = ExactCategoryMatch()
        # Match is case-sensitive
        result = matcher.match({"category": "Food"}, {"category": "food"})
        assert result["match"] is False

    def test_missing_predicted_category(self):
        matcher = ExactCategoryMatch()
        result = matcher.match({}, {"category": "food"})
        assert result["match"] is False
        assert result["predicted_category"] is None

    def test_missing_expected_category(self):
        matcher = ExactCategoryMatch()
        result = matcher.match({"category": "food"}, {})
        assert result["match"] is False
        assert result["expected_category"] is None

    def test_both_categories_missing(self):
        matcher = ExactCategoryMatch()
        result = matcher.match({}, {})
        assert result["match"] is True  # None == None


class TestGetMatcher:
    def test_default_strategy_is_exact_category(self):
        matcher = get_matcher()
        assert isinstance(matcher, ExactCategoryMatch)

    def test_explicit_exact_category(self):
        matcher = get_matcher("exact_category")
        assert isinstance(matcher, ExactCategoryMatch)

    def test_unknown_strategy_falls_back_to_exact(self):
        matcher = get_matcher("unknown_strategy")
        assert isinstance(matcher, ExactCategoryMatch)


class TestMatchTransactionLists:
    def test_perfect_match(self):
        predicted = [{"category": "food"}, {"category": "transport"}]
        expected = [{"category": "food"}, {"category": "transport"}]
        result = match_transaction_lists(predicted, expected)
        assert result["match_rate"] == 1.0
        assert result["matches"] == 2
        assert result["total"] == 2

    def test_complete_mismatch(self):
        predicted = [{"category": "food"}, {"category": "food"}]
        expected = [{"category": "transport"}, {"category": "entertainment"}]
        result = match_transaction_lists(predicted, expected)
        assert result["match_rate"] == 0.0
        assert result["matches"] == 0

    def test_partial_match(self):
        predicted = [{"category": "food"}, {"category": "wrong"}]
        expected = [{"category": "food"}, {"category": "transport"}]
        result = match_transaction_lists(predicted, expected)
        assert result["match_rate"] == 0.5
        assert result["matches"] == 1

    def test_predicted_longer_than_expected(self):
        predicted = [{"category": "food"}, {"category": "extra"}, {"category": "extra2"}]
        expected = [{"category": "food"}]
        result = match_transaction_lists(predicted, expected)
        assert result["total"] == 3  # max(3, 1)
        assert result["matches"] == 1  # only index 0 matches

    def test_expected_longer_than_predicted(self):
        predicted = [{"category": "food"}]
        expected = [{"category": "food"}, {"category": "transport"}, {"category": "entertainment"}]
        result = match_transaction_lists(predicted, expected)
        assert result["total"] == 3  # max(1, 3)
        assert result["matches"] == 1

    def test_empty_lists(self):
        result = match_transaction_lists([], [])
        assert result["match_rate"] == 0
        assert result["total"] == 0
        assert result["matches"] == 0

    def test_result_includes_details(self):
        predicted = [{"category": "food"}]
        expected = [{"category": "food"}]
        result = match_transaction_lists(predicted, expected)
        assert "details" in result
        assert len(result["details"]) == 1
        assert result["details"][0]["index"] == 0
        assert result["details"][0]["match"] is True

    def test_details_include_index(self):
        predicted = [{"category": "a"}, {"category": "b"}]
        expected = [{"category": "a"}, {"category": "c"}]
        result = match_transaction_lists(predicted, expected)
        assert result["details"][0]["index"] == 0
        assert result["details"][1]["index"] == 1

    def test_match_rate_rounds_to_4_decimals(self):
        predicted = [{"category": "a"}] * 1
        expected = [{"category": "a"}] * 1 + [{"category": "b"}] * 2
        result = match_transaction_lists(predicted, expected)
        # 1 match out of 3 = 0.3333...
        assert result["match_rate"] == round(1 / 3, 4)

    def test_custom_strategy(self):
        predicted = [{"category": "food"}]
        expected = [{"category": "food"}]
        result = match_transaction_lists(predicted, expected, strategy="exact_category")
        assert result["match_rate"] == 1.0
