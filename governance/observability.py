"""
governance/observability.py

Real-time behavioral monitoring and drift detection for agent sessions.

NIST 800-53 mappings:
    SI-7  — Software, firmware, and information integrity monitoring
    IR-6  — Incident reporting: anomalies surfaced for human review

AI RMF mappings:
    MEASURE 1.1 — Methods to identify AI risks established and in use
    MEASURE 2.5 — AI system to be deployed is demonstrated to be valid
    MEASURE 2.8 — Risks from AI system use monitored over time
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    session_id: str
    agent_name: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    steps_executed: int = 0
    guardrail_blocks: int = 0
    errors: int = 0
    tools_used: list[str] = field(default_factory=list)
    completed_at: str | None = None
    outcome: str | None = None
    success: bool | None = None


class ObservabilityLayer:
    """
    Tracks agent behavior across sessions and surfaces anomalies.

    In production, emit these metrics to your observability stack:
    Datadog, Prometheus, CloudWatch, or a SIEM for AU-6 review.
    """

    # Thresholds for anomaly detection (MEASURE 2.8)
    GUARDRAIL_BLOCK_THRESHOLD = 3
    ERROR_THRESHOLD = 2

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._sessions: dict[str, SessionMetrics] = {}
        self._anomalies: list[dict] = []

    def record_session_start(self, session_id: str) -> None:
        self._sessions[session_id] = SessionMetrics(
            session_id=session_id,
            agent_name=self.agent_name,
        )

    def record_step(self, step: Any, result: dict) -> None:
        session_id = self._infer_session()
        if session_id:
            m = self._sessions[session_id]
            m.steps_executed += 1
            if step.tool not in m.tools_used:
                m.tools_used.append(step.tool)

    def record_guardrail_block(self, step: Any, reason: str) -> None:
        session_id = self._infer_session()
        if session_id:
            m = self._sessions[session_id]
            m.guardrail_blocks += 1
            if m.guardrail_blocks >= self.GUARDRAIL_BLOCK_THRESHOLD:
                self._flag_anomaly(
                    session_id=session_id,
                    anomaly_type="excessive_guardrail_blocks",
                    detail=f"{m.guardrail_blocks} blocks in session. Last reason: {reason}",
                )

    def record_error(self, error: str) -> None:
        session_id = self._infer_session()
        if session_id:
            m = self._sessions[session_id]
            m.errors += 1
            if m.errors >= self.ERROR_THRESHOLD:
                self._flag_anomaly(
                    session_id=session_id,
                    anomaly_type="repeated_errors",
                    detail=f"{m.errors} errors in session. Latest: {error}",
                )

    def record_session_end(
        self, session_id: str, outcome: str, success: bool
    ) -> None:
        if session_id in self._sessions:
            m = self._sessions[session_id]
            m.completed_at = datetime.now(timezone.utc).isoformat()
            m.outcome = outcome
            m.success = success

    def get_session_metrics(self, session_id: str) -> SessionMetrics | None:
        return self._sessions.get(session_id)

    def get_anomalies(self) -> list[dict]:
        return list(self._anomalies)

    def _flag_anomaly(
        self, session_id: str, anomaly_type: str, detail: str
    ) -> None:
        anomaly = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": self.agent_name,
            "session_id": session_id,
            "anomaly_type": anomaly_type,
            "detail": detail,
        }
        self._anomalies.append(anomaly)
        logger.warning(f"ANOMALY DETECTED: {anomaly}")

    def _infer_session(self) -> str | None:
        """Return the most recent active session ID."""
        if not self._sessions:
            return None
        return list(self._sessions.keys())[-1]
