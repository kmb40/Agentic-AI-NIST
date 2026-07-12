"""
governance/guardrails.py

Runtime policy enforcement engine.
Evaluates every planned action before execution.

NIST 800-53 mappings:
    AC-6  — Least privilege: only permit explicitly allowed tool actions
    CM-7  — Least functionality: deny tools not in the approved set
    SI-10 — Information input validation: parameters inspected before execution

AI RMF mappings:
    GOVERN 6.1 — Policies that establish organizational risk tolerance
    GOVERN 6.2 — Organizational teams apply risk policies to deployment
    MANAGE 1.3 — Responses to identified AI risks prioritized and managed
"""

from dataclasses import dataclass, field


@dataclass
class GuardrailRule:
    """A single policy rule evaluated against an action."""
    name: str
    description: str
    blocked_tools: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    blocked_param_keys: list[str] = field(default_factory=list)


# Default rule set — extend for your organization's risk tolerance
DEFAULT_RULES: list[GuardrailRule] = [
    GuardrailRule(
        name="no_destructive_operations",
        description="Block any action that could delete or overwrite data",
        blocked_actions=["delete", "drop", "truncate", "overwrite", "destroy"],
    ),
    GuardrailRule(
        name="no_credential_exposure",
        description="Block actions attempting to access or transmit credentials",
        blocked_param_keys=["password", "secret", "api_key", "token", "private_key"],
    ),
    GuardrailRule(
        name="no_shell_execution",
        description="Block direct shell or OS command execution",
        blocked_tools=["shell", "bash", "exec", "subprocess", "os_command"],
    ),
]


class GuardrailEngine:
    """
    Evaluates agent actions against a policy rule set before execution.
    Returns (allowed: bool, reason: str).

    Add custom rules via add_rule() to extend organizational policy.
    """

    def __init__(self, rules: list[GuardrailRule] | None = None):
        self.rules = rules if rules is not None else list(DEFAULT_RULES)

    def add_rule(self, rule: GuardrailRule) -> None:
        self.rules.append(rule)

    def check(
        self,
        action: str,
        tool: str,
        parameters: dict,
    ) -> tuple[bool, str]:
        """
        Evaluate the action against all active rules.
        Returns (True, "allowed") if all rules pass.
        Returns (False, reason) on first violation.
        """
        action_lower = action.lower()
        tool_lower = tool.lower()
        param_keys = {k.lower() for k in parameters.keys()}

        for rule in self.rules:
            # Check blocked tools
            if any(blocked in tool_lower for blocked in rule.blocked_tools):
                return False, f"Rule '{rule.name}': tool '{tool}' is blocked. {rule.description}"

            # Check blocked actions
            if any(blocked in action_lower for blocked in rule.blocked_actions):
                return False, f"Rule '{rule.name}': action '{action}' is blocked. {rule.description}"

            # Check blocked parameter keys
            if any(blocked in param_keys for blocked in rule.blocked_param_keys):
                matched = param_keys & set(rule.blocked_param_keys)
                return False, (
                    f"Rule '{rule.name}': parameter(s) {matched} are blocked. "
                    f"{rule.description}"
                )

        return True, "allowed"

    def list_rules(self) -> list[dict]:
        return [
            {
                "name": r.name,
                "description": r.description,
                "blocked_tools": r.blocked_tools,
                "blocked_actions": r.blocked_actions,
                "blocked_param_keys": r.blocked_param_keys,
            }
            for r in self.rules
        ]
