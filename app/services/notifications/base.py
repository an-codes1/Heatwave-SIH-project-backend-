"""Notification provider abstraction for heat-health alerts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.core.security import mask_sensitive


class NotificationProvider(ABC):
    """Contract for sending alert notifications to recipients."""

    @abstractmethod
    def send(self, recipient: str, body: str) -> str:
        """Send a message; return a provider message identifier."""


class DryRunProvider(NotificationProvider):
    """Simulates sending; logs the intended message instead."""

    def send(self, recipient: str, body: str) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        marker = timestamp.replace(":", "-").replace(
            "-", "", 3
        )

        print(
            f"[DRY-RUN NOTIFICATION] to={mask_sensitive(recipient)} "
            f"at={timestamp}\n{body}"
        )

        return f"dry-run:{marker}"