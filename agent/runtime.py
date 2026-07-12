"""
agent/runtime.py

Core agent runtime loop.
Implements the Perceive > Reason > Act > Evaluate cycle.

NIST 800-53 mappings:
    SA-8  — Security design principles enforced at construction
    PL-2  — System planning baked into the task lifecycle
    AU-12 — Every cycle is traceable to a source prompt

AI RMF mappings:
    MAP 1.0  — Agent capabilities scoped at initialization
    MANAGE 2.2 — Memory lifecycle managed per session
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent.memory import MemoryStore
from agent.planner import Planner
from governance.audit import AuditLogger
from governance.guardrails import GuardrailEngine
from governance.observability import ObservabilityLayer


@dataclass
class AgentConfig:
    """
    Defines the operational boundary of the agent at initialization.
    Scoping here maps to AI RMF MAP 1.0 (intended use) and
    NIST SA-8 (security design principles).
    """
    name: str
    allowed_tools: list[str]
    max_steps: int = 10
    memory_ttl_seconds: int = 3600
    dry_run: bool = False


@dataclass
class AgentResult:
    session_id: str
    goal: str
    steps_taken: int
    outcome: str
    success: bool
    started_at: str
    completed_at: str
    audit_trace: list[dict] = field(default_factory=list)


class AgentRuntime:
    """
    The central orchestrator. Coordinates planning, memory, tool execution,
    guardrail enforcement, and observability for every agent session.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.memory = MemoryStore(ttl_seconds=config.memory_ttl_seconds)
        self.planner = Planner(allowed_tools=config.allowed_tools)
        self.audit = AuditLogger(agent_name=config.name)
        self.guardrails = GuardrailEngine()
        self.observability = ObservabilityLayer(agent_name=config.name)

    def run(self, goal: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Execute the full perceive > reason > act > evaluate loop for a given goal.
        """
        session_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        context = context or {}

        self.audit.start_session(session_id=session_id, goal=goal, context=context)
        self.observability.record_session_start(session_id=session_id)

        steps_taken = 0
        outcome = "incomplete"
        success = False

        try:
            # PERCEIVE — load relevant memory into context
            memory_context = self.memory.retrieve(query=goal)
            context["memory"] = memory_context

            # REASON — build the task plan
            plan = self.planner.create_plan(goal=goal, context=context)
            self.audit.log_plan(session_id=session_id, plan=plan)

            # ACT — execute each planned step within guardrail bounds
            for step in plan.steps:
                if steps_taken >= self.config.max_steps:
                    outcome = "max_steps_reached"
                    break

                # Guardrail check before every action (AC-6, GOVERN 6.1)
                allowed, reason = self.guardrails.check(
                    action=step.action,
                    tool=step.tool,
                    parameters=step.parameters,
                )
                if not allowed:
                    self.audit.log_guardrail_block(
                        session_id=session_id, step=step, reason=reason
                    )
                    self.observability.record_guardrail_block(step=step, reason=reason)
                    continue

                # Execute (or simulate in dry_run mode)
                result = self._execute_step(step=step, dry_run=self.config.dry_run)
                self.audit.log_step(session_id=session_id, step=step, result=result)
                self.observability.record_step(step=step, result=result)

                # Store result in memory
                self.memory.store(key=step.action, value=result)
                steps_taken += 1

            # EVALUATE — assess whether the goal was achieved
            success, outcome = self.planner.evaluate(
                goal=goal, memory=self.memory, steps_taken=steps_taken
            )

        except Exception as exc:
            outcome = f"error: {exc}"
            self.audit.log_error(session_id=session_id, error=str(exc))
            self.observability.record_error(error=str(exc))

        finally:
            completed_at = datetime.now(timezone.utc).isoformat()
            self.audit.end_session(
                session_id=session_id,
                outcome=outcome,
                success=success,
                completed_at=completed_at,
            )
            self.observability.record_session_end(
                session_id=session_id, outcome=outcome, success=success
            )

        return AgentResult(
            session_id=session_id,
            goal=goal,
            steps_taken=steps_taken,
            outcome=outcome,
            success=success,
            started_at=started_at,
            completed_at=completed_at,
            audit_trace=self.audit.get_trace(session_id=session_id),
        )

    def _execute_step(self, step: Any, dry_run: bool) -> dict:
        if dry_run:
            return {"status": "dry_run", "tool": step.tool, "action": step.action}
        # Real execution delegated to registered tool handlers
        from tools.registry import ToolRegistry
        return ToolRegistry.execute(tool=step.tool, action=step.action, parameters=step.parameters)
