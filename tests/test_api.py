from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_db():
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_stations():
    response = client.get("/api/v1/stations")
    assert response.status_code == 200
    stations = response.json()
    assert len(stations) >= 1
    assert stations[0]["station_code"].startswith("OPENMETEO")


def test_zones_returns_67_wards():
    response = client.get("/api/v1/zones")
    assert response.status_code == 200
    zones = response.json()
    assert len(zones) == 67
    assert all(z["zone_type"] == "ward" for z in zones)


def test_zone_by_code():
    response = client.get("/api/v1/zones/W1")
    assert response.status_code == 200
    assert response.json()["zone_code"] == "W1"


def test_zone_not_found():
    response = client.get("/api/v1/zones/ZZ999")
    assert response.status_code == 404


def test_zone_current_risk():
    response = client.get("/api/v1/zones/W1/current-risk")
    assert response.status_code == 200
    body = response.json()
    assert body["thermal_risk_score"] is not None
    assert body["overall_risk_level"] is not None
    assert body["mortality_risk_score"] is None


def test_zone_forecast_returns_five_days():
    response = client.get("/api/v1/zones/W1/forecast")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert all(p["mortality_risk_score"] is None for p in body)


def test_thermal_latest():
    response = client.get("/api/v1/thermal/latest")
    assert response.status_code == 200
    types = {i["calculation_type"] for i in response.json()}
    assert {
        "forecast_reference_shade",
        "forecast_sun_exposed",
    }.issubset(types)


def test_forecast_weather():
    response = client.get("/api/v1/forecast")
    assert response.status_code == 200
    assert len(response.json()) >= 120


def test_vulnerability():
    response = client.get("/api/v1/vulnerability")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 67
    assert all(v["vulnerability_score"] is not None for v in body)


def test_risk_zones_geojson():
    response = client.get("/api/v1/risk-zones")
    assert response.status_code == 200
    fc = response.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 67
    feature = fc["features"][0]
    assert feature["geometry"]["type"] == "MultiPolygon"
    assert feature["properties"]["overall_risk_level"] is not None


def test_risk_zones_level_filter():
    response = client.get(
        "/api/v1/risk-zones", params={"level": "EXTREME"}
    )
    assert response.status_code == 200
    features = response.json()["features"]
    assert all(
        f["properties"]["overall_risk_level"] == "EXTREME"
        for f in features
    )


def test_alerts_empty_list():
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)