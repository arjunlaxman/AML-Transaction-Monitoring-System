"""Pydantic response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    version: str = "1.0.0"


class JobResponse(BaseModel):
    status: str
    message: str
    detail: Optional[dict] = None


class EntitySchema(BaseModel):
    id: str
    entity_type: str
    country: str
    is_suspicious: bool
    cluster_id: Optional[str]
    risk_score: float
    features: dict

    @classmethod
    def from_orm(cls, e: Any) -> "EntitySchema":
        return cls(
            id=e.id, entity_type=e.entity_type, country=e.country,
            is_suspicious=e.is_suspicious, cluster_id=e.cluster_id,
            risk_score=e.risk_score, features=e.features,
        )


class TransactionSchema(BaseModel):
    id: str
    src_entity_id: str
    dst_entity_id: str
    amount: float
    timestamp: datetime
    channel: str
    country: str
    risk_flags: list[str]
    is_suspicious: bool

    @classmethod
    def from_orm(cls, t: Any) -> "TransactionSchema":
        return cls(
            id=t.id, src_entity_id=t.src_entity_id, dst_entity_id=t.dst_entity_id,
            amount=t.amount, timestamp=t.timestamp, channel=t.channel,
            country=t.country, risk_flags=t.risk_flags,
            is_suspicious=t.is_suspicious,
        )


class AlertSchema(BaseModel):
    id: str
    entity_id: str
    cluster_id: Optional[str]
    score: float
    narrative: str
    shap_values: dict
    status: str
    created_at: datetime

    @classmethod
    def from_orm(cls, a: Any) -> "AlertSchema":
        return cls(
            id=a.id, entity_id=a.entity_id, cluster_id=a.cluster_id,
            score=a.score, narrative=a.narrative, shap_values=a.shap_values,
            status=a.status, created_at=a.created_at,
        )


class ClusterSchema(BaseModel):
    id: str
    entity_ids: list[str]
    size: int
    suspicion_score: float
    pattern_type: str
    created_at: datetime

    @classmethod
    def from_orm(cls, c: Any) -> "ClusterSchema":
        return cls(
            id=c.id, entity_ids=c.entity_ids, size=c.size,
            suspicion_score=c.suspicion_score, pattern_type=c.pattern_type,
            created_at=c.created_at,
        )


class GraphNodeSchema(BaseModel):
    id: str
    entity_type: str
    country: str
    risk_score: float
    is_suspicious: bool
    cluster_id: Optional[str]


class GraphEdgeSchema(BaseModel):
    source: str
    target: str
    amount: float
    channel: str
    is_suspicious: bool


class SubgraphSchema(BaseModel):
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
    cluster_id: str


class MetricsSchema(BaseModel):
    mode: str
    gnn: dict[str, float]
    rule_based: dict[str, float]
    logistic_regression: dict[str, float]
    pr_curve: Optional[dict[str, list[float]]]
    created_at: datetime


class CaseDetailSchema(BaseModel):
    alert: AlertSchema
    entity: EntitySchema
    cluster: Optional[ClusterSchema]
    transactions: list[TransactionSchema]
    narrative: str
    shap_values: dict[str, float]
