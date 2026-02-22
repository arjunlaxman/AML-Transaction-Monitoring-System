"""Metrics computation for model evaluation."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray | None = None,
) -> dict[str, float]:
    """Return precision, recall, F1, and optionally ROC-AUC."""
    metrics: dict[str, float] = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
        "f1":        float(f1_score(y_true, y_pred, zero_division=0)),
    }
    if y_prob is not None and len(np.unique(y_true)) > 1:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        except ValueError:
            metrics["roc_auc"] = 0.0
    return metrics


def rule_based_score(
    feature_row: np.ndarray,
    feature_names: list[str],
) -> float:
    """
    Heuristic suspicion score in [0, 1].

    Intentionally simple — the GNN should comfortably outperform this.
    """
    f = dict(zip(feature_names, feature_row.tolist()))
    score = 0.0

    # High outgoing transaction volume
    if f.get("num_sent", 0) > np.log1p(30):
        score += 0.12
    # High geographic diversity (multi-jurisdiction)
    if f.get("geo_diversity", 0) > 3:
        score += 0.15
    # Pass-through ratio (in ≈ out suggests layering)
    ratio = f.get("in_out_ratio", 0)
    if 0.85 <= ratio <= 1.20:
        score += 0.18
    # Accumulated risk flags
    if f.get("risk_flag_count", 0) > np.log1p(1):
        score += 0.20
    # High-risk jurisdiction domicile
    if f.get("country_risk", 0) > 0.5:
        score += 0.15
    # Mule or shell entity type encoding
    if f.get("entity_type_enc", 0) >= 2:
        score += 0.15
    # High transaction burstiness
    if f.get("burstiness", 0) > 1.5:
        score += 0.05

    return min(score, 1.0)
