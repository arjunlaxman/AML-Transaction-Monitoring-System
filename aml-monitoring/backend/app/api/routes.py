"""FastAPI route definitions."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import Alert, Cluster, Entity, ModelRun, Transaction
from app.schemas.schemas import (
    AlertSchema,
    CaseDetailSchema,
    ClusterSchema,
    EntitySchema,
    GraphEdgeSchema,
    GraphNodeSchema,
    HealthResponse,
    JobResponse,
    MetricsSchema,
    SubgraphSchema,
    TransactionSchema,
)
from app.services.pipeline_service import run_generate, run_train

router = APIRouter()
settings = get_settings()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(db: Session = Depends(get_db)):
    """Service health check."""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return HealthResponse(status="ok", db_connected=db_ok)


# ---------------------------------------------------------------------------
# Data generation + training
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=JobResponse, tags=["pipeline"])
def generate(
    size: Literal["demo", "full"] = Query(default="demo", description="demo (~5K) or full (~150K)"),
    db: Session = Depends(get_db),
):
    """Generate synthetic transaction data and persist to database."""
    try:
        result = run_generate(db=db, mode=size, seed=settings.seed)
        return JobResponse(
            status="success",
            message=f"Generated {result['entities']:,} entities and {result['transactions']:,} transactions "
                    f"({result['suspicious_rate']:.1%} suspicious).",
            detail=result,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/train", response_model=JobResponse, tags=["pipeline"])
def train_model(
    mode: Literal["demo", "full"] = Query(default="demo"),
    db: Session = Depends(get_db),
):
    """Train GNN on stored data and create alerts."""
    try:
        result = run_train(db=db, mode=mode, seed=settings.seed)
        m = result["metrics"]
        return JobResponse(
            status="success",
            message=(
                f"Training complete — {result['alerts_created']} alerts created. "
                f"GNN F1: {m['gnn_f1']:.3f}, Precision: {m['gnn_precision']:.3f}, "
                f"Recall: {m['gnn_recall']:.3f}."
            ),
            detail=result,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@router.get("/alerts", tags=["alerts"])
def get_alerts(
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Paginated alerts ordered by risk score descending."""
    q = db.query(Alert).order_by(desc(Alert.score))
    if status:
        q = q.filter(Alert.status == status)
    total = q.count()
    items = [AlertSchema.from_orm(a) for a in q.offset(offset).limit(limit).all()]
    return {"total": total, "items": items}


# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------

@router.get("/clusters/top", tags=["clusters"])
def get_top_clusters(
    limit: int = Query(default=10, le=100),
    db: Session = Depends(get_db),
):
    """Top suspicious clusters by score."""
    clusters = (
        db.query(Cluster)
        .order_by(desc(Cluster.suspicion_score))
        .limit(limit)
        .all()
    )
    return [ClusterSchema.from_orm(c) for c in clusters]


# ---------------------------------------------------------------------------
# Case detail
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}", response_model=CaseDetailSchema, tags=["cases"])
def get_case(case_id: str, db: Session = Depends(get_db)):
    """Full case detail: alert + entity + cluster + transactions + SHAP explanation."""
    alert = db.query(Alert).filter(Alert.id == case_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    entity = db.query(Entity).filter(Entity.id == alert.entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found.")

    cluster = None
    if alert.cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == alert.cluster_id).first()

    txs = (
        db.query(Transaction)
        .filter(
            (Transaction.src_entity_id == entity.id) |
            (Transaction.dst_entity_id == entity.id)
        )
        .order_by(desc(Transaction.amount))
        .limit(25)
        .all()
    )

    return CaseDetailSchema(
        alert=AlertSchema.from_orm(alert),
        entity=EntitySchema.from_orm(entity),
        cluster=ClusterSchema.from_orm(cluster) if cluster else None,
        transactions=[TransactionSchema.from_orm(tx) for tx in txs],
        narrative=alert.narrative,
        shap_values=alert.shap_values,
    )


# ---------------------------------------------------------------------------
# Graph subgraph for visualization
# ---------------------------------------------------------------------------

@router.get("/graph/cluster/{cluster_id}", response_model=SubgraphSchema, tags=["graph"])
def get_cluster_subgraph(cluster_id: str, db: Session = Depends(get_db)):
    """Return subgraph data for a cluster — nodes and edges for the graph explorer."""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' not found.")

    member_ids = cluster.entity_ids
    entities = db.query(Entity).filter(Entity.id.in_(member_ids)).all()
    entity_id_set = {e.id for e in entities}

    txs = (
        db.query(Transaction)
        .filter(
            Transaction.src_entity_id.in_(entity_id_set) |
            Transaction.dst_entity_id.in_(entity_id_set)
        )
        .limit(300)
        .all()
    )

    nodes = [
        GraphNodeSchema(
            id=e.id, entity_type=e.entity_type, country=e.country,
            risk_score=e.risk_score, is_suspicious=e.is_suspicious,
            cluster_id=e.cluster_id,
        )
        for e in entities
    ]

    edges = [
        GraphEdgeSchema(
            source=tx.src_entity_id, target=tx.dst_entity_id,
            amount=tx.amount, channel=tx.channel,
            is_suspicious=tx.is_suspicious,
        )
        for tx in txs
        if tx.src_entity_id in entity_id_set and tx.dst_entity_id in entity_id_set
    ]

    return SubgraphSchema(nodes=nodes, edges=edges, cluster_id=cluster_id)


# ---------------------------------------------------------------------------
# Model metrics
# ---------------------------------------------------------------------------

@router.get("/metrics", response_model=MetricsSchema, tags=["metrics"])
def get_metrics(db: Session = Depends(get_db)):
    """Latest model run metrics."""
    run = (
        db.query(ModelRun)
        .filter(ModelRun.is_active == True)
        .order_by(desc(ModelRun.id))
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="No model run found. Run POST /train first.")

    m = run.metrics
    return MetricsSchema(
        mode=run.mode,
        gnn=m.get("gnn", {}),
        rule_based=m.get("rule_based", {}),
        logistic_regression=m.get("logistic_regression", {}),
        pr_curve=m.get("pr_curve"),
        created_at=run.created_at,
    )


# ---------------------------------------------------------------------------
# Overview stats
# ---------------------------------------------------------------------------

@router.get("/stats", tags=["system"])
def get_stats(db: Session = Depends(get_db)):
    """Aggregate stats for the dashboard overview."""
    total_entities    = db.query(Entity).count()
    total_transactions = db.query(Transaction).count()
    total_alerts      = db.query(Alert).count()
    open_alerts       = db.query(Alert).filter(Alert.status == "open").count()
    total_clusters    = db.query(Cluster).count()

    run = (
        db.query(ModelRun)
        .filter(ModelRun.is_active == True)
        .order_by(desc(ModelRun.id))
        .first()
    )
    m = run.metrics if run else {}

    return {
        "total_entities":    total_entities,
        "total_transactions": total_transactions,
        "total_alerts":      total_alerts,
        "open_alerts":       open_alerts,
        "total_clusters":    total_clusters,
        "gnn_precision":     m.get("gnn", {}).get("precision", 0.0),
        "gnn_recall":        m.get("gnn", {}).get("recall", 0.0),
        "gnn_f1":            m.get("gnn", {}).get("f1", 0.0),
        "gnn_roc_auc":       m.get("gnn", {}).get("roc_auc", 0.0),
        "has_model":         run is not None,
    }
