"""Tests for the storage layer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from aode import storage


@pytest.fixture()
def tmp_db(tmp_path: Path):
    db = tmp_path / "test.db"
    storage.init_db(db_path=db)
    return db


def test_init_db_creates_tables(tmp_db):
    import sqlite3
    conn = sqlite3.connect(str(tmp_db))
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    assert "raw_posts" in tables
    assert "opportunity_clusters" in tables
    assert "scored_opportunities" in tables
    assert "validations" in tables
    assert "built_mvps" in tables
    assert "cycle_log" in tables


def test_save_and_load_raw_posts(tmp_db):
    posts = [
        {
            "source": "reddit",
            "text": "manual data entry is painful",
            "metadata": {"id": "p1", "score": 100, "comments": 20},
        },
        {
            "source": "github",
            "text": "csv import is broken",
            "metadata": {"id": "p2", "score": 50, "comments": 10},
        },
    ]
    storage.save_raw_posts(posts, db_path=tmp_db)
    loaded = storage.load_raw_posts(db_path=tmp_db)
    assert len(loaded) == 2
    texts = {p["text"] for p in loaded}
    assert "manual data entry is painful" in texts
    assert "csv import is broken" in texts


def test_save_and_load_clusters(tmp_db):
    clusters = [
        {
            "problem_cluster": "Manual sync pain",
            "frequency": 5,
            "example_cases": ["I hate copying data manually"],
        }
    ]
    ids = storage.save_clusters(clusters, db_path=tmp_db)
    assert len(ids) == 1
    loaded = storage.load_clusters(db_path=tmp_db)
    assert len(loaded) == 1
    assert loaded[0]["problem_cluster"] == "Manual sync pain"


def test_save_and_load_scores(tmp_db):
    clusters = [
        {"problem_cluster": "Test Cluster", "frequency": 3, "example_cases": []}
    ]
    [cluster_id] = storage.save_clusters(clusters, db_path=tmp_db)
    scores = [
        {
            "cluster_id": cluster_id,
            "score": 0.75,
            "reasoning": "High pain, good feasibility",
            "risks": ["Risk A"],
        }
    ]
    ids = storage.save_scores(scores, db_path=tmp_db)
    assert len(ids) == 1

    top = storage.load_top_scores(top_n=3, db_path=tmp_db)
    assert len(top) == 1
    assert top[0]["score"] == pytest.approx(0.75)


def test_save_validation(tmp_db):
    clusters = [
        {"problem_cluster": "Pay pain", "frequency": 2, "example_cases": []}
    ]
    [cid] = storage.save_clusters(clusters, db_path=tmp_db)
    [sid] = storage.save_scores(
        [{"cluster_id": cid, "score": 0.6, "reasoning": "ok", "risks": []}],
        db_path=tmp_db,
    )
    vid = storage.save_validation(
        {
            "scored_id": sid,
            "landing_page": "# Headline",
            "outreach_message": "Hi there",
            "validation_score": 0.5,
            "confidence": 0.8,
        },
        db_path=tmp_db,
    )
    assert isinstance(vid, int)
    assert vid >= 1


def test_save_mvp(tmp_db):
    mvp_id = storage.save_mvp(
        {
            "validation_id": None,
            "name": "test-mvp",
            "readme": "# Test",
            "code": {"main.py": "print('hello')"},
        },
        db_path=tmp_db,
    )
    assert isinstance(mvp_id, int)


def test_cycle_log(tmp_db):
    storage.log_cycle(1, "ingest", "Fetched 50 posts", db_path=tmp_db)
    import sqlite3
    conn = sqlite3.connect(str(tmp_db))
    rows = conn.execute("SELECT * FROM cycle_log").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][2] == "ingest"
