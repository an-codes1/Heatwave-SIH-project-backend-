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
        from_number: str | None,
    ) -> None:
        if not account_sid or not auth_token or not from_number:
            raise ValueError(
                "Twilio SMS credentials are not configured "
                "(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                "TWILIO_FROM_NUMBER)."
            )

        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

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
                "From": self.from_number,
                "Body": body,
            },
            timeout=20.0,
        )

        response.raise_for_status()

        return str(response.json().get("sid", "twilio"))