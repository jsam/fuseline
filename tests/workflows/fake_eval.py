from typing import Tuple

from fuseline import Computed, Depends


def calculate_precision_recall(true_positives: int, false_positives: int, false_negatives: int) -> Tuple[float, float]:
    """Calculate precision and recall."""
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    return precision, recall


def calculate_f1_score(
    precision_recall: Computed[Tuple[float, float]] = Depends(calculate_precision_recall),
) -> float:
    """Calculate F1 score from precision and recall."""
    precision, recall = precision_recall
    return 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0


def evaluate_model(f1_score: Computed[float] = Depends(calculate_f1_score)) -> str:
    """Evaluate the model based on F1 score."""
    if f1_score >= 0.8:
        return f"Excellent model performance with F1 score of {f1_score:.2f}"
    elif f1_score >= 0.6:
        return f"Good model performance with F1 score of {f1_score:.2f}"
    else:
        return f"Model needs improvement. F1 score: {f1_score:.2f}"
