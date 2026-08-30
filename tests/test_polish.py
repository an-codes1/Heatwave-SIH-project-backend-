"""Polish-pass API tests: pagination, geo best practice, errors, CORS,
security (no secret leakage), and notification dry-run semantics."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.main import app

client = TestClient(app)
client2 = TestClient(app)

INDIA = ZoneInfo("Asia/Kolkata")


def test_thermal_history_pagination():
    page1 = client.get(
        "/api/v1/thermal/history?limit=5&offset=0"
    ).json()
    page2 = client.get(
        "/api/v1/thermal/history?limit=5&offset=5"
    ).json()

    assert len(page1) == 5
    assert len(page2) == 5

    newest = page1[0]["valid_for"]
    oldest_page1 = page1[-1]["valid_for"]
    oldest_page2 = page2[-1]["valid_for"]

    assert oldest_page1 <= newest
    assert oldest_page2 <= oldest_page1


def test_thermal_history_limit_capped():
    response = client.get(
        "/api/v1/thermal/history?limit=501"
    )
    assert response.status_code == 422


def test_thermal_history_negative_offset_rejected():
    response = client.get(
        "/api/v1/thermal/history?offset=-1"
    )
    assert response.status_code == 422


def test_thermal_latest_includes_scenario_and_generated_at():
    body = client.get("/api/v1/thermal/latest").json()
    assert body
    for item in body:
        assert item["scenario"] in (
            "observed_reference_shade",
            "observed_sun_exposed",
            "forecast_reference_shade",
            "forecast_sun_exposed",
        )
        assert item["generated_at"]
        assert item["valid_for"]
        assert item["utci_c"] is not None


def test_forecast_response_shape():
    body = client.get("/api/v1/forecast").json()
    assert len(body) >= 120
    for item in body:
        assert item["forecast_for"]
        assert item["generated_at"]
        assert item["source"] is not None
        assert (
            "air_temperature_c" in item
            and "solar_radiation_wm2" in item
        )


def test_geojson_coordinates_are_epsg4326():
    fc = client.get("/api/v1/risk-zones").json()
    assert fc["type"] == "FeatureCollection"

    def first_point(coords):
        while isinstance(coords, list) and coords:
            if isinstance(coords[0], (int, float)):
                return coords
            coords = coords[0]
        return coords

    for feature in fc["features"]:
        assert feature["type"] == "Feature"
        lon, lat = first_point(feature["geometry"]["coordinates"])
        assert -180 <= lon <= 180 and -90 <= lat <= 90
        assert 84.0 <= lon <= 87.0
        assert 19.0 <= lat <= 22.0
        prop = feature["properties"]
        assert {"zone_code", "zone_name", "population",
                "population_density", "vulnerability_score",
                "thermal_risk_score", "overall_risk_level",
                "valid_for"}.issubset(prop.keys())
        datetime.fromisoformat(prop["valid_for"])


def test_risk_zones_day_filter_returns_67():
    day = "2026-09-02"
    fc = client.get(
        "/api/v1/risk-zones",
        params={"forecast_day": day},
    ).json()

    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 67

    for feature in fc["features"]:
        valid = datetime.fromisoformat(
            feature["properties"]["valid_for"]
        ).astimezone(INDIA).date().isoformat()
        assert valid == day


def test_risk_zones_invalid_level_rejected():
    response = client.get(
        "/api/v1/risk-zones", params={"level": "COOL"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("path", ["/health", "/api/v1/zones", "/openapi.json"])
def test_no_secret_leakage(path):
    secrets = [
        settings.twilio_account_sid,
        settings.twilio_auth_token,
        settings.alert_recipient_phone,
    ]
    text = client.get(path).text

    for secret in secrets:
        if secret:
            assert secret not in text


def test_db_failure_returns_503(monkeypatch):
    import app.services.queries as queries

    def boom(*_args, **_kwargs):
        raise SQLAlchemyError("connection refused")

    monkeypatch.setattr(queries, "list_stations", boom)

    response = client.get("/api/v1/stations")
    assert response.status_code == 503
    assert "traceback" not in response.text.lower()
    assert "password" not in response.text.lower()


def test_cors_preflight_localhost_allowed():
    response = client2.options(
        "/api/v1/zones",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:3000"
    )


def test_cors_origins_configured_not_wildcard():
    assert "http://localhost:3000" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins
    assert "*" not in settings.cors_origins


def test_alert_dry_run_fields():
    headers = {"X-Admin-Key": "test-admin-key"}
    generation = client.post(
        "/api/v1/alerts/generate",
        headers=headers,
    ).json()
    assert "dry_run_default" in generation

    alerts = client.get("/api/v1/alerts").json()
    if alerts:
        assert "dry_run" in alerts[0]

    pending = [a for a in alerts if a["status"] == "pending"]
    if pending:
        sent = client.post(
            f"/api/v1/alerts/{pending[0]['id']}/send",
            headers=headers,
        ).json()
        assert sent["dry_run"] is True
        assert sent["status"] == "sent"


def test_openapi_tags_declared():
    schema = client.get("/openapi.json").json()
    declared = [t["name"] for t in schema["tags"]]
    for expected in ("Health", "Stations", "Zones", "Thermal",
                     "Forecast", "Risk", "Alerts"):
        assert expected in declared