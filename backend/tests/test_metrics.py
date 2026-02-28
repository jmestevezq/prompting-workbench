"""Tests for the metrics computation layer.

Focus: behavioral correctness of precision/recall/F1 and confusion matrix outputs.
"""

import pytest
from app.services.metrics import (
    compute_binary_metrics,
    compute_classification_metrics,
)


class TestComputeBinaryMetrics:
    """Autorater eval metrics: predicted labels vs ground truth labels."""

    def test_empty_results(self):
        result = compute_binary_metrics([])
        assert result["accuracy"] == 0
        assert result["total"] == 0

    def test_perfect_accuracy(self):
        results = [
            {"match": True, "predicted_labels": {"safety": "pass"}, "ground_truth_labels": {"safety": "pass"}},
            {"match": True, "predicted_labels": {"safety": "pass"}, "ground_truth_labels": {"safety": "pass"}},
        ]
        result = compute_binary_metrics(results)
        assert result["accuracy"] == 1.0
        assert result["total"] == 2
        assert result["correct"] == 2

    def test_zero_accuracy(self):
        results = [
            {"match": False, "predicted_labels": {"safety": "fail"}, "ground_truth_labels": {"safety": "pass"}},
            {"match": False, "predicted_labels": {"safety": "fail"}, "ground_truth_labels": {"safety": "pass"}},
        ]
        result = compute_binary_metrics(results)
        assert result["accuracy"] == 0.0

    def test_partial_accuracy(self):
        results = [
            {"match": True, "predicted_labels": {}, "ground_truth_labels": {}},
            {"match": False, "predicted_labels": {}, "ground_truth_labels": {}},
        ]
        result = compute_binary_metrics(results)
        assert result["accuracy"] == 0.5

    def test_per_label_precision_recall_f1(self):
        # 2 positive, 0 false positive, 0 false negative → perfect P/R/F1
        results = [
            {"match": True, "predicted_labels": {"safety": "pass"}, "ground_truth_labels": {"safety": "pass"}},
            {"match": True, "predicted_labels": {"safety": "pass"}, "ground_truth_labels": {"safety": "pass"}},
        ]
        result = compute_binary_metrics(results)
        assert "safety" in result["per_label"]
        label_metrics = result["per_label"]["safety"]
        assert label_metrics["precision"] == 1.0
        assert label_metrics["recall"] == 1.0
        assert label_metrics["f1"] == 1.0

    def test_precision_recall_with_false_positives_and_negatives(self):
        results = [
            # TP: predicted pass, truth pass
            {"match": True, "predicted_labels": {"safety": "pass"}, "ground_truth_labels": {"safety": "pass"}},
            # FP: predicted pass, truth is not pass (None in predicted context means different label)
            # Actually for binary_metrics it's checking if p_val == t_val
            # Let's test a mismatch case
            {"match": False, "predicted_labels": {"safety": "pass"}, "ground_truth_labels": {"safety": "none"}},
        ]
        result = compute_binary_metrics(results)
        label_metrics = result["per_label"]["safety"]
        # TP: 1 (both pass), FP: 1 (predicted pass, truth none)
        assert label_metrics["tp"] == 1
        assert label_metrics["fp"] == 1

    def test_confusion_matrix_included(self):
        results = [
            {"match": True, "predicted_labels": {"safety": "pass"}, "ground_truth_labels": {"safety": "pass"}},
        ]
        result = compute_binary_metrics(results)
        assert "confusion_matrix" in result

    def test_accuracy_rounded_to_4_decimals(self):
        results = [{"match": True, "predicted_labels": {}, "ground_truth_labels": {}}] * 1 + \
                  [{"match": False, "predicted_labels": {}, "ground_truth_labels": {}}] * 2
        result = compute_binary_metrics(results)
        assert result["accuracy"] == round(1 / 3, 4)

    def test_multiple_label_keys(self):
        results = [
            {
                "match": True,
                "predicted_labels": {"safety": "pass", "math": "correct"},
                "ground_truth_labels": {"safety": "pass", "math": "correct"},
            }
        ]
        result = compute_binary_metrics(results)
        assert "safety" in result["per_label"]
        assert "math" in result["per_label"]


class TestComputeClassificationMetrics:
    """Classification eval metrics: predicted output lists vs expected output lists."""

    def test_empty_results(self):
        result = compute_classification_metrics([])
        assert result["exact_match_rate"] == 0
        assert result["total"] == 0

    def test_perfect_exact_match(self):
        results = [
            {
                "predicted_output": [{"category": "food"}, {"category": "transport"}],
                "expected_output": [{"category": "food"}, {"category": "transport"}],
            }
        ]
        result = compute_classification_metrics(results)
        assert result["exact_match_rate"] == 1.0
        assert result["exact_matches"] == 1

    def test_no_exact_match_when_one_transaction_wrong(self):
        results = [
            {
                "predicted_output": [{"category": "food"}, {"category": "wrong"}],
                "expected_output": [{"category": "food"}, {"category": "transport"}],
            }
        ]
        result = compute_classification_metrics(results)
        assert result["exact_match_rate"] == 0.0
        assert result["exact_matches"] == 0

    def test_exact_match_requires_same_length(self):
        results = [
            {
                "predicted_output": [{"category": "food"}],
                "expected_output": [{"category": "food"}, {"category": "transport"}],
            }
        ]
        result = compute_classification_metrics(results)
        assert result["exact_match_rate"] == 0.0

    def test_partial_exact_match_across_multiple_entries(self):
        results = [
            {
                "predicted_output": [{"category": "food"}],
                "expected_output": [{"category": "food"}],
            },
            {
                "predicted_output": [{"category": "wrong"}],
                "expected_output": [{"category": "transport"}],
            },
        ]
        result = compute_classification_metrics(results)
        assert result["exact_match_rate"] == 0.5
        assert result["total"] == 2

    def test_per_category_metrics_included(self):
        results = [
            {
                "predicted_output": [{"category": "food"}, {"category": "food"}],
                "expected_output": [{"category": "food"}, {"category": "transport"}],
            }
        ]
        result = compute_classification_metrics(results)
        assert "per_category" in result
        assert "food" in result["per_category"]
        assert "transport" in result["per_category"]

    def test_per_category_has_prf(self):
        results = [
            {
                "predicted_output": [{"category": "food"}],
                "expected_output": [{"category": "food"}],
            }
        ]
        result = compute_classification_metrics(results)
        food_metrics = result["per_category"]["food"]
        assert "precision" in food_metrics
        assert "recall" in food_metrics
        assert "f1" in food_metrics
        assert "count" in food_metrics

    def test_perfect_per_category_metrics(self):
        results = [
            {
                "predicted_output": [{"category": "food"}],
                "expected_output": [{"category": "food"}],
            }
        ]
        result = compute_classification_metrics(results)
        food = result["per_category"]["food"]
        assert food["precision"] == 1.0
        assert food["recall"] == 1.0
        assert food["f1"] == 1.0

    def test_empty_predicted_output(self):
        results = [
            {
                "predicted_output": [],
                "expected_output": [{"category": "food"}],
            }
        ]
        result = compute_classification_metrics(results)
        assert result["exact_match_rate"] == 0.0

    def test_multiple_categories(self):
        results = [
            {
                "predicted_output": [
                    {"category": "food"},
                    {"category": "transport"},
                    {"category": "entertainment"},
                ],
                "expected_output": [
                    {"category": "food"},
                    {"category": "transport"},
                    {"category": "entertainment"},
                ],
            }
        ]
        result = compute_classification_metrics(results)
        assert result["exact_match_rate"] == 1.0
        assert len(result["per_category"]) == 3
