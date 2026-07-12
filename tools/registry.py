"""
tools/registry.py

Tool registry and execution dispatcher.
Only registered tools can be called by the agent.

NIST 800-53 mappings:
    CM-7  — Least functionality: approved tools explicitly enumerated
    SA-9  — External system services: third-party tools documented
    AC-6  — Least privilege: each tool scoped to minimum required access

AI RMF mappings:
    MANAGE 1.3 — Risk responses for each registered tool capability
    MAP 5.1    — Likelihood of risks from third-party tool dependencies
"""

from typing import Any, Callable


# Tool handler type: (action: str, parameters: dict) -> dict
ToolHandler = Callable[[str, dict[str, Any]], dict[str, Any]]

_REGISTRY: dict[str, ToolHandler] = {}


def register(tool_name: str):
    """
    Decorator to register a function as a named tool handler.

    Usage:
        @register("web_search")
        def handle_web_search(action: str, parameters: dict) -> dict:
            ...
    """
    def decorator(fn: ToolHandler) -> ToolHandler:
        _REGISTRY[tool_name] = fn
        return fn
    return decorator


class ToolRegistry:
    """
    Dispatches agent tool calls to registered handlers.
    Raises ValueError for unregistered tools — never silently fails.
    """

    @staticmethod
    def execute(tool: str, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        handler = _REGISTRY.get(tool)
        if handler is None:
            raise ValueError(
                f"Tool '{tool}' is not registered. "
                f"Available tools: {list(_REGISTRY.keys())}"
            )
        return handler(action, parameters)

    @staticmethod
    def list_tools() -> list[str]:
        return list(_REGISTRY.keys())


# ── Built-in stub tools ────────────────────────────────────────────────────────
# Replace these stubs with real implementations for your use case.

@register("reasoning")
def handle_reasoning(action: str, parameters: dict) -> dict:
    """
    Stub reasoning tool. In production, call your LLM here.
    Example: Anthropic Claude with structured tool use.
    """
    return {
        "status": "success",
        "tool": "reasoning",
        "action": action,
        "result": f"Reasoning step '{action}' completed with params: {list(parameters.keys())}",
    }


@register("file_read")
def handle_file_read(action: str, parameters: dict) -> dict:
    """Read a local file. Scoped to read-only (AC-6)."""
    import os
    path = parameters.get("path", "")
    if not os.path.exists(path):
        return {"status": "error", "error": f"File not found: {path}"}
    with open(path) as f:
        content = f.read()
    return {"status": "success", "content": content[:4096]}  # truncate for safety


@register("http_get")
def handle_http_get(action: str, parameters: dict) -> dict:
    """
    HTTP GET only — no POST, PUT, DELETE (least privilege per AC-6).
    In production, add domain allowlist enforcement.
    """
    import urllib.request
    url = parameters.get("url", "")
    if not url.startswith("https://"):
        return {"status": "error", "error": "Only HTTPS URLs are permitted"}
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return {"status": "success", "status_code": resp.status, "url": url}
    except Exception as e:
        return {"status": "error", "error": str(e)}
