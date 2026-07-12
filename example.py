"""
example.py

Demonstrates the agent running a dry-run session with full governance hooks.
Run: python example.py
"""

import logging
from agent.runtime import AgentConfig, AgentRuntime

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main():
    config = AgentConfig(
        name="security-ops-agent",
        allowed_tools=["reasoning", "file_read", "http_get"],
        max_steps=5,
        dry_run=True,  # Set to False with real tool handlers in place
    )

    agent = AgentRuntime(config=config)

    result = agent.run(
        goal="Analyze the current threat surface and identify top 3 unpatched vulnerabilities",
        context={"environment": "production", "scope": "external-facing services"},
    )

    print("\n── Agent Result ──────────────────────────────────")
    print(f"Session ID : {result.session_id}")
    print(f"Goal       : {result.goal}")
    print(f"Success    : {result.success}")
    print(f"Outcome    : {result.outcome}")
    print(f"Steps      : {result.steps_taken}")
    print(f"Started    : {result.started_at}")
    print(f"Completed  : {result.completed_at}")
    print(f"\nAudit trace ({len(result.audit_trace)} events):")
    for event in result.audit_trace:
        print(f"  [{event['event']}] {event['timestamp']}")


if __name__ == "__main__":
    main()
