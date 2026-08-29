from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_code: str
    station_name: str | None
    latitude: float
    longitude: float
    source: str | None
    is_active: bool


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_code: str
    zone_name: str
    zone_type: str
    population: int | None
    source: str | None


class VulnerabilityOut(BaseModel):
    zone_code: str
    zone_name: str
    total_population: int | None
    population_density_per_km2: float | None
    vulnerability_score: float | None
    reference_year: int | None
    source: str | None


class ThermalIndexOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    utci_c: float | None
    thermal_risk_level: str | None
    calculation_type: str
    valid_for: datetime
    methodology: str | None


class RiskPredictionOut(BaseModel):
    zone_code: str
    prediction_for: datetime
    thermal_risk_score: float | None
    mortality_risk_score: float | None = None
    hospitalization_risk_score: float | None = None
    overall_risk_level: str | None
    model_name: str | None
    model_version: str | None


class ForecastOut(BaseModel):
    forecast_for: datetime
    air_temperature_c: float | None
    relative_humidity_pct: float | None
    wind_speed_ms: float | None
    solar_radiation_wm2: float | None
    direct_normal_irradiance_wm2: float | None
    atmospheric_pressure_hpa: float | None
    source: str | None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_code: str | None = None
    alert_level: str
    alert_message: str
    recommended_action: str | None
    status: str
    channel: str | None
    created_at: datetime
    sent_at: datetime | None


class AlertGenerationOut(BaseModel):
    generated: int
    deduplicated: int
    below_threshold: int
    alerts: list[AlertOut]


class RiskZoneFeature(BaseModel):
    type: str = "Feature"
    geometry: dict = Field(..., description="GeoJSON geometry")
    properties: dict


class RiskZonesResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[RiskZoneFeature]