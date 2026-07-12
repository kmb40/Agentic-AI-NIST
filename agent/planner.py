"""
agent/planner.py

Planning engine — decomposes goals into executable task steps.

NIST 800-53 mappings:
    SA-8  — Security design principles: minimal footprint, explicit tool scoping
    PL-2  — Planning artifacts captured and auditable
    CM-7  — Only approved tools are plan-eligible

AI RMF mappings:
    MAP 1.0 — Context establishment: what the agent is allowed to do
    MAP 2.0 — Scientific and engineering practices applied to plan construction
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskStep:
    """A single atomic action within a plan."""
    action: str
    tool: str
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class Plan:
    goal: str
    steps: list[TaskStep]
    rationale: str = ""


class Planner:
    """
    Converts a high-level goal string into an ordered list of TaskSteps.

    In production, replace _decompose_goal with an LLM-backed reasoning
    call (e.g., Anthropic Claude with tool use) constrained to allowed_tools.
    The interface stays the same — only the decomposition logic changes.
    """

    def __init__(self, allowed_tools: list[str]):
        self.allowed_tools = set(allowed_tools)

    def create_plan(self, goal: str, context: dict[str, Any]) -> Plan:
        """
        Produce a Plan for the given goal.
        Steps are filtered to only include allowed tools (CM-7 enforcement).
        """
        raw_steps = self._decompose_goal(goal=goal, context=context)
        safe_steps = [s for s in raw_steps if s.tool in self.allowed_tools]

        return Plan(
            goal=goal,
            steps=safe_steps,
            rationale=f"Plan generated for goal: {goal}. "
                      f"{len(raw_steps) - len(safe_steps)} step(s) excluded by tool policy.",
        )

    def evaluate(
        self,
        goal: str,
        memory: Any,
        steps_taken: int,
    ) -> tuple[bool, str]:
        """
        Assess whether the goal was achieved based on memory state.
        Returns (success: bool, outcome_description: str).
        """
        results = memory.retrieve(query=goal)
        if results and steps_taken > 0:
            return True, "goal_achieved"
        if steps_taken == 0:
            return False, "no_steps_executed"
        return False, "goal_not_verified"

    def _decompose_goal(self, goal: str, context: dict[str, Any]) -> list[TaskStep]:
        """
        Stub implementation. Replace with LLM-backed decomposition.

        Example production implementation:
            response = anthropic_client.messages.create(
                model="claude-opus-4-5",
                tools=self._build_tool_schemas(),
                messages=[{"role": "user", "content": goal}],
            )
            return self._parse_tool_use(response)
        """
        # Minimal stub returns a single reconnaissance step for demo purposes
        return [
            TaskStep(
                action="analyze_goal",
                tool="reasoning",
                parameters={"goal": goal, "context_keys": list(context.keys())},
                description=f"Analyze and plan approach for: {goal}",
            )
        ]
