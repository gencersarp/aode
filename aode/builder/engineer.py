"""Engineer Agent — generates runnable code for each planned task."""

from __future__ import annotations

import os
import textwrap
from typing import Any


class EngineerAgent:
    """Generates Python code files for each task in the plan.

    Uses OpenAI when ``OPENAI_API_KEY`` is set, otherwise produces
    high-quality template code using the problem context.
    """

    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY", "")

    def build(self, plan: dict[str, Any], problem: str) -> dict[str, str]:
        """Return a dict mapping filename → file content."""
        if self._api_key:
            try:
                return self._build_with_llm(plan, problem)
            except Exception:  # noqa: BLE001
                pass

        return self._build_heuristic(plan, problem)

    # ------------------------------------------------------------------
    # Heuristic code generator
    # ------------------------------------------------------------------

    def _build_heuristic(
        self, plan: dict[str, Any], problem: str
    ) -> dict[str, str]:
        code: dict[str, str] = {}
        mvp_type = plan.get("mvp_type", "cli")
        tech_stack = plan.get("tech_stack", [])

        for task in plan.get("tasks", []):
            filename = task.get("filename", "module.py")
            name = task.get("name", "unknown")
            description = task.get("description", "")
            code[filename] = self._generate_file(
                name, filename, description, problem, mvp_type
            )

        # Always ensure requirements.txt exists
        if "requirements.txt" not in code:
            deps = ["requests>=2.31.0"]
            if mvp_type == "web":
                deps += ["fastapi>=0.104.0", "uvicorn>=0.24.0"]
            code["requirements.txt"] = "\n".join(deps) + "\n"

        return code

    def _generate_file(
        self,
        task_name: str,
        filename: str,
        description: str,
        problem: str,
        mvp_type: str,
    ) -> str:
        generators = {
            "data_model": self._gen_models,
            "core_logic": self._gen_core,
            "cli_interface": self._gen_cli,
            "web_app": self._gen_web,
            "storage": self._gen_storage,
            "requirements": self._gen_requirements,
        }
        gen = generators.get(task_name, self._gen_generic)
        return gen(problem, description, mvp_type)

    def _gen_models(self, problem: str, description: str, mvp_type: str) -> str:
        return textwrap.dedent(
            f'''\
            """Data models for: {problem[:60]}"""

            from __future__ import annotations
            from dataclasses import dataclass, field
            from typing import Any


            @dataclass
            class Problem:
                """Represents a captured user problem."""
                id: str = ""
                description: str = ""
                source: str = ""
                severity: int = 0          # 1-10
                tags: list[str] = field(default_factory=list)

                def to_dict(self) -> dict[str, Any]:
                    return {{
                        "id": self.id,
                        "description": self.description,
                        "source": self.source,
                        "severity": self.severity,
                        "tags": self.tags,
                    }}

                @classmethod
                def from_dict(cls, data: dict[str, Any]) -> "Problem":
                    return cls(**{{k: v for k, v in data.items() if k in cls.__dataclass_fields__}})


            @dataclass
            class Solution:
                """A candidate solution/feature linked to a problem."""
                problem_id: str = ""
                name: str = ""
                status: str = "proposed"   # proposed | validated | shipped
                notes: str = ""

                def to_dict(self) -> dict[str, Any]:
                    return self.__dict__.copy()
            '''
        )

    def _gen_core(self, problem: str, description: str, mvp_type: str) -> str:
        return textwrap.dedent(
            f'''\
            """Core business logic for: {problem[:60]}"""

            from __future__ import annotations
            from typing import Any
            from models import Problem, Solution


            def capture_problem(description: str, source: str = "manual", severity: int = 5) -> Problem:
                """Create and register a new problem."""
                import uuid
                problem = Problem(
                    id=str(uuid.uuid4())[:8],
                    description=description,
                    source=source,
                    severity=severity,
                )
                return problem


            def score_problem(problem: Problem) -> float:
                """Return a simple urgency score based on severity."""
                return min(1.0, problem.severity / 10.0)


            def suggest_solutions(problem: Problem) -> list[Solution]:
                """Generate initial solution candidates for the problem."""
                templates = [
                    f"Automate {{problem.description[:30]}} via CLI tool",
                    f"Build a webhook integration for {{problem.description[:30]}}",
                    f"Create a no-code dashboard for {{problem.description[:30]}}",
                ]
                return [Solution(problem_id=problem.id, name=t) for t in templates]
            '''
        )

    def _gen_cli(self, problem: str, description: str, mvp_type: str) -> str:
        return textwrap.dedent(
            f'''\
            """CLI interface for: {problem[:60]}"""

            from __future__ import annotations
            import argparse
            import json
            from core import capture_problem, score_problem, suggest_solutions
            from storage import load_problems, save_problem


            def cmd_add(args: argparse.Namespace) -> None:
                problem = capture_problem(args.description, severity=args.severity)
                save_problem(problem)
                print(f"✓ Captured problem [{{problem.id}}]: {{problem.description[:50]}}")
                score = score_problem(problem)
                print(f"  Urgency score: {{score:.0%}}")


            def cmd_list(args: argparse.Namespace) -> None:
                problems = load_problems()
                if not problems:
                    print("No problems captured yet. Run: python main.py add --help")
                    return
                for p in sorted(problems, key=lambda x: x.severity, reverse=True):
                    print(f"[{{p.id}}] (sev={{p.severity}}) {{p.description[:60]}}")


            def cmd_suggest(args: argparse.Namespace) -> None:
                problems = load_problems()
                target = next((p for p in problems if p.id == args.id), None)
                if not target:
                    print(f"Problem {{args.id!r}} not found.")
                    return
                solutions = suggest_solutions(target)
                print(f"Suggested solutions for '{{target.description[:40]}}':")
                for s in solutions:
                    print(f"  • {{s.name}}")


            def main() -> None:
                parser = argparse.ArgumentParser(description="{problem[:60]}")
                sub = parser.add_subparsers(dest="command")

                p_add = sub.add_parser("add", help="Capture a new problem")
                p_add.add_argument("description", help="Problem description")
                p_add.add_argument("--severity", type=int, default=5, choices=range(1, 11))
                p_add.set_defaults(func=cmd_add)

                p_list = sub.add_parser("list", help="List all captured problems")
                p_list.set_defaults(func=cmd_list)

                p_sug = sub.add_parser("suggest", help="Suggest solutions for a problem")
                p_sug.add_argument("id", help="Problem ID")
                p_sug.set_defaults(func=cmd_suggest)

                args = parser.parse_args()
                if hasattr(args, "func"):
                    args.func(args)
                else:
                    parser.print_help()


            if __name__ == "__main__":
                main()
            '''
        )

    def _gen_web(self, problem: str, description: str, mvp_type: str) -> str:
        return textwrap.dedent(
            f'''\
            """FastAPI web app for: {problem[:60]}"""

            from __future__ import annotations
            from fastapi import FastAPI, HTTPException
            from pydantic import BaseModel
            from core import capture_problem, score_problem, suggest_solutions
            from storage import load_problems, save_problem

            app = FastAPI(title="{problem[:50]}", version="0.1.0")


            class ProblemIn(BaseModel):
                description: str
                severity: int = 5
                source: str = "api"


            @app.post("/problems")
            def create_problem(body: ProblemIn):
                p = capture_problem(body.description, body.source, body.severity)
                save_problem(p)
                return {{"id": p.id, "score": score_problem(p)}}


            @app.get("/problems")
            def list_problems():
                return [p.to_dict() for p in load_problems()]


            @app.get("/problems/{{problem_id}}/solutions")
            def get_solutions(problem_id: str):
                problems = load_problems()
                p = next((x for x in problems if x.id == problem_id), None)
                if not p:
                    raise HTTPException(404, "Problem not found")
                return [s.to_dict() for s in suggest_solutions(p)]


            if __name__ == "__main__":
                import uvicorn
                uvicorn.run(app, host="0.0.0.0", port=8000)
            '''
        )

    def _gen_storage(self, problem: str, description: str, mvp_type: str) -> str:
        return textwrap.dedent(
            '''\
            """Persistent storage using JSON."""

            from __future__ import annotations
            import json
            from pathlib import Path
            from models import Problem

            _DATA_FILE = Path("problems.json")


            def save_problem(problem: Problem) -> None:
                problems = load_problems()
                # Update existing or append
                ids = [p.id for p in problems]
                if problem.id in ids:
                    problems[ids.index(problem.id)] = problem
                else:
                    problems.append(problem)
                _DATA_FILE.write_text(
                    json.dumps([p.to_dict() for p in problems], indent=2)
                )


            def load_problems() -> list[Problem]:
                if not _DATA_FILE.exists():
                    return []
                data = json.loads(_DATA_FILE.read_text())
                return [Problem.from_dict(d) for d in data]
            '''
        )

    def _gen_requirements(
        self, problem: str, description: str, mvp_type: str
    ) -> str:
        if mvp_type == "web":
            return "fastapi>=0.104.0\nuvicorn>=0.24.0\npydantic>=2.0.0\n"
        return "# No external dependencies required\n"

    def _gen_generic(
        self, problem: str, description: str, mvp_type: str
    ) -> str:
        return textwrap.dedent(
            f'''\
            """Module: {description[:60]}

            Problem: {problem[:60]}
            """

            # TODO: Implement {description[:40]}
            '''
        )

    # ------------------------------------------------------------------
    # LLM-powered code generator
    # ------------------------------------------------------------------

    def _build_with_llm(
        self, plan: dict[str, Any], problem: str
    ) -> dict[str, str]:
        import openai  # type: ignore[import-untyped]

        client = openai.OpenAI(api_key=self._api_key)
        code: dict[str, str] = {}

        for task in plan.get("tasks", []):
            filename = task.get("filename", "module.py")
            description = task.get("description", "")

            prompt = (
                f"Write production-quality Python code for this task.\n\n"
                f"Problem: {problem}\n"
                f"Task: {description}\n"
                f"Filename: {filename}\n\n"
                f"Output ONLY the raw Python code, no markdown fences."
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.2,
            )
            code[filename] = response.choices[0].message.content or ""

        return code
