from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    AlertChannel,
    AlertStatus,
    ThermalScenario,
)


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_code: str = Field(description="Unique station code.")
    station_name: str | None = Field(description="Human-readable name.")
    latitude: float = Field(description="Latitude, EPSG:4326.")
    longitude: float = Field(description="Longitude, EPSG:4326.")
    source: str | None = Field(description="Data provider.")
    is_active: bool = True


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_code: str = Field(description="Zone code (e.g. W1).")
    zone_name: str
    zone_type: str = Field(description="Always 'ward' for BMC wards.")
    population: int | None = Field(
        description="Total ward population from BMC census attributes."
    )
    source: str | None


class VulnerabilityOut(BaseModel):
    zone_code: str
    zone_name: str
    total_population: int | None = Field(
        description="Total ward population."
    )
    population_density_per_km2: float | None
    vulnerability_score: float | None = Field(
        description="Provisional 0-100 demographic vulnerability score."
    )
    reference_year: int | None
    source: str | None


class ThermalIndexOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    utci_c: float | None = Field(
        description="Universal Thermal Climate Index, degrees Celsius."
    )
    wbgt_c: float | None = Field(
        description="Wet-bulb globe temperature, degrees Celsius."
    )
    heat_index_c: float | None = Field(
        description="Heat index, degrees Celsius."
    )
    thermal_risk_level: str | None = Field(
        description="UTCI-derived stress category."
    )
    scenario: ThermalScenario = Field(
        description="Exposure scenario (shade or sun-exposed)."
    )
    calculation_type: str = Field(
        description="Raw calculation type string (retained for compat)."
    )
    valid_for: datetime = Field(
        description="Timestamp the thermal value is valid for (ISO-8601)."
    )
    generated_at: datetime = Field(
        description="Timestamp the value was calculated (ISO-8601)."
    )
    methodology: str | None = Field(
        description="Summary of the calculation methodology."
    )


class ForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    forecast_for: datetime = Field(
        description="Local validity timestamp (ISO-8601)."
    )
    generated_at: datetime = Field(
        description="Timestamp the forecast was issued (ISO-8601)."
    )
    air_temperature_c: float | None
    relative_humidity_pct: float | None
    wind_speed_ms: float | None
    solar_radiation_wm2: float | None
    direct_radiation_wm2: float | None
    diffuse_radiation_wm2: float | None
    direct_normal_irradiance_wm2: float | None
    atmospheric_pressure_hpa: float | None
    source: str | None


class RiskPredictionOut(BaseModel):
    zone_code: str
    prediction_for: datetime = Field(
        description="Local day the risk applies to (ISO-8601)."
    )
    generated_at: datetime = Field(
        description="Timestamp the prediction was issued (ISO-8601)."
    )
    thermal_risk_score: float | None = Field(
        description="Composite 0-100 heat-health risk proxy score."
    )
    mortality_risk_score: float | None = None
    hospitalization_risk_score: float | None = None
    overall_risk_level: str | None = Field(
        description="LOW | MODERATE | HIGH | VERY_HIGH | EXTREME."
    )
    model_name: str | None
    model_version: str | None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_code: str | None = None
    alert_level: str = Field(
        description="LOW | MODERATE | HIGH | VERY_HIGH | EXTREME."
    )
    alert_message: str
    recommended_action: str | None
    status: AlertStatus
    channel: AlertChannel | None
    created_at: datetime
    sent_at: datetime | None
    dry_run: bool = Field(
        description="True when the alert was only simulated, not delivered."
    )


class AlertGenerationOut(BaseModel):
    generated: int
    deduplicated: int
    below_threshold: int
    dry_run_default: bool = Field(
        description="Current global notification dry-run setting."
    )
    alerts: list[AlertOut]


class RiskZoneFeature(BaseModel):
    type: str = "Feature"
    geometry: dict = Field(..., description="GeoJSON geometry, EPSG:4326")
    properties: dict


class RiskZonesResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[RiskZoneFeature]