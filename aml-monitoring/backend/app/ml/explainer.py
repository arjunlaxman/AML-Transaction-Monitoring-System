"""
Explainability module.

Approach:
  1. Train XGBoost surrogate on node features to approximate GNN probabilities.
  2. Apply SHAP TreeExplainer — produces per-feature attributions without
     requiring backpropagation through the graph.
  3. generate_narrative() produces regulator-ready case text from attributions.

This is an industry-standard approach for explaining GNN predictions:
the surrogate learns the GNN's decision surface on the feature space,
so SHAP values explain "why the GNN considers this entity suspicious."
"""

from __future__ import annotations

import numpy as np

try:
    import shap
    _SHAP = True
except ImportError:
    _SHAP = False

try:
    import xgboost as xgb
    _XGB = True
except ImportError:
    _XGB = False


def train_surrogate_and_shap(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_all: np.ndarray,
    feature_names: list[str],
    seed: int = 42,
) -> tuple[np.ndarray, object]:
    """
    Train a surrogate to approximate GNN output probabilities and compute SHAP values.

    Args:
        X_train:       node features for training nodes
        y_train:       GNN predicted probabilities for training nodes (soft targets)
        X_all:         node features for all nodes
        feature_names: names for SHAP display
        seed:          random seed

    Returns:
        shap_matrix: (n_nodes, n_features) array of SHAP values
        surrogate:   fitted surrogate model
    """
    if _XGB:
        surrogate = xgb.XGBRegressor(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            random_state=seed,
            tree_method="hist",
        )
        surrogate.fit(X_train, y_train, verbose=False)

        if _SHAP:
            explainer = shap.TreeExplainer(surrogate)
            shap_values = explainer.shap_values(X_all)
            return shap_values, surrogate

        # XGB without shap: gradient-perturbation approximation
        baseline_preds = surrogate.predict(X_all)
        shap_matrix = np.zeros_like(X_all)
        for j in range(X_all.shape[1]):
            Xp = X_all.copy()
            Xp[:, j] = X_all[:, j].mean()
            shap_matrix[:, j] = baseline_preds - surrogate.predict(Xp)
        return shap_matrix, surrogate

    # Fallback: Ridge regression with coefficient-based attribution
    from sklearn.linear_model import Ridge
    surrogate = Ridge(alpha=1.0)
    surrogate.fit(X_train, y_train)
    # Attribution = signed coefficient × (feature − mean)
    feat_mean = X_all.mean(axis=0)
    shap_matrix = (X_all - feat_mean) * surrogate.coef_[np.newaxis, :]
    return shap_matrix, surrogate


def generate_narrative(
    entity_id: str,
    entity_type: str,
    country: str,
    risk_score: float,
    cluster_id: str | None,
    cluster_size: int,
    pattern_type: str,
    shap_values: dict[str, float],
    top_k: int = 4,
) -> str:
    """
    Generate a regulator-ready SAR-style case narrative.

    Args:
        entity_id:    entity identifier
        entity_type:  e.g. "mule", "shell", "individual"
        country:      ISO country code
        risk_score:   GNN suspicion probability [0, 1]
        cluster_id:   suspicious cluster ID (may be None)
        cluster_size: number of entities in cluster
        pattern_type: "smurfing" | "layering" | "circular" | "mixed"
        shap_values:  feature → SHAP value dict
        top_k:        number of risk drivers to highlight

    Returns:
        Multi-section narrative string suitable for a case file.
    """
    risk_level = "HIGH" if risk_score > 0.75 else "MEDIUM" if risk_score > 0.50 else "ELEVATED"
    risk_tier  = "1" if risk_score > 0.75 else "2" if risk_score > 0.50 else "3"

    pattern_descriptions = {
        "smurfing":  (
            "structuring / smurfing — multiple transactions just below the $10,000 "
            "reporting threshold, consistent with deliberate avoidance of CTR requirements"
        ),
        "layering":  (
            "multi-hop transaction layering — funds routed through a chain of intermediary "
            "entities across multiple high-risk jurisdictions to obscure beneficial ownership"
        ),
        "circular":  (
            "circular fund flows — transactions forming closed loops among a small set of "
            "entities, consistent with wash transactions or value-inflation schemes"
        ),
        "mixed":     "multiple co-occurring suspicious transaction patterns",
    }
    pattern_desc = pattern_descriptions.get(pattern_type.lower(), "anomalous transaction behavior")

    # Top SHAP drivers (positive = increases risk)
    sorted_shap = sorted(shap_values.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_k]
    driver_lines = []
    for fname, val in sorted_shap:
        readable = fname.replace("_", " ").title()
        direction = "↑ Elevates" if val > 0 else "↓ Mitigates"
        driver_lines.append(f"    • {readable}: {direction} risk  (attribution: {val:+.4f})")
    drivers_str = "\n".join(driver_lines)

    narrative = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUSPICIOUS ACTIVITY REPORT — CASE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ENTITY:       {entity_id}
TYPE:         {entity_type.upper()}
JURISDICTION: {country}
RISK LEVEL:   {risk_level}  (Tier {risk_tier} — Score: {risk_score:.4f})

── EXECUTIVE SUMMARY ──────────────────────────────

Entity {entity_id} ({entity_type}, {country}) has been flagged by the Graph Neural
Network with a suspicion score of {risk_score:.4f}, placing it in the {risk_level} risk tier.
{"This entity is a member of suspicious cluster " + cluster_id + " comprising " + str(cluster_size) + " interconnected entities." if cluster_id else "No cluster association was identified; the entity's individual transaction patterns drive this alert."}

The predominant typology detected is {pattern_desc}.

── KEY RISK DRIVERS (SHAP Attributions) ───────────

{drivers_str}

── RECOMMENDED ACTIONS ────────────────────────────

  1. File a Suspicious Activity Report (SAR) with FinCEN within 30 days.
  2. Freeze account pending enhanced due diligence review.
  3. Conduct full 12-month transaction history analysis for entity and
     all {"cluster members" if cluster_id else "first-degree counterparties"}.
  4. Escalate to Compliance Officer (Level 2) and Legal Counsel.
  5. Preserve all records per BSA record-retention requirements.

── REGULATORY REFERENCES ──────────────────────────

  31 U.S.C. § 5318(g)  — SAR Filing Obligation
  31 CFR § 1020.320    — Reports of Suspicious Transactions
  FinCEN Advisory FIN-2014-A007 — Layering Typologies

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated by AML GNN System v1.0 | Explainability: XGBoost-SHAP Surrogate
"""
    return narrative.strip()
