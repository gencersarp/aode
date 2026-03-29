"""Auto-Build System — multi-agent MVP builder.

Agents:
  - PlannerAgent  : breaks the idea into implementation tasks
  - EngineerAgent : generates runnable Python code for each task
  - TesterAgent   : validates output structure and executes smoke tests

The build pipeline orchestrates all three agents and produces:
  - A working MVP (Python CLI or simple web app)
  - A README.md
  - Structured code dict keyed by filename
"""

from __future__ import annotations

from typing import Any

from aode.builder.planner import PlannerAgent
from aode.builder.engineer import EngineerAgent
from aode.builder.tester import TesterAgent


def build_mvp(
    validation: dict[str, Any],
    validation_id: int | None = None,
) -> dict[str, Any]:
    """Run the full build pipeline for a validated opportunity.

    Args:
        validation: Output from the validation engine.
        validation_id: DB row id of the validation record.

    Returns:
        MVP dict with ``name``, ``readme``, ``code`` and ``test_results``.
    """
    problem = validation.get("problem_cluster", "Unknown Problem")

    planner = PlannerAgent()
    engineer = EngineerAgent()
    tester = TesterAgent()

    # Step 1: Plan
    plan = planner.plan(problem, validation)

    # Step 2: Engineer
    code = engineer.build(plan, problem)

    # Step 3: Test
    test_results = tester.test(code, plan)

    # Step 4: Generate README
    readme = _generate_readme(problem, plan, test_results)

    name = _slugify(problem)

    return {
        "validation_id": validation_id,
        "name": name,
        "readme": readme,
        "code": code,
        "plan": plan,
        "test_results": test_results,
    }


def _slugify(text: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60]


def _generate_readme(
    problem: str,
    plan: dict[str, Any],
    test_results: dict[str, Any],
) -> str:
    tasks = plan.get("tasks", [])
    status = test_results.get("status", "unknown")
    passed = test_results.get("passed", 0)
    total = test_results.get("total", 0)

    task_list = "\n".join(f"- {t['name']}: {t['description']}" for t in tasks)
    return (
        f"# {problem}\n\n"
        f"Auto-generated MVP by AODE (Autonomous Opportunity Discovery Engine).\n\n"
        f"## Problem\n{problem}\n\n"
        f"## Implementation Plan\n{task_list}\n\n"
        f"## Getting Started\n"
        f"```bash\npip install -r requirements.txt\npython main.py\n```\n\n"
        f"## Test Results\n"
        f"Status: **{status}** ({passed}/{total} checks passed)\n\n"
        f"---\n*Built automatically — review and extend before shipping.*\n"
    )
