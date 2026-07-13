# Agentic AI Framework with NIST 800-53 and AI RMF Governance

<img src="https://raw.githubusercontent.com/kmb40/Artifacts/main/ai/security/linkedin-post-image-blue.jpg" alt="Governance belongs inside the agent, not beside it" width="50%">


A Python framework for building autonomous AI agents with governance controls mapped directly to NIST SP 800-53 and the NIST AI Risk Management Framework.

Built as part of an enterprise AI governance content series by Kyle M. Brown.

---

## Why This Exists

Most agentic AI examples show you how to build the agent.
None of them show you where the governance goes.

This repo treats governance as a first-class architecture concern. Every module carries inline NIST 800-53 and AI RMF annotations. You know exactly which control applies, where it lives in the code, and why it matters.

---

## Architecture

```
Perceive >> Reason >> Act >> Evaluate
   |            |         |         |
MemoryStore  Planner  ToolRegistry  Planner.evaluate()
                |         |
           Guardrails  AuditLogger + ObservabilityLayer
```

### Component to Control Mapping

| Component | File | NIST 800-53 | AI RMF |
|---|---|---|---|
| Agent Runtime | `agent/runtime.py` | SA-8, PL-2, AU-12 | MAP 1.0, MANAGE 2.2 |
| Memory Store | `agent/memory.py` | SC-28, AC-3, SI-12 | MANAGE 2.2 |
| Planner | `agent/planner.py` | SA-8, PL-2, CM-7 | MAP 1.0, MAP 2.0 |
| Audit Logger | `governance/audit.py` | AU-2, AU-9, AU-12 | GOVERN 1.7, MEASURE 4.1 |
| Guardrails | `governance/guardrails.py` | AC-6, CM-7, SI-10 | GOVERN 6.1, GOVERN 6.2, MANAGE 1.3 |
| Observability | `governance/observability.py` | SI-7, IR-6 | MEASURE 1.1, MEASURE 2.5, MEASURE 2.8 |
| Tool Registry | `tools/registry.py` | CM-7, SA-9, AC-6 | MANAGE 1.3, MAP 5.1 |

---

## Project Structure

```
agent-nist-framework/
├── agent/
│   ├── __init__.py
│   ├── runtime.py          # Core perceive > reason > act > evaluate loop
│   ├── memory.py           # TTL-scoped memory store
│   └── planner.py          # Goal decomposition and evaluation
├── governance/
│   ├── __init__.py
│   ├── audit.py            # Append-only audit logger (AU-2, AU-9)
│   ├── guardrails.py       # Runtime policy enforcement (AC-6, GOVERN 6.1)
│   └── observability.py    # Behavioral monitoring and drift detection
├── tools/
│   ├── __init__.py
│   └── registry.py         # Tool registration and dispatch (CM-7)
├── tests/
│   └── test_agent.py       # Unit and integration tests
├── example.py              # Runnable demo
├── requirements.txt
└── README.md
```

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/yourusername/agent-nist-framework.git
cd agent-nist-framework

# Install dependencies
pip install -r requirements.txt

# Run the example
python example.py

# Run tests
pytest tests/ -v
```

### What You Will See

Running `python example.py` produces terminal output and JSON audit logs saved to `logs/audit/`.

The terminal shows a live session trace: the agent receives a goal, builds a plan, executes a step, and closes the session. Every event is timestamped and labeled.

The JSON files in `logs/audit/` are the immutable audit records for that session. One file per run, named by session ID. This is NIST AU-2 and AU-9 working automatically in the background.

The outcome will read `goal_not_verified`. That is expected. The planner is currently a stub with no real reasoning engine behind it. The framework, the governance hooks, and the audit trail are all fully operational. Connecting a live LLM is the next step.

Running `pytest tests/ -v` confirms all 14 tests pass across memory, guardrails, planner, and runtime components.

---

## Building With the Framework

Once you have confirmed the Quick Start works, you can import the agent directly into your own project.

```python
from agent.runtime import AgentConfig, AgentRuntime

config = AgentConfig(
    name="security-ops-agent",
    allowed_tools=["reasoning", "file_read", "http_get"],
    max_steps=5,
    dry_run=False,
)

agent = AgentRuntime(config=config)

result = agent.run(
    goal="Analyze threat surface and identify unpatched vulnerabilities",
    context={"environment": "production"},
)

print(result.outcome)
print(result.audit_trace)
```

The difference between this and the Quick Start is intent. The Quick Start confirms the framework runs. This is how you embed it inside a larger system and drive it programmatically toward your own goals.

---

## Extending the Framework

### Add a Custom Tool

```python
from tools.registry import register

@register("vulnerability_scanner")
def handle_vuln_scan(action: str, parameters: dict) -> dict:
    # Your implementation here
    return {"status": "success", "findings": [...]}
```

### Add a Custom Guardrail Rule

```python
from governance.guardrails import GuardrailRule

agent.guardrails.add_rule(GuardrailRule(
    name="no_production_writes",
    description="Block any write to production databases",
    blocked_actions=["insert", "update", "upsert"],
))
```

The framework was designed so that new tools and rules plug in without touching the core runtime. Your governance policy stays separate from your agent logic. That separation is intentional and important.

### Connect a Real LLM (Anthropic Claude)

In `agent/planner.py`, replace `_decompose_goal` with a real reasoning call:

```python
import anthropic

client = anthropic.Anthropic()

def _decompose_goal(self, goal: str, context: dict) -> list[TaskStep]:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=self._build_tool_schemas(),
        messages=[{"role": "user", "content": goal}],
    )
    return self._parse_tool_use(response)
```

This is the step that turns the framework into a fully autonomous agent. Everything else is already in place.

---

## Production Considerations

| Concern | Recommendation |
|---|---|
| Memory encryption (SC-28) | Back MemoryStore with Redis plus TLS or AWS Secrets Manager |
| Audit log immutability (AU-9) | Ship logs to CloudTrail, Splunk, or a WORM S3 bucket |
| Observability (MEASURE 2.8) | Emit metrics to Datadog, Prometheus, or a SIEM |
| Tool allowlist (CM-7) | Enforce via environment config rather than hardcoded lists |
| LLM provider (SA-9) | Document your model provider as an external system dependency |

---

## Framework References

- [NIST SP 800-53 Rev 5](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)
- [NIST AI Risk Management Framework 1.0](https://airc.nist.gov/RMF)
- [NIST AI RMF Playbook](https://airc.nist.gov/Docs/2)
- [Anthropic Claude API](https://docs.anthropic.com)

---

## Author

**Kyle M. Brown**
Solutions Architect, Enterprise AI
Author of Agentic Artificial Intelligence

Part of the AI Governance in Practice LinkedIn series.

---

## License

MIT. Use freely with attribution.
