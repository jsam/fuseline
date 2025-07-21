from __future__ import annotations

from abc import ABC, abstractmethod


class Tracer(ABC):
    """Interface for recording workflow execution events."""

    @abstractmethod
    def record(self, event: dict) -> None:
        """Persist a trace event."""
