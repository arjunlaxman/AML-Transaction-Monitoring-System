"""Unit tests for the synthetic AML data generator."""

import numpy as np
import pytest

from app.ml.data_generator import (
    AMLDataGenerator,
    build_networkx_graph,
    compute_node_features,
)


class TestAMLDataGenerator:
    def setup_method(self):
        self.gen = AMLDataGenerator(seed=42)

    def test_demo_entity_count(self):
        entities, _ = self.gen.generate(mode="demo")
        assert len(entities) >= 500

    def test_demo_transaction_count(self):
        _, txs = self.gen.generate(mode="demo")
        assert len(txs) >= 1_000

    def test_suspicious_rate_in_range(self):
        entities, _ = self.gen.generate(mode="demo")
        rate = sum(1 for e in entities if e.is_suspicious) / len(entities)
        assert 0.01 <= rate <= 0.25, f"Suspicious rate {rate:.2%} out of expected range"

    def test_entity_ids_unique(self):
        entities, _ = self.gen.generate(mode="demo")
        ids = [e.id for e in entities]
        assert len(ids) == len(set(ids))

    def test_transaction_ids_unique(self):
        _, txs = self.gen.generate(mode="demo")
        ids = [tx.id for tx in txs]
        assert len(ids) == len(set(ids))

    def test_cluster_assignments_exist(self):
        entities, _ = self.gen.generate(mode="demo")
        with_cluster = [e for e in entities if e.cluster_id is not None]
        assert len(with_cluster) > 0

    def test_transaction_amounts_positive(self):
        _, txs = self.gen.generate(mode="demo")
        assert all(tx.amount > 0 for tx in txs)

    def test_deterministic_with_same_seed(self):
        gen1 = AMLDataGenerator(seed=99)
        gen2 = AMLDataGenerator(seed=99)
        e1, t1 = gen1.generate("demo")
        e2, t2 = gen2.generate("demo")
        assert len(e1) == len(e2)
        assert len(t1) == len(t2)
        assert e1[0].id == e2[0].id


class TestFeatureExtraction:
    def setup_method(self):
        gen = AMLDataGenerator(seed=42)
        self.entities, self.transactions = gen.generate(mode="demo")
        self.G = build_networkx_graph(self.entities, self.transactions)

    def test_feature_matrix_rows_match_entities(self):
        feat, node_ids, names = compute_node_features(
            self.G, self.entities, self.transactions
        )
        assert feat.shape[0] == len(self.entities)
        assert len(node_ids) == len(self.entities)

    def test_feature_names_match_columns(self):
        feat, _, names = compute_node_features(
            self.G, self.entities, self.transactions
        )
        assert feat.shape[1] == len(names)

    def test_no_nan_in_features(self):
        feat, _, _ = compute_node_features(
            self.G, self.entities, self.transactions
        )
        assert not np.isnan(feat).any(), "Feature matrix contains NaN"

    def test_no_inf_in_features(self):
        feat, _, _ = compute_node_features(
            self.G, self.entities, self.transactions
        )
        assert not np.isinf(feat).any(), "Feature matrix contains Inf"

    def test_features_have_18_dimensions(self):
        feat, _, names = compute_node_features(
            self.G, self.entities, self.transactions
        )
        assert feat.shape[1] == 18
        assert len(names) == 18
