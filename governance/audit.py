"""
governance/audit.py

Immutable audit logger for every agent action and decision.

NIST 800-53 mappings:
    AU-2  — Audit events: every agent action is a loggable event
    AU-9  — Protection of audit information: append-only design
    AU-12 — Audit record generation: tied to session and source prompt

AI RMF mappings:
    GOVERN 1.7 — Processes for accountability and transparency
    MEASURE 4.1 — Trustworthiness measurements documented and reported
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Append-only audit log for agent sessions.

    Design principle (AU-9): entries are never modified after write.
    In production, ship these to an immutable log sink (CloudTrail,
    Splunk, or a WORM-compliant storage bucket).
    """

    def __init__(self, agent_name: str, log_dir: str = "logs/audit"):
        self.agent_name = agent_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._traces: dict[str, list[dict]] = {}

    def start_session(self, session_id: str, goal: str, context: dict) -> None:
        self._traces[session_id] = []
        self._write(session_id, event="session_start", payload={
            "goal": goal,
            "context_keys": list(context.keys()),
        })

    def log_plan(self, session_id: str, plan: Any) -> None:
        self._write(session_id, event="plan_created", payload={
            "goal": plan.goal,
            "step_count": len(plan.steps),
            "rationale": plan.rationale,
            "steps": [
                {"action": s.action, "tool": s.tool}
                for s in plan.steps
            ],
        })

    def log_step(self, session_id: str, step: Any, result: dict) -> None:
        self._write(session_id, event="step_executed", payload={
            "action": step.action,
            "tool": step.tool,
            "parameters": step.parameters,
            "result_status": result.get("status"),
        })

    def log_guardrail_block(self, session_id: str, step: Any, reason: str) -> None:
        self._write(session_id, event="guardrail_block", payload={
            "action": step.action,
            "tool": step.tool,
            "block_reason": reason,
        })

    def log_error(self, session_id: str, error: str) -> None:
        self._write(session_id, event="error", payload={"error": error})

    def end_session(
        self,
        session_id: str,
        outcome: str,
        success: bool,
        completed_at: str,
    ) -> None:
        self._write(session_id, event="session_end", payload={
            "outcome": outcome,
            "success": success,
            "completed_at": completed_at,
        })
        # Flush trace to file
        self._flush(session_id)

    def get_trace(self, session_id: str) -> list[dict]:
        return self._traces.get(session_id, [])

    def _write(self, session_id: str, event: str, payload: dict) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": self.agent_name,
            "session_id": session_id,
            "event": event,
            "payload": payload,
        }
        self._traces.setdefault(session_id, []).append(entry)
        logger.info(json.dumps(entry))

    def _flush(self, session_id: str) -> None:
        """Write full session trace to disk as a JSON audit record."""
        path = self.log_dir / f"{session_id}.json"
        with open(path, "w") as f:
            json.dump(self._traces[session_id], f, indent=2)
