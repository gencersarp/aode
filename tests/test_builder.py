"""Tests for the Auto-Build System."""

from __future__ import annotations

import pytest

from aode.builder.planner import PlannerAgent
from aode.builder.engineer import EngineerAgent
from aode.builder.tester import TesterAgent
from aode.builder import build_mvp


_VALIDATION = {
    "problem_cluster": "Affordable invoicing for freelancers",
    "validation_score": 0.65,
    "confidence": 0.8,
    "landing_page": "# Invoice Tool\nStop paying too much.",
    "outreach_message": "Hi {first_name}, ...",
}


def test_planner_returns_plan():
    agent = PlannerAgent()
    plan = agent.plan("Invoicing tool for freelancers", _VALIDATION)
    assert isinstance(plan, dict)
    assert "tasks" in plan
    assert "mvp_type" in plan
    assert len(plan["tasks"]) >= 3


def test_planner_task_schema():
    agent = PlannerAgent()
    plan = agent.plan("Invoicing tool", _VALIDATION)
    for task in plan["tasks"]:
        assert "name" in task
        assert "description" in task
        assert "filename" in task


def test_engineer_generates_code():
    planner = PlannerAgent()
    engineer = EngineerAgent()
    plan = planner.plan("Invoicing tool for freelancers", _VALIDATION)
    code = engineer.build(plan, "Invoicing tool for freelancers")
    assert isinstance(code, dict)
    assert len(code) >= 1


def test_engineer_code_has_expected_files():
    planner = PlannerAgent()
    engineer = EngineerAgent()
    plan = planner.plan("Invoicing tool for freelancers", _VALIDATION)
    code = engineer.build(plan, "Invoicing tool")
    expected = {t["filename"] for t in plan["tasks"]}
    # At least half the planned files should be generated
    generated = set(code.keys())
    overlap = expected & generated
    assert len(overlap) >= len(expected) // 2


def test_tester_validates_code():
    planner = PlannerAgent()
    engineer = EngineerAgent()
    tester = TesterAgent()
    plan = planner.plan("Invoicing tool for freelancers", _VALIDATION)
    code = engineer.build(plan, "Invoicing tool")
    results = tester.test(code, plan)
    assert "status" in results
    assert "passed" in results
    assert "total" in results
    assert results["status"] in ("pass", "partial", "fail")


def test_tester_detects_syntax_error():
    tester = TesterAgent()
    bad_code = {"main.py": "def main(\n  print('unclosed'"}
    plan = {"mvp_type": "cli", "tasks": [{"filename": "main.py"}]}
    results = tester.test(bad_code, plan)
    syntax_checks = [c for c in results["checks"] if c["name"].startswith("syntax:")]
    assert any(not c["passed"] for c in syntax_checks)


def test_build_mvp_full_pipeline():
    mvp = build_mvp(_VALIDATION, validation_id=None)
    assert "name" in mvp
    assert "readme" in mvp
    assert "code" in mvp
    assert "test_results" in mvp
    assert isinstance(mvp["code"], dict)
    assert len(mvp["code"]) >= 1


def test_build_mvp_readme_content():
    mvp = build_mvp(_VALIDATION)
    readme = mvp["readme"]
    assert isinstance(readme, str)
    assert len(readme) > 20
    assert "#" in readme
