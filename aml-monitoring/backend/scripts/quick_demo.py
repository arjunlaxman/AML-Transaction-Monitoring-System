#!/usr/bin/env python3
"""
Quick demo: generate data + train model in one shot.

Usage (inside container):
    python scripts/quick_demo.py

Usage (local venv):
    cd backend && python scripts/quick_demo.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.database import Base
from app.db import models  # noqa: F401 — registers all ORM models
from app.services.pipeline_service import run_generate, run_train


def main() -> None:
    settings = get_settings()
    print("=" * 60)
    print("AML Monitoring System — Quick Demo")
    print("=" * 60)

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        print("\n[1/2] Generating demo dataset …")
        t0 = time.time()
        gen = run_generate(db=db, mode="demo", seed=42)
        print(f"  ✓ {gen['entities']:,} entities · {gen['transactions']:,} transactions "
              f"· {gen['suspicious_rate']:.1%} suspicious  ({time.time() - t0:.1f}s)")

        print("\n[2/2] Training GNN (60 epochs) …")
        t1 = time.time()
        tr = run_train(db=db, mode="demo", seed=42)
        m  = tr["metrics"]
        print(f"  ✓ {tr['alerts_created']} alerts · {tr['clusters_created']} clusters  "
              f"({time.time() - t1:.1f}s)")
        print(f"\n  GNN   Precision {m['gnn_precision']:.3f} · Recall {m['gnn_recall']:.3f} "
              f"· F1 {m['gnn_f1']:.3f}")

    print(f"\n✅ Total time: {time.time() - t0:.1f}s")
    print("   Open http://localhost:5173 to explore the dashboard.\n")


if __name__ == "__main__":
    main()
