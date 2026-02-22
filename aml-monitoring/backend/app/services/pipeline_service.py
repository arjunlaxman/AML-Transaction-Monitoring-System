"""
Orchestration service: data generation → model training → DB persistence.

Keeps all heavy ML work out of the FastAPI request handlers.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Alert, Cluster, Entity, ModelRun, Transaction
from app.ml.data_generator import AMLDataGenerator, EntityRecord, TransactionRecord
from app.ml.explainer import generate_narrative
from app.ml.trainer import train


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def run_generate(db: Session, mode: str = "demo", seed: int = 42) -> dict:
    """
    Generate synthetic AML dataset and persist to database.
    Clears all existing data before inserting.
    """
    gen = AMLDataGenerator(seed=seed)
    entities, transactions = gen.generate(mode=mode)

    # Clear previous data in dependency order
    db.query(Alert).delete()
    db.query(Cluster).delete()
    db.query(Transaction).delete()
    db.query(Entity).delete()
    db.commit()

    # Bulk insert entities
    for e in entities:
        db.add(Entity(
            id=e.id,
            entity_type=e.entity_type,
            country=e.country,
            is_suspicious=e.is_suspicious,
            cluster_id=e.cluster_id,
            risk_score=0.0,
            features_json="{}",
        ))

    # Bulk insert transactions
    for tx in transactions:
        db.add(Transaction(
            id=tx.id,
            src_entity_id=tx.src,
            dst_entity_id=tx.dst,
            amount=tx.amount,
            timestamp=tx.timestamp,
            channel=tx.channel,
            country=tx.country,
            risk_flags_json=json.dumps(tx.risk_flags),  # consistent field name
            is_suspicious=tx.is_suspicious,
        ))

    db.commit()
    suspicious_count = sum(1 for e in entities if e.is_suspicious)

    return {
        "entities": len(entities),
        "transactions": len(transactions),
        "suspicious_entities": suspicious_count,
        "suspicious_rate": round(suspicious_count / max(len(entities), 1), 4),
    }


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def run_train(db: Session, mode: str = "demo", seed: int = 42) -> dict:
    """
    Load data from DB, train model, persist alerts / clusters / metrics.
    """
    db_entities = db.query(Entity).all()
    db_transactions = db.query(Transaction).all()

    if not db_entities:
        raise ValueError("No entities in database. Call POST /generate first.")

    # Reconstruct in-memory records
    entities = [
        EntityRecord(
            id=e.id, entity_type=e.entity_type, country=e.country,
            is_suspicious=e.is_suspicious, cluster_id=e.cluster_id,
        )
        for e in db_entities
    ]
    transactions = [
        TransactionRecord(
            id=tx.id, src=tx.src_entity_id, dst=tx.dst_entity_id,
            amount=tx.amount, timestamp=tx.timestamp,
            channel=tx.channel, country=tx.country,
            risk_flags=tx.risk_flags,  # uses the @property
            is_suspicious=tx.is_suspicious,
        )
        for tx in db_transactions
    ]

    # Train
    results = train(entities, transactions, mode=mode, seed=seed)
    node_scores: dict[str, float] = results["node_scores"]
    node_shap: dict[str, dict[str, float]] = results["node_shap"]
    metrics: dict = results["metrics"]

    # Update entity risk scores and feature attribution in DB
    for db_e in db_entities:
        db_e.risk_score = node_scores.get(db_e.id, 0.0)
        db_e.features_json = json.dumps(node_shap.get(db_e.id, {}))
    db.commit()

    # Build cluster groups from cluster_id labels
    db.query(Alert).delete()
    db.query(Cluster).delete()
    db.commit()

    cluster_map: dict[str, list[EntityRecord]] = {}
    for e in entities:
        if e.cluster_id:
            cluster_map.setdefault(e.cluster_id, []).append(e)

    def _pattern(cid: str) -> str:
        if "SMURF" in cid: return "smurfing"
        if "LAYER" in cid: return "layering"
        if "CIRC"  in cid: return "circular"
        return "mixed"

    for cid, members in cluster_map.items():
        scores = [node_scores.get(m.id, 0.0) for m in members]
        db.add(Cluster(
            id=cid,
            entity_ids_json=json.dumps([m.id for m in members]),
            size=len(members),
            suspicion_score=float(max(scores)),
            pattern_type=_pattern(cid),
        ))
    db.commit()

    # Create alerts for entities above threshold
    threshold = 0.50
    alerts_created = 0

    for db_e in db_entities:
        score = db_e.risk_score
        if score < threshold:
            continue

        shap_vals   = node_shap.get(db_e.id, {})
        cid         = db_e.cluster_id
        c_size      = len(cluster_map.get(cid or "", []))
        pattern     = _pattern(cid) if cid else "mixed"

        narrative = generate_narrative(
            entity_id=db_e.id,
            entity_type=db_e.entity_type,
            country=db_e.country,
            risk_score=score,
            cluster_id=cid,
            cluster_size=c_size,
            pattern_type=pattern,
            shap_values=shap_vals,
        )

        db.add(Alert(
            id=str(uuid.uuid4())[:8].upper(),
            entity_id=db_e.id,
            cluster_id=cid,
            score=score,
            narrative=narrative,
            shap_values_json=json.dumps(shap_vals),
            status="open",
            created_at=datetime.utcnow(),
        ))
        alerts_created += 1

    # Save model run record (deactivate previous)
    db.query(ModelRun).filter(ModelRun.is_active == True).update({"is_active": False})
    db.add(ModelRun(
        mode=mode,
        metrics_json=json.dumps(metrics),
        is_active=True,
        created_at=datetime.utcnow(),
    ))
    db.commit()

    return {
        "alerts_created": alerts_created,
        "clusters_created": len(cluster_map),
        "metrics": {
            "gnn_f1":        metrics["gnn"].get("f1", 0.0),
            "gnn_precision": metrics["gnn"].get("precision", 0.0),
            "gnn_recall":    metrics["gnn"].get("recall", 0.0),
        },
    }
