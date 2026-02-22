"""SQLAlchemy ORM models for AML monitoring system."""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Entity(Base):
    """A financial entity: individual, business, mule, or shell company."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    country: Mapped[str] = mapped_column(String(8))
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    features_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def features(self) -> dict:
        return json.loads(self.features_json)


class Transaction(Base):
    """A financial transaction between two entities."""

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    src_entity_id: Mapped[str] = mapped_column(String(32), index=True)
    dst_entity_id: Mapped[str] = mapped_column(String(32), index=True)
    amount: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    channel: Mapped[str] = mapped_column(String(32))
    country: Mapped[str] = mapped_column(String(8))
    # Stored as JSON list string — access via .risk_flags property
    risk_flags_json: Mapped[str] = mapped_column(Text, default="[]")
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def risk_flags(self) -> list[str]:
        return json.loads(self.risk_flags_json)


class Cluster(Base):
    """A suspicious entity cluster detected by the GNN."""

    __tablename__ = "clusters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_ids_json: Mapped[str] = mapped_column(Text)
    size: Mapped[int] = mapped_column(Integer)
    suspicion_score: Mapped[float] = mapped_column(Float)
    pattern_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def entity_ids(self) -> list[str]:
        return json.loads(self.entity_ids_json)


class Alert(Base):
    """An alert raised for a suspicious entity or cluster."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(32), index=True)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    score: Mapped[float] = mapped_column(Float)
    narrative: Mapped[str] = mapped_column(Text)
    shap_values_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def shap_values(self) -> dict:
        return json.loads(self.shap_values_json)


class ModelRun(Base):
    """A record of a model training run and its metrics."""

    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str] = mapped_column(String(16))
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def metrics(self) -> dict:
        return json.loads(self.metrics_json)
