"""Match strategies for classification evaluation."""

from typing import Any


class MatchStrategy:
    def match(self, predicted: dict, expected: dict) -> dict:
        """Returns {"match": bool, "details": {...}}"""
        raise NotImplementedError


class ExactCategoryMatch(MatchStrategy):
    """Exact match on the 'category' field only."""

    def match(self, predicted: dict, expected: dict) -> dict:
        pred_cat = predicted.get("category")
        exp_cat = expected.get("category")
        is_match = pred_cat == exp_cat
        return {
            "match": is_match,
            "predicted_category": pred_cat,
            "expected_category": exp_cat,
        }


def get_matcher(strategy: str = "exact_category") -> MatchStrategy:
    strategies = {
        "exact_category": ExactCategoryMatch,
    }
    cls = strategies.get(strategy, ExactCategoryMatch)
    return cls()


def match_transaction_lists(
    predicted: list[dict],
    expected: list[dict],
    strategy: str = "exact_category",
) -> dict:
    """Compare two lists of transactions using the given strategy.

    Returns per-transaction match details and overall match rate.
    """
    matcher = get_matcher(strategy)
    details = []
    matches = 0

    # Match by position (aligned lists)
    max_len = max(len(predicted), len(expected))
    for i in range(max_len):
        pred = predicted[i] if i < len(predicted) else {}
        exp = expected[i] if i < len(expected) else {}
        result = matcher.match(pred, exp)
        result["index"] = i
        details.append(result)
        if result["match"]:
            matches += 1

    return {
        "total": max_len,
        "matches": matches,
        "match_rate": round(matches / max_len, 4) if max_len > 0 else 0,
        "details": details,
    }
