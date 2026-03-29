"""CLI entry point for AODE."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aode",
        description="Autonomous Opportunity Discovery Engine",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of discovery cycles to run (default: 1)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=3,
        help="Number of top opportunities to validate (default: 3)",
    )
    parser.add_argument(
        "--no-sklearn",
        action="store_true",
        help="Disable ML-based clustering (use keyword heuristic instead)",
    )
    parser.add_argument(
        "--n-clusters",
        type=int,
        default=8,
        help="Number of k-means clusters (default: 8)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=200,
        help="Maximum posts to fetch per cycle (default: 200)",
    )

    args = parser.parse_args()

    from aode.orchestrator import Orchestrator

    orchestrator = Orchestrator(
        top_n=args.top_n,
        max_posts=args.max_posts,
        use_sklearn=not args.no_sklearn,
        n_clusters=args.n_clusters,
    )
    orchestrator.run(cycles=args.cycles)


if __name__ == "__main__":
    main()
