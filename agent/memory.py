"""
agent/memory.py

Agent memory store — short and long-term context retention.

NIST 800-53 mappings:
    SC-28 — Data at rest protection (encrypt sensitive memory entries)
    AC-3  — Access enforcement (memory scoped per session)
    SI-12 — Information management and retention

AI RMF mappings:
    MANAGE 2.2 — Mechanisms to sustain AI risk management over time
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    key: str
    value: Any
    stored_at: float = field(default_factory=time.time)
    ttl_seconds: int = 3600

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.stored_at) > self.ttl_seconds


class MemoryStore:
    """
    In-process memory store with TTL-based expiration.

    In production, back this with an encrypted store (Redis with TLS,
    or a secrets-aware key-value service) to satisfy SC-28.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self._store: dict[str, MemoryEntry] = {}
        self._ttl = ttl_seconds

    def store(self, key: str, value: Any) -> None:
        """Write a value into memory. Overwrites existing keys."""
        self._store[key] = MemoryEntry(key=key, value=value, ttl_seconds=self._ttl)

    def retrieve(self, query: str) -> dict[str, Any]:
        """
        Retrieve all non-expired entries relevant to the query.
        Simple substring match — swap with vector similarity in production.
        """
        self._evict_expired()
        return {
            k: v.value
            for k, v in self._store.items()
            if query.lower() in k.lower()
        }

    def get(self, key: str) -> Any | None:
        """Retrieve a single entry by exact key."""
        entry = self._store.get(key)
        if entry is None or entry.is_expired:
            return None
        return entry.value

    def clear(self) -> None:
        """Clear all memory entries. Call at session end."""
        self._store.clear()

    def _evict_expired(self) -> None:
        expired = [k for k, v in self._store.items() if v.is_expired]
        for k in expired:
            del self._store[k]

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._store)
