from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ADMIN_KEY = "test-admin-key"


def _auth() -> dict[str, str]:
    return {"X-Admin-Key": ADMIN_KEY}


def test_generate_alerts_and_idempotent():
    first = client.post("/api/v1/alerts/generate", headers=_auth())
    assert first.status_code == 200
    body = first.json()
    assert body["generated"] >= 0
    assert body["deduplicated"] >= 0
    assert isinstance(body["alerts"], list)

    second = client.post("/api/v1/alerts/generate", headers=_auth())
    assert second.status_code == 200
    assert second.json()["generated"] == 0
    assert second.json()["deduplicated"] >= 1

    alerts = client.get("/api/v1/alerts").json()
    assert len(alerts) >= 1
    assert all(
        a["status"] in ("pending", "sent") for a in alerts
    )


def test_send_alert_dry_run():
    alerts = client.get("/api/v1/alerts").json()
    pending = [a for a in alerts if a["status"] == "pending"]

    assert pending, "expected at least one pending alert"

    alert_id = pending[0]["id"]
    response = client.post(
        f"/api/v1/alerts/{alert_id}/send",
        headers=_auth(),
    )
    assert response.status_code == 200
    sent = response.json()
    assert sent["status"] == "sent"
    assert sent["sent_at"] is not None


def test_send_missing_alert_is_404():
    response = client.post(
        "/api/v1/alerts/99999999/send",
        headers=_auth(),
    )
    assert response.status_code == 404