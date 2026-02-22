"""
Training pipeline: GNN → surrogate SHAP → metrics.

Steps:
  1. Extract 18-dim node features + build PyG/tensor graph
  2. Train GraphSAGE with class-weighted cross-entropy (handles ~5% positive rate)
  3. Get GNN embeddings on all nodes
  4. Train XGBoost surrogate on features+embeddings, compute SHAP
  5. Compute metrics for GNN, rule-based, and logistic regression baselines
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve
from sklearn.model_selection import train_test_split

from app.core.config import get_settings
from app.ml.data_generator import (
    EntityRecord,
    TransactionRecord,
    build_networkx_graph,
    compute_node_features,
)
from app.ml.explainer import train_surrogate_and_shap
from app.ml.gnn_model import GraphSAGE, build_graph_tensors
from app.ml.metrics import compute_classification_metrics, rule_based_score


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def train(
    entities: list[EntityRecord],
    transactions: list[TransactionRecord],
    mode: str = "demo",
    seed: int = 42,
) -> dict:
    """
    Full training pipeline.

    Returns:
        metrics:      precision/recall/F1 for GNN + baselines
        node_scores:  dict[entity_id → float suspicion probability]
        node_shap:    dict[entity_id → dict[feature → shap_value]]
        feature_names: list of feature names
    """
    settings = get_settings()
    _set_seed(seed)

    epochs = settings.gnn_epochs_demo if mode == "demo" else settings.gnn_epochs_full
    hidden = settings.gnn_hidden_channels

    # ------------------------------------------------------------------ #
    # 1. Feature extraction                                                #
    # ------------------------------------------------------------------ #
    print(f"[Trainer] Extracting features for {len(entities):,} entities …")
    G = build_networkx_graph(entities, transactions)
    feat_matrix, node_ids, feature_names = compute_node_features(G, entities, transactions)

    data = build_graph_tensors(feat_matrix, node_ids, entities, transactions)
    labels = np.array([1 if e.is_suspicious else 0 for e in entities])
    n = len(entities)

    # ------------------------------------------------------------------ #
    # 2. Stratified train / val / test split                              #
    # ------------------------------------------------------------------ #
    idx = np.arange(n)
    idx_tv, idx_test = train_test_split(idx, test_size=0.15, stratify=labels, random_state=seed)
    idx_train, idx_val = train_test_split(
        idx_tv, test_size=0.15, stratify=labels[idx_tv], random_state=seed
    )

    def mask(indices: np.ndarray) -> torch.Tensor:
        m = torch.zeros(n, dtype=torch.bool)
        m[indices] = True
        return m

    train_mask = mask(idx_train)
    val_mask   = mask(idx_val)
    test_mask  = mask(idx_test)

    # ------------------------------------------------------------------ #
    # 3. GNN training                                                      #
    # ------------------------------------------------------------------ #
    print(f"[Trainer] Training GraphSAGE ({epochs} epochs, hidden={hidden}) …")
    n_feats = feat_matrix.shape[1]
    model = GraphSAGE(in_channels=n_feats, hidden_channels=hidden, out_channels=2)

    # Class weights: penalise false negatives (minority = suspicious)
    n_pos = int(labels[idx_train].sum())
    n_neg = len(idx_train) - n_pos
    class_weight = torch.tensor([1.0, n_neg / max(n_pos, 1)], dtype=torch.float32)

    optimizer  = torch.optim.Adam(model.parameters(), lr=settings.gnn_lr, weight_decay=5e-4)
    scheduler  = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_f1 = -1.0
    best_state: Optional[dict] = None

    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(data.x, data.edge_index)
        loss = F.cross_entropy(logits[train_mask], data.y[train_mask], weight=class_weight)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        if epoch % 10 == 0:
            model.eval()
            with torch.no_grad():
                val_prob = torch.softmax(model(data.x, data.edge_index), dim=-1)[:, 1].numpy()
                val_pred = (val_prob[val_mask.numpy()] > 0.5).astype(int)
                vm = compute_classification_metrics(labels[idx_val], val_pred, val_prob[idx_val])
                print(f"  ep {epoch:03d} | loss={loss.item():.4f} | val_f1={vm['f1']:.4f} "
                      f"| val_prec={vm['precision']:.4f}")
                if vm["f1"] > best_val_f1:
                    best_val_f1 = vm["f1"]
                    best_state = {k: v.clone() for k, v in model.state_dict().items()}

    if best_state:
        model.load_state_dict(best_state)
        print(f"  ✓ Loaded best checkpoint (val_f1={best_val_f1:.4f})")

    # ------------------------------------------------------------------ #
    # 4. Inference on all nodes                                           #
    # ------------------------------------------------------------------ #
    model.eval()
    with torch.no_grad():
        all_probs = torch.softmax(model(data.x, data.edge_index), dim=-1)[:, 1].numpy()
        embeddings = model.embed(data.x, data.edge_index).numpy()

    test_probs = all_probs[idx_test]
    test_preds = (test_probs > 0.5).astype(int)
    test_labels = labels[idx_test]

    gnn_metrics = compute_classification_metrics(test_labels, test_preds, test_probs)
    print(f"[Trainer] GNN test → {gnn_metrics}")

    # ------------------------------------------------------------------ #
    # 5. Baselines                                                         #
    # ------------------------------------------------------------------ #
    rule_probs = np.array([rule_based_score(feat_matrix[i], feature_names) for i in range(n)])
    rb_metrics = compute_classification_metrics(
        test_labels, (rule_probs[idx_test] > 0.5).astype(int), rule_probs[idx_test]
    )
    print(f"[Trainer] Rule-based → {rb_metrics}")

    lr_clf = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed, C=0.5)
    lr_clf.fit(feat_matrix[idx_train], labels[idx_train])
    lr_probs = lr_clf.predict_proba(feat_matrix[idx_test])[:, 1]
    lr_metrics = compute_classification_metrics(
        test_labels, (lr_probs > 0.5).astype(int), lr_probs
    )
    print(f"[Trainer] LogReg → {lr_metrics}")

    # ------------------------------------------------------------------ #
    # 6. Surrogate + SHAP                                                  #
    # ------------------------------------------------------------------ #
    print("[Trainer] Training SHAP surrogate …")
    combined = np.hstack([feat_matrix, embeddings])
    combined_names = feature_names + [f"emb_{i}" for i in range(embeddings.shape[1])]

    shap_matrix, _ = train_surrogate_and_shap(
        X_train=combined[idx_train],
        y_train=all_probs[idx_train],
        X_all=combined,
        feature_names=combined_names,
        seed=seed,
    )

    # Keep only the raw-feature SHAP values (drop embedding dims)
    node_shap: dict[str, dict[str, float]] = {
        eid: {fname: float(shap_matrix[i, j]) for j, fname in enumerate(feature_names)}
        for i, eid in enumerate(node_ids)
    }

    # ------------------------------------------------------------------ #
    # 7. Save model artifact                                               #
    # ------------------------------------------------------------------ #
    artifacts_dir = Path(settings.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), artifacts_dir / "gnn_model.pt")
    print("[Trainer] Saved model artifact.")

    # ------------------------------------------------------------------ #
    # 8. PR curve                                                          #
    # ------------------------------------------------------------------ #
    precision_curve, recall_curve, _ = precision_recall_curve(test_labels, test_probs)

    return {
        "metrics": {
            "gnn":                  gnn_metrics,
            "rule_based":           rb_metrics,
            "logistic_regression":  lr_metrics,
            "pr_curve": {
                "precision": precision_curve.tolist(),
                "recall":    recall_curve.tolist(),
            },
        },
        "node_scores":  {eid: float(all_probs[i]) for i, eid in enumerate(node_ids)},
        "node_shap":    node_shap,
        "feature_names": feature_names,
    }
