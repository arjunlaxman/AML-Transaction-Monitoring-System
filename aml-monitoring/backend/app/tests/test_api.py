"""API endpoint integration tests."""

import pytest


class TestHealth:
    def test_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestGenerate:
    def test_demo_mode_succeeds(self, client):
        r = client.post("/generate?size=demo")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "success"
        assert d["detail"]["entities"] > 0
        assert d["detail"]["transactions"] > 0

    def test_invalid_size_rejected(self, client):
        r = client.post("/generate?size=huge")
        assert r.status_code == 422

    def test_suspicious_rate_reported(self, client):
        r = client.post("/generate?size=demo")
        assert r.status_code == 200
        assert "suspicious_rate" in r.json()["detail"]


class TestStats:
    def test_stats_empty_db(self, client):
        r = client.get("/stats")
        assert r.status_code == 200
        assert "total_entities" in r.json()

    def test_stats_after_generate(self, client):
        client.post("/generate?size=demo")
        r = client.get("/stats")
        assert r.status_code == 200
        assert r.json()["total_entities"] > 0
        assert r.json()["total_transactions"] > 0


class TestAlerts:
    def test_alerts_empty_initially(self, client):
        r = client.get("/alerts")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    def test_alerts_pagination(self, client):
        r = client.get("/alerts?limit=5&offset=0")
        assert r.status_code == 200


class TestClusters:
    def test_clusters_empty_list(self, client):
        r = client.get("/clusters/top")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_clusters_limit_respected(self, client):
        r = client.get("/clusters/top?limit=3")
        assert r.status_code == 200
        assert len(r.json()) <= 3


class TestMetrics:
    def test_metrics_404_before_training(self, client):
        r = client.get("/metrics")
        assert r.status_code == 404


class TestCases:
    def test_case_not_found(self, client):
        r = client.get("/cases/NOTEXIST")
        assert r.status_code == 404


class TestGraph:
    def test_graph_cluster_not_found(self, client):
        r = client.get("/graph/cluster/FAKE_CLUSTER")
        assert r.status_code == 404
