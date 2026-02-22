#!/usr/bin/env python3
"""
Full run: 15,000 entities · ~150,000 transactions · 120 GNN epochs.

Expected time: 15–40 min on CPU · ~4 GB RAM.

Usage:
    docker compose exec api python scripts/full_run.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.database import Base
from app.db import models  # noqa: F401
from app.services.pipeline_service import run_generate, run_train


def main() -> None:
    settings = get_settings()
    print("=" * 60)
    print("AML Monitoring — Full Run (100K+ transactions)")
    print("Expected time: 15–40 min on CPU")
    print("=" * 60)

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        print("\n[1/2] Generating full dataset …")
        t0 = time.time()
        gen = run_generate(db=db, mode="full", seed=42)
        print(f"  ✓ {gen['entities']:,} entities · {gen['transactions']:,} transactions "
              f"({time.time() - t0:.1f}s)")

        print("\n[2/2] Training GNN (120 epochs) …")
        t1 = time.time()
        tr = run_train(db=db, mode="full", seed=42)
        m  = tr["metrics"]
        print(f"  ✓ {tr['alerts_created']} alerts · {tr['clusters_created']} clusters "
              f"({time.time() - t1:.1f}s)")
        print(f"\n  GNN   Precision {m['gnn_precision']:.3f} · Recall {m['gnn_recall']:.3f} "
              f"· F1 {m['gnn_f1']:.3f}")

    print(f"\n✅ Full run complete in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
