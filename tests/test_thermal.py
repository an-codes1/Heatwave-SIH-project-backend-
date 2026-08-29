import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from thermal.mrt import (
    Scenario,
    reference_shade_mrt,
    solar_delta_mrt,
    sun_exposed_mrt,
)
from thermal.risk_classification import (
    classify,
    heat_severity_score,
    utci_stress_category,
)
from thermal.solar_position import solar_positions
from thermal.utci import calculate_utci


INDIA = ZoneInfo("Asia/Kolkata")


def test_reference_utci_known_case():
    result = calculate_utci(
        air_temperature_c=25.0,
        mean_radiant_temperature_c=25.0,
        wind_speed_ms=1.0,
        relative_humidity_pct=50.0,
    )

    assert result.valid is True
    assert result.utci_c is not None
    assert result.utci_c == pytest.approx(24.64, abs=0.1)
    assert result.stress_category == "no thermal stress"


def test_reference_shade_mrt_equals_air_temperature():
    result = reference_shade_mrt(35.0)

    assert result.scenario is Scenario.REFERENCE_SHADE
    assert result.mean_radiant_temperature_c == 35.0
    assert result.delta_mrt_c == 0.0


def test_zero_solar_gain_at_night():
    assert solar_delta_mrt(800.0, 0.0) == 0.0
    assert solar_delta_mrt(800.0, -10.0) == 0.0
    assert solar_delta_mrt(None, 45.0) == 0.0
    assert solar_delta_mrt(0.0, 45.0) == 0.0


def test_positive_daytime_delta_mrt():
    delta = solar_delta_mrt(800.0, 60.0)

    assert delta > 0.0

    night = sun_exposed_mrt(35.0, 800.0, -5.0)
    day = sun_exposed_mrt(35.0, 800.0, 60.0)

    assert night.mean_radiant_temperature_c == 35.0
    assert day.mean_radiant_temperature_c > night.mean_radiant_temperature_c


def test_utci_categories():
    assert utci_stress_category(25.0) == "no thermal stress"
    assert utci_stress_category(28.0) == "moderate heat stress"
    assert utci_stress_category(35.0) == "strong heat stress"
    assert utci_stress_category(42.0) == "very strong heat stress"
    assert utci_stress_category(47.0) == "extreme heat stress"


def test_severity_score_bounds():
    assert heat_severity_score(26.0) == 0.0
    assert heat_severity_score(46.0) == 100.0
    assert 0.0 <= heat_severity_score(35.0) <= 100.0


def test_classify_none_input():
    assert classify(None) is None
    result = classify(35.0)
    assert result.stress_category == "strong heat stress"


def test_solar_positions_returns_elevation_and_azimuth():
    times = [
        datetime(2025, 5, 1, 12, tzinfo=INDIA),
        datetime(2025, 5, 1, 0, tzinfo=INDIA),
    ]

    elevations, azimuths = solar_positions(times)

    assert len(elevations) == 2
    assert len(azimuths) == 2
    assert elevations[0] > 0
    assert elevations[1] < 0


def test_radiation_never_used_directly_as_mrt():
    air = 35.0
    radiation = 800.0

    shade = reference_shade_mrt(air)
    exposed = sun_exposed_mrt(air, radiation, 60.0)

    assert shade.mean_radiant_temperature_c == air
    assert exposed.mean_radiant_temperature_c != radiation
    assert exposed.mean_radiant_temperature_c < radiation * 0.5
    assert exposed.delta_mrt_c == pytest.approx(
        solar_delta_mrt(radiation, 60.0), abs=1e-6
    )


def test_sun_exposed_mrt_not_below_shade_mrt_during_day():
    exposed = sun_exposed_mrt(35.0, 800.0, 60.0)
    shade = reference_shade_mrt(35.0)

    assert exposed.mean_radiant_temperature_c >= (
        shade.mean_radiant_temperature_c
    )