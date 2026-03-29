"""Storage layer for AODE — SQLite-backed persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "aode.db"


def _get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Create all required tables if they don't exist."""
    conn = _get_connection(db_path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_posts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source      TEXT NOT NULL,
                external_id TEXT,
                text        TEXT NOT NULL,
                metadata    TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS opportunity_clusters (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_cluster TEXT NOT NULL,
                frequency       INTEGER NOT NULL DEFAULT 0,
                example_cases   TEXT NOT NULL DEFAULT '[]',
                created_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scored_opportunities (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id     INTEGER REFERENCES opportunity_clusters(id),
                score          REAL NOT NULL,
                reasoning      TEXT NOT NULL,
                risks          TEXT NOT NULL DEFAULT '[]',
                created_at     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS validations (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                scored_id        INTEGER REFERENCES scored_opportunities(id),
                landing_page     TEXT NOT NULL DEFAULT '',
                outreach_message TEXT NOT NULL DEFAULT '',
                validation_score REAL NOT NULL DEFAULT 0.0,
                confidence       REAL NOT NULL DEFAULT 0.0,
                created_at       TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS built_mvps (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                validation_id INTEGER REFERENCES validations(id),
                name        TEXT NOT NULL,
                readme      TEXT NOT NULL DEFAULT '',
                code        TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cycle_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle      INTEGER NOT NULL,
                phase      TEXT NOT NULL,
                summary    TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
    conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- raw posts ----------

def save_raw_posts(posts: list[dict[str, Any]], db_path: Path = DB_PATH) -> None:
    conn = _get_connection(db_path)
    with conn:
        conn.executemany(
            """
            INSERT INTO raw_posts (source, external_id, text, metadata, created_at)
            VALUES (:source, :external_id, :text, :metadata, :created_at)
            """,
            [
                {
                    "source": p["source"],
                    "external_id": p.get("metadata", {}).get("id"),
                    "text": p["text"],
                    "metadata": json.dumps(p.get("metadata", {})),
                    "created_at": _now(),
                }
                for p in posts
            ],
        )
    conn.close()


def load_raw_posts(limit: int = 500, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    conn = _get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM raw_posts ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "source": r["source"],
            "text": r["text"],
            "metadata": json.loads(r["metadata"]),
        }
        for r in rows
    ]


# ---------- clusters ----------

def save_clusters(
    clusters: list[dict[str, Any]], db_path: Path = DB_PATH
) -> list[int]:
    conn = _get_connection(db_path)
    ids: list[int] = []
    with conn:
        for c in clusters:
            cur = conn.execute(
                """
                INSERT INTO opportunity_clusters
                    (problem_cluster, frequency, example_cases, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    c["problem_cluster"],
                    c["frequency"],
                    json.dumps(c.get("example_cases", [])),
                    _now(),
                ),
            )
            ids.append(cur.lastrowid)
    conn.close()
    return ids


def load_clusters(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    conn = _get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM opportunity_clusters ORDER BY frequency DESC"
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "problem_cluster": r["problem_cluster"],
            "frequency": r["frequency"],
            "example_cases": json.loads(r["example_cases"]),
        }
        for r in rows
    ]


# ---------- scored opportunities ----------

def save_scores(
    scores: list[dict[str, Any]], db_path: Path = DB_PATH
) -> list[int]:
    conn = _get_connection(db_path)
    ids: list[int] = []
    with conn:
        for s in scores:
            cur = conn.execute(
                """
                INSERT INTO scored_opportunities
                    (cluster_id, score, reasoning, risks, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    s.get("cluster_id"),
                    s["score"],
                    s["reasoning"],
                    json.dumps(s.get("risks", [])),
                    _now(),
                ),
            )
            ids.append(cur.lastrowid)
    conn.close()
    return ids


def load_top_scores(
    top_n: int = 3, db_path: Path = DB_PATH
) -> list[dict[str, Any]]:
    conn = _get_connection(db_path)
    rows = conn.execute(
        """
        SELECT s.*, c.problem_cluster, c.frequency, c.example_cases
        FROM scored_opportunities s
        JOIN opportunity_clusters c ON c.id = s.cluster_id
        ORDER BY s.score DESC
        LIMIT ?
        """,
        (top_n,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "cluster_id": r["cluster_id"],
            "score": r["score"],
            "reasoning": r["reasoning"],
            "risks": json.loads(r["risks"]),
            "problem_cluster": r["problem_cluster"],
            "frequency": r["frequency"],
            "example_cases": json.loads(r["example_cases"]),
        }
        for r in rows
    ]


# ---------- validations ----------

def save_validation(
    validation: dict[str, Any], db_path: Path = DB_PATH
) -> int:
    conn = _get_connection(db_path)
    with conn:
        cur = conn.execute(
            """
            INSERT INTO validations
                (scored_id, landing_page, outreach_message,
                 validation_score, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                validation.get("scored_id"),
                validation.get("landing_page", ""),
                validation.get("outreach_message", ""),
                validation.get("validation_score", 0.0),
                validation.get("confidence", 0.0),
                _now(),
            ),
        )
        row_id = cur.lastrowid
    conn.close()
    return row_id


# ---------- MVPs ----------

def save_mvp(mvp: dict[str, Any], db_path: Path = DB_PATH) -> int:
    conn = _get_connection(db_path)
    with conn:
        cur = conn.execute(
            """
            INSERT INTO built_mvps
                (validation_id, name, readme, code, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                mvp.get("validation_id"),
                mvp["name"],
                mvp.get("readme", ""),
                json.dumps(mvp.get("code", {})),
                _now(),
            ),
        )
        row_id = cur.lastrowid
    conn.close()
    return row_id


# ---------- cycle log ----------

def log_cycle(cycle: int, phase: str, summary: str, db_path: Path = DB_PATH) -> None:
    conn = _get_connection(db_path)
    with conn:
        conn.execute(
            "INSERT INTO cycle_log (cycle, phase, summary, created_at) VALUES (?, ?, ?, ?)",
            (cycle, phase, summary, _now()),
        )
    conn.close()
