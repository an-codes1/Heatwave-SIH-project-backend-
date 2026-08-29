"""Notification provider factory.

Dry-run is the default: nothing is ever transmitted unless
NOTIFICATION_DRY_RUN=false AND the relevant Twilio credentials are set.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.notifications.base import (
    DryRunProvider,
    NotificationProvider,
)
from app.services.notifications.twilio_provider import (
    TwilioSmsProvider,
)


def get_notification_provider() -> NotificationProvider:
    if settings.notification_dry_run:
        return DryRunProvider()

    return TwilioSmsProvider(
        settings.twilio_account_sid,
        settings.twilio_auth_token,
        settings.twilio_sms_from,
    )