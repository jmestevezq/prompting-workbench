"""Precision, recall, F1 computation and confusion matrix."""

from collections import Counter
from typing import Any


def compute_binary_metrics(results: list[dict]) -> dict:
    """Compute metrics from a list of {predicted, ground_truth, match} dicts.

    For autorater eval where each transcript has a single predicted vs ground_truth label.
    """
    if not results:
        return {"accuracy": 0, "total": 0}

    total = len(results)
    correct = sum(1 for r in results if r.get("match"))
    accuracy = correct / total if total > 0 else 0

    # Compute per-label metrics
    all_labels = set()
    for r in results:
        if isinstance(r.get("predicted_labels"), dict):
            all_labels.update(r["predicted_labels"].keys())
        if isinstance(r.get("ground_truth_labels"), dict):
            all_labels.update(r["ground_truth_labels"].keys())

    per_label = {}
    for label_key in all_labels:
        tp = fp = fn = tn = 0
        for r in results:
            pred = r.get("predicted_labels", {})
            truth = r.get("ground_truth_labels", {})
            p_val = pred.get(label_key) if isinstance(pred, dict) else None
            t_val = truth.get(label_key) if isinstance(truth, dict) else None
            if p_val == t_val:
                if p_val is not None:
                    tp += 1
                else:
                    tn += 1
            else:
                if p_val is not None:
                    fp += 1
                if t_val is not None:
                    fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        per_label[label_key] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        }

    # Build confusion matrix for the most common label
    confusion = _build_confusion_matrix(results)

    return {
        "accuracy": round(accuracy, 4),
        "total": total,
        "correct": correct,
        "per_label": per_label,
        "confusion_matrix": confusion,
    }


def compute_classification_metrics(
    results: list[dict],
) -> dict:
    """Compute metrics for classification eval.

    Each result has predicted_output and expected_output (lists of transactions).
    """
    if not results:
        return {"exact_match_rate": 0, "total": 0}

    total = len(results)
    exact_matches = 0
    all_categories_pred = []
    all_categories_true = []

    for r in results:
        predicted = r.get("predicted_output", [])
        expected = r.get("expected_output", [])

        # Check exact match (all transactions match)
        if _lists_match(predicted, expected):
            exact_matches += 1

        # Collect per-transaction categories for P/R/F1
        for p in predicted:
            all_categories_pred.append(p.get("category", "unknown"))
        for e in expected:
            all_categories_true.append(e.get("category", "unknown"))

    exact_match_rate = exact_matches / total if total > 0 else 0

    # Per-category P/R/F1
    per_category = _compute_per_category_metrics(all_categories_pred, all_categories_true)

    return {
        "exact_match_rate": round(exact_match_rate, 4),
        "total": total,
        "exact_matches": exact_matches,
        "per_category": per_category,
    }


def _lists_match(predicted: list, expected: list) -> bool:
    if len(predicted) != len(expected):
        return False
    for p, e in zip(predicted, expected):
        if p.get("category") != e.get("category"):
            return False
    return True


def _compute_per_category_metrics(predicted: list[str], true: list[str]) -> dict:
    all_cats = set(predicted) | set(true)
    pred_counts = Counter(predicted)
    true_counts = Counter(true)

    result = {}
    for cat in all_cats:
        tp = min(pred_counts.get(cat, 0), true_counts.get(cat, 0))
        fp = max(0, pred_counts.get(cat, 0) - true_counts.get(cat, 0))
        fn = max(0, true_counts.get(cat, 0) - pred_counts.get(cat, 0))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        result[cat] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "count": true_counts.get(cat, 0),
        }
    return result


def _build_confusion_matrix(results: list[dict]) -> dict:
    """Build confusion matrix from eval results."""
    # For autorater: compare predicted vs ground truth for each label dimension
    matrix: dict[str, dict[str, int]] = {}

    for r in results:
        pred = r.get("predicted_labels", {})
        truth = r.get("ground_truth_labels", {})
        if not isinstance(pred, dict) or not isinstance(truth, dict):
            continue

        for key in set(list(pred.keys()) + list(truth.keys())):
            p_val = str(pred.get(key, "none"))
            t_val = str(truth.get(key, "none"))

            if key not in matrix:
                matrix[key] = {}
            pair_key = f"{t_val} -> {p_val}"
            matrix[key][pair_key] = matrix[key].get(pair_key, 0) + 1

    return matrix
