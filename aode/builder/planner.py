"""Planner Agent — decomposes a problem into implementation tasks."""

from __future__ import annotations

import os
from typing import Any


class PlannerAgent:
    """Breaks a startup idea into actionable engineering tasks.

    Uses the OpenAI API when ``OPENAI_API_KEY`` is set, otherwise uses a
    structured heuristic decomposition that works offline.
    """

    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY", "")

    def plan(
        self, problem: str, validation: dict[str, Any]
    ) -> dict[str, Any]:
        """Return a structured plan dict.

        Returns:
            {
                "problem": str,
                "mvp_type": "cli" | "web",
                "tasks": [{"name": str, "description": str, "filename": str}],
                "tech_stack": [str],
            }
        """
        if self._api_key:
            try:
                return self._plan_with_llm(problem, validation)
            except Exception:  # noqa: BLE001
                pass  # fall through to heuristic

        return self._plan_heuristic(problem, validation)

    def _plan_heuristic(
        self, problem: str, validation: dict[str, Any]
    ) -> dict[str, Any]:
        prob_lower = problem.lower()

        # Determine MVP type
        mvp_type = "cli"
        if any(kw in prob_lower for kw in ["web", "platform", "dashboard", "portal"]):
            mvp_type = "web"

        # Core tasks every MVP needs
        tasks = [
            {
                "name": "data_model",
                "description": f"Define data structures for {problem[:50]}",
                "filename": "models.py",
            },
            {
                "name": "core_logic",
                "description": f"Implement core business logic for {problem[:50]}",
                "filename": "core.py",
            },
            {
                "name": "cli_interface",
                "description": "Build CLI interface with argparse",
                "filename": "main.py",
            },
            {
                "name": "storage",
                "description": "Persist state using JSON or SQLite",
                "filename": "storage.py",
            },
            {
                "name": "requirements",
                "description": "List Python dependencies",
                "filename": "requirements.txt",
            },
        ]

        # Swap CLI for web if needed
        if mvp_type == "web":
            tasks[2] = {
                "name": "web_app",
                "description": "Build FastAPI web application",
                "filename": "app.py",
            }

        tech_stack = ["Python 3.10+", "argparse", "sqlite3", "json"]
        if mvp_type == "web":
            tech_stack = ["Python 3.10+", "FastAPI", "uvicorn", "sqlite3"]

        return {
            "problem": problem,
            "mvp_type": mvp_type,
            "tasks": tasks,
            "tech_stack": tech_stack,
        }

    def _plan_with_llm(
        self, problem: str, validation: dict[str, Any]
    ) -> dict[str, Any]:
        """Delegate planning to OpenAI chat completions."""
        import json as _json
        import openai  # type: ignore[import-untyped]

        client = openai.OpenAI(api_key=self._api_key)
        prompt = (
            f"You are a senior software architect. "
            f"Break down this startup problem into 5 engineering tasks for a minimal MVP.\n\n"
            f"Problem: {problem}\n\n"
            f"Respond ONLY with valid JSON matching this schema:\n"
            f'{{"problem": str, "mvp_type": "cli"|"web", "tasks": '
            f'[{{"name": str, "description": str, "filename": str}}], '
            f'"tech_stack": [str]}}'
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3,
        )
        content = response.choices[0].message.content or "{}"
        return _json.loads(content)
