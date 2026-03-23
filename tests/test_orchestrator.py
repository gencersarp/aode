"""Integration test for the full Orchestrator cycle."""

from __future__ import annotations

import pytest
from pathlib import Path

from aode.orchestrator import Orchestrator
from aode import storage


@pytest.fixture()
def tmp_db(tmp_path: Path):
    db = tmp_path / "test_orch.db"
    storage.init_db(db_path=db)
    return db


def test_single_cycle_completes(tmp_db):
    orch = Orchestrator(top_n=2, max_posts=20, use_sklearn=False, n_clusters=4, db_path=tmp_db)
    result = orch.run_cycle(cycle=1)

    assert result["cycle"] == 1
    assert result["posts_fetched"] > 0
    assert result["clusters_found"] > 0
    assert isinstance(result["top_opportunities"], list)
    assert isinstance(result["validations"], list)
    assert "reflection" in result


def test_top_opportunities_have_scores(tmp_db):
    orch = Orchestrator(top_n=3, max_posts=20, use_sklearn=False, db_path=tmp_db)
    result = orch.run_cycle(cycle=1)
    for opp in result["top_opportunities"]:
        assert "score" in opp
        assert 0.0 <= opp["score"] <= 1.0


def test_mvp_built(tmp_db):
    orch = Orchestrator(top_n=1, max_posts=20, use_sklearn=False, db_path=tmp_db)
    result = orch.run_cycle(cycle=1)
    mvp = result.get("mvp", {})
    assert "name" in mvp
    assert "readme" in mvp
    assert "code" in mvp


def test_multi_cycle_run(tmp_db):
    orch = Orchestrator(top_n=1, max_posts=10, use_sklearn=False, db_path=tmp_db)
    results = orch.run(cycles=2)
    assert len(results) == 2
    assert results[0]["cycle"] == 1
    assert results[1]["cycle"] == 2


def test_data_persisted_to_db(tmp_db):
    orch = Orchestrator(top_n=1, max_posts=20, use_sklearn=False, db_path=tmp_db)
    orch.run_cycle(cycle=1)

    posts = storage.load_raw_posts(db_path=tmp_db)
    clusters = storage.load_clusters(db_path=tmp_db)
    top = storage.load_top_scores(db_path=tmp_db)

    assert len(posts) > 0
    assert len(clusters) > 0
    assert len(top) > 0
