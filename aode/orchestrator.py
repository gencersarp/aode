"""AODE Orchestrator — main discovery and build loop.

Executes one full cycle:
  1. Fetch raw data from all scrapers
  2. Extract opportunity clusters
  3. Score each cluster
  4. Validate top N ideas
  5. Build MVP for best idea
  6. Persist all results
  7. Reflect and summarise
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from aode.ingestion.reddit_scraper import RedditScraper
from aode.ingestion.github_scraper import GitHubScraper
from aode.extraction import extract_opportunities
from aode.scoring import score_opportunities
from aode.validation import validate_top_opportunities
from aode.builder import build_mvp
from aode import storage

_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def _banner(msg: str) -> None:
    width = 70
    print("\n" + "=" * width)
    print(f"  {msg}")
    print("=" * width)


def _step(msg: str) -> None:
    print(f"  → {msg}")


class Orchestrator:
    """Runs one or more AODE discovery cycles."""

    def __init__(
        self,
        top_n: int = 3,
        max_posts: int = 200,
        use_sklearn: bool = True,
        n_clusters: int = 8,
        db_path: Path | None = None,
    ) -> None:
        self.top_n = top_n
        self.max_posts = max_posts
        self.use_sklearn = use_sklearn
        self.n_clusters = n_clusters
        self._db_path = db_path or storage.DB_PATH
        storage.init_db(db_path=self._db_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_cycle(self, cycle: int = 1) -> dict[str, Any]:
        """Execute a single full discovery-build cycle.

        Returns a summary dict with all cycle artefacts.
        """
        _banner(f"AODE Cycle {cycle}")
        start = time.time()

        # 1. Ingest
        _step("Fetching data…")
        posts = self._fetch_data()
        storage.log_cycle(cycle, "ingest", f"Fetched {len(posts)} posts", db_path=self._db_path)
        _step(f"Fetched {len(posts)} posts")

        # 2. Extract
        _step("Extracting opportunity clusters…")
        clusters = extract_opportunities(
            posts, use_sklearn=self.use_sklearn, n_clusters=self.n_clusters
        )
        cluster_ids = storage.save_clusters(clusters, db_path=self._db_path)
        for c, cid in zip(clusters, cluster_ids):
            c["id"] = cid
        storage.log_cycle(cycle, "extract", f"Found {len(clusters)} clusters", db_path=self._db_path)
        _step(f"Extracted {len(clusters)} clusters")

        # 3. Score
        _step("Scoring opportunities…")
        scored = score_opportunities(clusters)
        score_ids = storage.save_scores(scored, db_path=self._db_path)
        storage.log_cycle(cycle, "score", f"Scored {len(scored)} opportunities", db_path=self._db_path)
        top_scored = storage.load_top_scores(top_n=self.top_n, db_path=self._db_path)
        _step(f"Top {self.top_n} opportunities identified")

        # 4. Validate
        _step("Validating top opportunities…")
        top_score_ids = score_ids[: self.top_n]
        validations = validate_top_opportunities(top_scored, scored_ids=top_score_ids)
        validation_ids: list[int] = []
        for v in validations:
            vid = storage.save_validation(v, db_path=self._db_path)
            validation_ids.append(vid)
        storage.log_cycle(cycle, "validate", f"Validated {len(validations)} ideas", db_path=self._db_path)
        _step(f"Validated {len(validations)} ideas")

        # 5. Build
        best_validation = validations[0] if validations else None
        mvp: dict[str, Any] = {}
        if best_validation:
            _step(f"Building MVP for: {best_validation.get('problem_cluster', '?')[:50]}…")
            best_vid = validation_ids[0] if validation_ids else None
            mvp = build_mvp(best_validation, validation_id=best_vid)
            storage.save_mvp(mvp, db_path=self._db_path)
            self._write_mvp_to_disk(mvp, cycle)
            storage.log_cycle(cycle, "build", f"Built MVP: {mvp.get('name', '?')}", db_path=self._db_path)
            _step(f"MVP built: {mvp.get('name', '?')}")

        elapsed = round(time.time() - start, 2)

        # 6. Reflect
        reflection = self._reflect(clusters, scored, validations, mvp, elapsed)
        storage.log_cycle(cycle, "reflect", reflection, db_path=self._db_path)
        _step("Reflection complete")

        summary = {
            "cycle": cycle,
            "posts_fetched": len(posts),
            "clusters_found": len(clusters),
            "top_opportunities": top_scored,
            "validations": validations,
            "mvp": mvp,
            "reflection": reflection,
            "elapsed_seconds": elapsed,
        }

        self._print_summary(summary)
        return summary

    def run(self, cycles: int = 1) -> list[dict[str, Any]]:
        """Run multiple cycles sequentially."""
        results = []
        for i in range(1, cycles + 1):
            results.append(self.run_cycle(cycle=i))
            if i < cycles:
                time.sleep(1)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_data(self) -> list[dict[str, Any]]:
        scrapers = [RedditScraper(), GitHubScraper()]
        posts: list[dict[str, Any]] = []
        for scraper in scrapers:
            try:
                fetched = scraper.fetch(limit=self.max_posts // len(scrapers))
                posts.extend(fetched)
            except Exception as exc:  # noqa: BLE001
                print(f"    [WARN] {scraper.source_name} scraper failed: {exc}")
        storage.save_raw_posts(posts, db_path=self._db_path)
        return posts

    def _write_mvp_to_disk(self, mvp: dict[str, Any], cycle: int) -> None:
        """Persist generated MVP files to the output directory."""
        name = mvp.get("name", f"cycle_{cycle}_mvp")
        mvp_dir = _OUTPUT_DIR / f"cycle_{cycle}" / name
        mvp_dir.mkdir(parents=True, exist_ok=True)

        readme_path = mvp_dir / "README.md"
        readme_path.write_text(mvp.get("readme", ""))

        code = mvp.get("code", {})
        for filename, content in code.items():
            (mvp_dir / filename).write_text(content)

        # Also write a manifest
        manifest = {
            "cycle": cycle,
            "name": name,
            "problem_cluster": mvp.get("plan", {}).get("problem", ""),
            "test_results": mvp.get("test_results", {}),
        }
        (mvp_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    @staticmethod
    def _reflect(
        clusters: list[dict[str, Any]],
        scored: list[dict[str, Any]],
        validations: list[dict[str, Any]],
        mvp: dict[str, Any],
        elapsed: float,
    ) -> str:
        if not scored:
            return "No opportunities found. Check data ingestion and extraction."

        best = scored[0] if scored else {}
        best_score = best.get("score", 0.0)
        weakest_component = "scoring" if best_score < 0.3 else "extraction"

        test_status = mvp.get("test_results", {}).get("status", "unknown")
        if test_status != "pass":
            weakest_component = "build"

        return (
            f"Cycle completed in {elapsed}s. "
            f"Found {len(clusters)} clusters, top score={best_score:.3f}. "
            f"MVP status: {test_status}. "
            f"Weakest component: {weakest_component}. "
            f"Next: improve {weakest_component} module."
        )

    @staticmethod
    def _print_summary(summary: dict[str, Any]) -> None:
        _banner(f"Cycle {summary['cycle']} Summary")
        print(f"  Posts fetched      : {summary['posts_fetched']}")
        print(f"  Clusters found     : {summary['clusters_found']}")
        print()
        print("  Top Opportunities:")
        for i, opp in enumerate(summary.get("top_opportunities", []), 1):
            print(
                f"    {i}. [{opp.get('score', 0):.3f}] "
                f"{opp.get('problem_cluster', '?')[:55]}"
            )
        print()
        print(f"  MVP Built          : {summary.get('mvp', {}).get('name', 'N/A')}")
        mvp_tests = summary.get("mvp", {}).get("test_results", {})
        if mvp_tests:
            print(
                f"  Test Status        : {mvp_tests.get('status')} "
                f"({mvp_tests.get('passed')}/{mvp_tests.get('total')} checks)"
            )
        print()
        print(f"  Reflection: {summary['reflection']}")
        print()
