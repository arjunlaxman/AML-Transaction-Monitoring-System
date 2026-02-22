"""
Synthetic AML transaction network generator.

Creates realistic multi-hop transaction networks with laundering patterns:
  - Smurfing: many small deposits into mules, then consolidated
  - Layering: multi-hop chains with splitting/merging across jurisdictions
  - Circular flows: A→B→C→A cycles to obscure fund origin

Design notes:
  - Class imbalance: ~5% suspicious (realistic for AML)
  - Feature computation uses O(1) lookups throughout (no nested linear scans)
  - Deterministic with seeded RNG for reproducibility
"""

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import networkx as nx
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COUNTRIES = [
    "US", "GB", "DE", "FR", "NL", "CH", "SG", "HK", "AE", "PA",
    "VG", "KY", "LU", "MT", "CY", "LI", "MH", "BZ", "WS", "SC",
]
HIGH_RISK_COUNTRIES = {"PA", "VG", "KY", "MH", "BZ", "WS", "SC", "AE", "LI"}
NORMAL_COUNTRIES = [c for c in COUNTRIES if c not in HIGH_RISK_COUNTRIES]

CHANNELS = ["wire", "cash", "crypto", "ach", "check", "swift"]
HIGH_RISK_CHANNELS = {"cash", "crypto"}

ENTITY_TYPES = ["individual", "business"]
SUSPICIOUS_TYPES = ["mule", "shell"]

BASE_DATE = datetime(2023, 1, 1)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EntityRecord:
    id: str
    entity_type: str
    country: str
    is_suspicious: bool
    cluster_id: Optional[str] = None
    risk_score: float = 0.0
    features: dict = field(default_factory=dict)


@dataclass
class TransactionRecord:
    id: str
    src: str
    dst: str
    amount: float
    timestamp: datetime
    channel: str
    country: str
    risk_flags: list[str] = field(default_factory=list)
    is_suspicious: bool = False


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class AMLDataGenerator:
    """Generates synthetic AML transaction datasets with realistic laundering patterns."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self._reset_rng()

    def _reset_rng(self) -> None:
        np.random.seed(self.seed)
        random.seed(self.seed)

    def generate(
        self,
        mode: str = "demo",
    ) -> tuple[list[EntityRecord], list[TransactionRecord]]:
        """Generate entities and transactions for the given mode.

        Args:
            mode: "demo" (~5K transactions) or "full" (~150K transactions)

        Returns:
            Tuple of (entities, transactions)
        """
        self._reset_rng()

        if mode == "demo":
            return self._generate_dataset(
                n_entities=1_000,
                n_normal_tx=4_000,
                n_smurfing_clusters=6,
                n_layering_chains=10,
                n_circular_clusters=5,
            )
        else:
            return self._generate_dataset(
                n_entities=15_000,
                n_normal_tx=120_000,
                n_smurfing_clusters=90,
                n_layering_chains=140,
                n_circular_clusters=70,
            )

    # ------------------------------------------------------------------
    # Private dataset assembly
    # ------------------------------------------------------------------

    def _generate_dataset(
        self,
        n_entities: int,
        n_normal_tx: int,
        n_smurfing_clusters: int,
        n_layering_chains: int,
        n_circular_clusters: int,
    ) -> tuple[list[EntityRecord], list[TransactionRecord]]:
        entities = self._create_entities(n_entities)
        # O(1) lookup map — used throughout to avoid linear scans
        entity_map: dict[str, EntityRecord] = {e.id: e for e in entities}
        normal_ids = [e.id for e in entities if not e.is_suspicious]
        susp_ids = [e.id for e in entities if e.is_suspicious]

        transactions: list[TransactionRecord] = []
        tx_offset = 0

        # Normal background transactions
        for i in range(n_normal_tx):
            src, dst = random.sample(normal_ids, 2)
            transactions.append(self._make_tx(src, dst, False, tx_offset + i))
        tx_offset += n_normal_tx

        # Smurfing patterns
        for k in range(n_smurfing_clusters):
            cluster_id = f"CLU_SMURF_{k:04d}"
            new_txs, members = self._generate_smurfing(susp_ids, normal_ids, tx_offset)
            transactions.extend(new_txs)
            tx_offset += len(new_txs)
            for mid in members:
                if mid in entity_map:
                    entity_map[mid].cluster_id = cluster_id
                    entity_map[mid].is_suspicious = True

        # Layering patterns
        for k in range(n_layering_chains):
            cluster_id = f"CLU_LAYER_{k:04d}"
            new_txs, members = self._generate_layering(susp_ids, normal_ids, tx_offset)
            transactions.extend(new_txs)
            tx_offset += len(new_txs)
            for mid in members:
                if mid in entity_map:
                    entity_map[mid].cluster_id = cluster_id
                    entity_map[mid].is_suspicious = True

        # Circular flow patterns
        for k in range(n_circular_clusters):
            cluster_id = f"CLU_CIRC_{k:04d}"
            new_txs, members = self._generate_circular(susp_ids, normal_ids, tx_offset)
            transactions.extend(new_txs)
            tx_offset += len(new_txs)
            for mid in members:
                if mid in entity_map:
                    entity_map[mid].cluster_id = cluster_id
                    entity_map[mid].is_suspicious = True

        return list(entity_map.values()), transactions

    def _create_entities(self, n: int) -> list[EntityRecord]:
        """Create n entities with ~5% suspicious rate."""
        n_suspicious = max(10, int(n * 0.05))
        entities = []
        for i in range(n):
            is_susp = i < n_suspicious
            etype = random.choice(SUSPICIOUS_TYPES) if is_susp else random.choice(ENTITY_TYPES)
            country = random.choice(list(HIGH_RISK_COUNTRIES)) if is_susp else random.choice(NORMAL_COUNTRIES)
            entities.append(EntityRecord(
                id=f"E{i:07d}",
                entity_type=etype,
                country=country,
                is_suspicious=is_susp,
            ))
        return entities

    def _make_tx(
        self,
        src: str,
        dst: str,
        is_suspicious: bool,
        tx_idx: int,
        amount: Optional[float] = None,
        channel: Optional[str] = None,
        country: Optional[str] = None,
        days_spread: int = 365,
    ) -> TransactionRecord:
        """Build one TransactionRecord with realistic attributes."""
        if amount is None:
            amount = float(np.random.lognormal(mean=7.5, sigma=1.8))
        if channel is None:
            channel = random.choice(list(HIGH_RISK_CHANNELS)) if is_suspicious else random.choice(CHANNELS)
        if country is None:
            country = random.choice(list(HIGH_RISK_COUNTRIES)) if is_suspicious else random.choice(NORMAL_COUNTRIES)

        ts = BASE_DATE + timedelta(
            days=random.randint(0, days_spread),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        flags: list[str] = []
        if 9_000 <= amount < 10_000:
            flags.append("structuring_threshold")
        if channel in HIGH_RISK_CHANNELS:
            flags.append("high_risk_channel")
        if country in HIGH_RISK_COUNTRIES:
            flags.append("high_risk_country")
        if amount > 100_000:
            flags.append("large_value")

        return TransactionRecord(
            id=f"T{tx_idx:010d}",
            src=src,
            dst=dst,
            amount=round(amount, 2),
            timestamp=ts,
            channel=channel,
            country=country,
            risk_flags=flags,
            is_suspicious=is_suspicious,
        )

    def _generate_smurfing(
        self,
        susp_ids: list[str],
        normal_ids: list[str],
        tx_offset: int,
    ) -> tuple[list[TransactionRecord], list[str]]:
        """
        Smurfing: N smurfs each send small amounts (<$10K) to a central mule,
        which then consolidates and forwards to a beneficiary.
        """
        n_smurfs = random.randint(5, 14)
        smurfs = random.sample(normal_ids, min(n_smurfs, len(normal_ids)))
        mule = random.choice(susp_ids) if susp_ids else random.choice(normal_ids)
        beneficiary = random.choice(susp_ids) if susp_ids else random.choice(normal_ids)

        txs: list[TransactionRecord] = []
        total = 0.0
        base_day = random.randint(0, 300)

        for i, smurf in enumerate(smurfs):
            # Each smurf sends just below the $10K reporting threshold
            amount = round(random.uniform(2_500, 9_490), 2)
            total += amount
            txs.append(self._make_tx(
                smurf, mule, True, tx_offset + i,
                amount=amount, channel="cash",
                country=random.choice(NORMAL_COUNTRIES),
                days_spread=7,
            ))

        # Consolidation: slight fee taken
        txs.append(self._make_tx(
            mule, beneficiary, True,
            tx_offset + len(smurfs),
            amount=round(total * 0.93, 2),
            channel=random.choice(["wire", "crypto", "swift"]),
            country=random.choice(list(HIGH_RISK_COUNTRIES)),
        ))

        return txs, smurfs + [mule, beneficiary]

    def _generate_layering(
        self,
        susp_ids: list[str],
        normal_ids: list[str],
        tx_offset: int,
    ) -> tuple[list[TransactionRecord], list[str]]:
        """
        Layering: funds flow through a chain of entities across jurisdictions,
        with slight amounts taken at each hop to obscure the trail.
        """
        chain_length = random.randint(4, 9)
        chain: list[str] = []
        for _ in range(chain_length):
            if random.random() < 0.55 and susp_ids:
                chain.append(random.choice(susp_ids))
            else:
                chain.append(random.choice(normal_ids))

        amount = round(random.uniform(50_000, 800_000), 2)
        txs: list[TransactionRecord] = []

        for i in range(len(chain) - 1):
            # Slight shrinkage at each hop (fees / layering cost)
            hop_amount = round(amount * random.uniform(0.88, 0.97), 2)
            txs.append(self._make_tx(
                chain[i], chain[i + 1], True,
                tx_offset + i,
                amount=hop_amount,
                country=random.choice(list(HIGH_RISK_COUNTRIES)),
                channel=random.choice(["wire", "swift", "crypto"]),
                days_spread=90,
            ))
            amount = hop_amount

        return txs, chain

    def _generate_circular(
        self,
        susp_ids: list[str],
        normal_ids: list[str],
        tx_offset: int,
    ) -> tuple[list[TransactionRecord], list[str]]:
        """Circular flow: A→B→C→...→A. Funds cycle to create the illusion of legitimate activity."""
        cycle_size = random.randint(3, 7)
        pool = susp_ids if len(susp_ids) >= cycle_size else normal_ids
        cycle = random.sample(pool, min(cycle_size, len(pool)))

        amount = round(random.uniform(15_000, 300_000), 2)
        txs: list[TransactionRecord] = []

        for i in range(len(cycle)):
            src = cycle[i]
            dst = cycle[(i + 1) % len(cycle)]
            txs.append(self._make_tx(
                src, dst, True,
                tx_offset + i,
                amount=round(amount * random.uniform(0.92, 1.08), 2),
                channel=random.choice(["wire", "crypto", "swift"]),
                country=random.choice(list(HIGH_RISK_COUNTRIES)),
                days_spread=30,
            ))

        return txs, cycle


# ---------------------------------------------------------------------------
# Graph construction + Feature extraction
# ---------------------------------------------------------------------------

def build_networkx_graph(
    entities: list[EntityRecord],
    transactions: list[TransactionRecord],
) -> nx.DiGraph:
    """Build a directed NetworkX graph from entities (nodes) and transactions (edges)."""
    G = nx.DiGraph()
    for e in entities:
        G.add_node(e.id, entity_type=e.entity_type, country=e.country,
                   is_suspicious=e.is_suspicious, cluster_id=e.cluster_id)
    for tx in transactions:
        G.add_edge(tx.src, tx.dst,
                   tx_id=tx.id, amount=tx.amount, channel=tx.channel,
                   country=tx.country, is_suspicious=tx.is_suspicious)
    return G


def compute_node_features(
    G: nx.DiGraph,
    entities: list[EntityRecord],
    transactions: list[TransactionRecord],
) -> tuple["np.ndarray", list[str], list[str]]:
    """
    Compute an 18-dimensional feature vector per entity node.

    All aggregations are computed via O(1) dict lookups after a single
    pass through the transaction list — no nested linear scans.

    Returns:
        feature_matrix: shape (n_entities, 18)
        node_ids:        entity IDs in row order
        feature_names:   names for each of the 18 features
    """
    # Build entity lookup once — O(1) per access
    entity_lookup: dict[str, EntityRecord] = {e.id: e for e in entities}
    eids = [e.id for e in entities]

    # Pre-allocate accumulators (single pass through transactions)
    out_amounts: dict[str, list[float]] = {eid: [] for eid in eids}
    in_amounts:  dict[str, list[float]] = {eid: [] for eid in eids}
    out_countries: dict[str, set[str]] = {eid: set() for eid in eids}
    in_countries:  dict[str, set[str]] = {eid: set() for eid in eids}
    out_channels:  dict[str, set[str]] = {eid: set() for eid in eids}
    in_channels:   dict[str, set[str]] = {eid: set() for eid in eids}
    timestamps:    dict[str, list[datetime]] = {eid: [] for eid in eids}
    counterparts:  dict[str, set[str]] = {eid: set() for eid in eids}
    flag_counts:   dict[str, int] = {eid: 0 for eid in eids}

    for tx in transactions:
        s, d = tx.src, tx.dst
        if s in out_amounts:
            out_amounts[s].append(tx.amount)
            out_countries[s].add(tx.country)
            out_channels[s].add(tx.channel)
            timestamps[s].append(tx.timestamp)
            counterparts[s].add(d)
            flag_counts[s] += len(tx.risk_flags)
        if d in in_amounts:
            in_amounts[d].append(tx.amount)
            in_countries[d].add(tx.country)
            in_channels[d].add(tx.channel)
            timestamps[d].append(tx.timestamp)
            counterparts[d].add(s)
            flag_counts[d] += len(tx.risk_flags)

    # Centrality (degree-based approximation for large graphs)
    n = len(G.nodes)
    if n <= 8_000:
        deg_cent = nx.degree_centrality(G)
        in_deg_cent = nx.in_degree_centrality(G)
    else:
        max_d = max((d for _, d in G.degree()), default=1)
        max_id = max((d for _, d in G.in_degree()), default=1)
        deg_cent = {nd: d / max_d for nd, d in G.degree()}
        in_deg_cent = {nd: d / max_id for nd, d in G.in_degree()}

    etype_enc = {"individual": 0, "business": 1, "mule": 2, "shell": 3}

    feature_names = [
        "total_sent", "total_received", "num_sent", "num_received",
        "avg_sent", "avg_received", "max_sent", "max_received",
        "in_out_ratio", "geo_diversity", "channel_diversity",
        "unique_counterparties", "burstiness", "risk_flag_count",
        "degree_centrality", "in_degree_centrality",
        "entity_type_enc", "country_risk",
    ]

    rows: list[list[float]] = []
    for eid in eids:
        oa = out_amounts[eid]
        ia = in_amounts[eid]
        e = entity_lookup[eid]  # O(1) — dict lookup

        total_s  = sum(oa)
        total_r  = sum(ia)
        n_s      = len(oa)
        n_r      = len(ia)
        avg_s    = float(np.mean(oa)) if oa else 0.0
        avg_r    = float(np.mean(ia)) if ia else 0.0
        max_s    = float(max(oa)) if oa else 0.0
        max_r    = float(max(ia)) if ia else 0.0
        ratio    = total_r / (total_s + 1e-9)
        geo      = len(out_countries[eid] | in_countries[eid])
        ch_div   = len(out_channels[eid] | in_channels[eid])
        cp       = len(counterparts[eid])
        crisk    = 1.0 if e.country in HIGH_RISK_COUNTRIES else 0.0

        # Burstiness: coefficient of variation of inter-transaction intervals
        ts_list = sorted(timestamps[eid])
        if len(ts_list) >= 3:
            deltas = np.diff([(t - ts_list[0]).total_seconds() for t in ts_list])
            burstiness = float(np.std(deltas) / (np.mean(deltas) + 1e-9))
        else:
            burstiness = 0.0

        rows.append([
            np.log1p(total_s), np.log1p(total_r),
            np.log1p(n_s),     np.log1p(n_r),
            np.log1p(avg_s),   np.log1p(avg_r),
            np.log1p(max_s),   np.log1p(max_r),
            np.log1p(ratio),
            float(geo), float(ch_div), np.log1p(cp),
            min(burstiness, 10.0),
            np.log1p(flag_counts[eid]),
            deg_cent.get(eid, 0.0),
            in_deg_cent.get(eid, 0.0),
            float(etype_enc.get(e.entity_type, 0)),
            crisk,
        ])

    feat_matrix = np.array(rows, dtype=np.float32)
    feat_matrix = np.nan_to_num(feat_matrix, nan=0.0, posinf=10.0, neginf=0.0)
    return feat_matrix, eids, feature_names
