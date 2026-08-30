"""Security hardening tests: admin-key auth, security headers, and
safe dry-run notification behavior.

The admin key is injected by tests/conftest.py as "test-admin-key".
Tests never contact Twilio (dry-run is forced in conftest).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ADMIN_KEY = "test-admin-key"

SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}


def _auth() -> dict[str, str]:
    return {"X-Admin-Key": ADMIN_KEY}


def test_admin_generate_missing_key_401():
    response = client.post("/api/v1/alerts/generate")
    assert response.status_code == 401


def test_admin_generate_wrong_key_403():
    response = client.post(
        "/api/v1/alerts/generate",
        headers={"X-Admin-Key": "not-the-secret"},
    )
    assert response.status_code == 403


def test_admin_generate_correct_key_success():
    response = client.post("/api/v1/alerts/generate", headers=_auth())
    assert response.status_code == 200
    body = response.json()
    assert "generated" in body
    assert "deduplicated" in body


def test_admin_send_missing_key_401():
    response = client.post("/api/v1/alerts/1/send")
    assert response.status_code == 401


def test_admin_send_wrong_key_403():
    response = client.post(
        "/api/v1/alerts/1/send",
        headers={"X-Admin-Key": "wrong"},
    )
    assert response.status_code == 403


def test_public_get_endpoints_work_without_admin_key():
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/zones").status_code == 200
    assert client.get("/api/v1/thermal/latest").status_code == 200
    assert client.get("/api/v1/risk-zones").status_code == 200


def test_security_headers_present():
    for path in ("/health", "/api/v1/zones", "/docs"):
        response = client.get(path)
        for name, value in SECURITY_HEADERS.items():
            assert response.headers.get(name) == value
        assert (
            response.headers.get("permissions-policy")
            is not None
        )


def test_security_headers_present_on_errors():
    response = client.post("/api/v1/alerts/generate")
    assert response.status_code == 401
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value


def test_notification_dry_run_still_safe_with_key():
    client.post("/api/v1/alerts/generate", headers=_auth())
    alerts = client.get("/api/v1/alerts").json()
    pending = [a for a in alerts if a["status"] == "pending"]

    assert pending, "expected at least one pending alert"

    response = client.post(
        f"/api/v1/alerts/{pending[0]['id']}/send",
        headers=_auth(),
    )
    assert response.status_code == 200
    sent = response.json()
    assert sent["dry_run"] is True
    assert sent["status"] == "sent"


def test_admin_key_never_appears_in_responses():
    body = client.post(
        "/api/v1/alerts/generate",
        headers=_auth(),
    ).text
    assert ADMIN_KEY not in body

    wrong = client.post(
        "/api/v1/alerts/generate",
        headers={"X-Admin-Key": "totally-wrong-key"},
    ).text
    assert ADMIN_KEY not in wrong
    assert "not-the-secret" not in wrong