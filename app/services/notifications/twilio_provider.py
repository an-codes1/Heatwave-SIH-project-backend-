"""Twilio SMS notification provider.

Credentials are read from environment variables only. When credentials
are not configured the provider raises ValueError so callers can fall
back to dry-run mode.
"""

from __future__ import annotations

import httpx

from app.services.notifications.base import NotificationProvider


class TwilioSmsProvider(NotificationProvider):
    def __init__(
        self,
        account_sid: str | None,
        auth_token: str | None,
        sms_from: str | None,
    ) -> None:
        if not account_sid or not auth_token or not sms_from:
            raise ValueError(
                "Twilio SMS credentials are not configured "
                "(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                "TWILIO_SMS_FROM)."
            )

        self.account_sid = account_sid
        self.auth_token = auth_token
        self.sms_from = sms_from

    def send(self, recipient: str, body: str) -> str:
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Messages.json"
        )

        response = httpx.post(
            url,
            auth=(self.account_sid, self.auth_token),
            data={
                "To": recipient,
                "From": self.sms_from,
                "Body": body,
            },
            timeout=20.0,
        )

        response.raise_for_status()

        return str(response.json().get("sid", "twilio"))