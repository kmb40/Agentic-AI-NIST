"""
tests/test_agent.py

Unit tests for the agent runtime and governance components.
"""

import pytest
from agent.memory import MemoryStore
from agent.planner import Planner, TaskStep
from agent.runtime import AgentConfig, AgentRuntime
from governance.guardrails import GuardrailEngine, GuardrailRule


# ── Memory Tests ───────────────────────────────────────────────────────────────

class TestMemoryStore:

    def test_store_and_retrieve(self):
        mem = MemoryStore()
        mem.store("scan_result", {"findings": 3})
        result = mem.retrieve("scan")
        assert "scan_result" in result
        assert result["scan_result"]["findings"] == 3

    def test_retrieve_no_match_returns_empty(self):
        mem = MemoryStore()
        mem.store("unrelated_key", "value")
        result = mem.retrieve("nonexistent_query")
        assert result == {}

    def test_get_exact_key(self):
        mem = MemoryStore()
        mem.store("my_key", 42)
        assert mem.get("my_key") == 42

    def test_clear_empties_store(self):
        mem = MemoryStore()
        mem.store("key", "value")
        mem.clear()
        assert len(mem) == 0


# ── Guardrail Tests ────────────────────────────────────────────────────────────

class TestGuardrailEngine:

    def setup_method(self):
        self.engine = GuardrailEngine()

    def test_allows_safe_action(self):
        allowed, reason = self.engine.check(
            action="analyze_logs",
            tool="reasoning",
            parameters={"query": "find anomalies"},
        )
        assert allowed is True
        assert reason == "allowed"

    def test_blocks_destructive_action(self):
        allowed, reason = self.engine.check(
            action="delete_records",
            tool="database",
            parameters={},
        )
        assert allowed is False
        assert "no_destructive_operations" in reason

    def test_blocks_shell_tool(self):
        allowed, reason = self.engine.check(
            action="run_script",
            tool="bash",
            parameters={},
        )
        assert allowed is False
        assert "no_shell_execution" in reason

    def test_blocks_credential_params(self):
        allowed, reason = self.engine.check(
            action="authenticate",
            tool="http_get",
            parameters={"api_key": "secret123"},
        )
        assert allowed is False
        assert "no_credential_exposure" in reason

    def test_custom_rule_applied(self):
        self.engine.add_rule(GuardrailRule(
            name="no_external_writes",
            description="Block writes to external systems",
            blocked_actions=["write_external"],
        ))
        allowed, reason = self.engine.check(
            action="write_external_log",
            tool="http_get",
            parameters={},
        )
        assert allowed is False
        assert "no_external_writes" in reason


# ── Planner Tests ──────────────────────────────────────────────────────────────

class TestPlanner:

    def test_plan_filters_disallowed_tools(self):
        planner = Planner(allowed_tools=["reasoning"])
        plan = planner.create_plan(
            goal="test goal",
            context={},
        )
        for step in plan.steps:
            assert step.tool in {"reasoning"}

    def test_evaluate_no_steps_returns_false(self):
        planner = Planner(allowed_tools=["reasoning"])
        mem = MemoryStore()
        success, outcome = planner.evaluate(goal="test", memory=mem, steps_taken=0)
        assert success is False
        assert outcome == "no_steps_executed"


# ── Runtime Integration Test ───────────────────────────────────────────────────

class TestAgentRuntime:

    def test_dry_run_completes(self):
        config = AgentConfig(
            name="test-agent",
            allowed_tools=["reasoning"],
            dry_run=True,
        )
        agent = AgentRuntime(config=config)
        result = agent.run(goal="analyze threat surface")
        assert result.session_id is not None
        assert result.started_at is not None
        assert result.completed_at is not None

    def test_audit_trace_populated(self):
        config = AgentConfig(
            name="audit-test",
            allowed_tools=["reasoning"],
            dry_run=True,
        )
        agent = AgentRuntime(config=config)
        result = agent.run(goal="check compliance posture")
        assert len(result.audit_trace) > 0
        events = [e["event"] for e in result.audit_trace]
        assert "session_start" in events
        assert "session_end" in events

    def test_max_steps_respected(self):
        config = AgentConfig(
            name="limit-test",
            allowed_tools=["reasoning"],
            max_steps=0,
            dry_run=True,
        )
        agent = AgentRuntime(config=config)
        result = agent.run(goal="enumerate vulnerabilities")
        assert result.steps_taken == 0
