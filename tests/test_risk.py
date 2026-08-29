from risk.heat_health_risk import (
    RiskLevel,
    heat_health_risk,
    risk_level,
)
from risk.vulnerability import (
    percentile_rank,
    provisional_vulnerability_score,
)


def test_percentile_rank():
    values = [1.0, 2.0, 3.0, 4.0]

    assert percentile_rank(values, 1.0) == 12.5
    assert percentile_rank(values, 4.0) == 87.5
    assert percentile_rank([], 5.0) == 0.0


def test_provisional_vulnerability_score_without_data():
    score = provisional_vulnerability_score([], [], None, None)
    assert score == 0.0


def test_provisional_vulnerability_score_uses_both_terms():
    populations = [1000.0, 2000.0, 3000.0, 4000.0]
    densities = [100.0, 200.0, 300.0, 400.0]

    score = provisional_vulnerability_score(
        populations,
        densities,
        4000.0,
        400.0,
    )

    assert score == 87.5


def test_risk_level_boundaries():
    assert risk_level(10.0) is RiskLevel.LOW
    assert risk_level(25.0) is RiskLevel.MODERATE
    assert risk_level(50.0) is RiskLevel.HIGH
    assert risk_level(70.0) is RiskLevel.VERY_HIGH
    assert risk_level(90.0) is RiskLevel.EXTREME


def test_heat_health_risk_weights_and_bounds():
    score, level = heat_health_risk(
        thermal_severity=100.0,
        vulnerability=0.0,
    )

    assert score >= 60.0
    assert level is RiskLevel.VERY_HIGH

    score, level = heat_health_risk(
        thermal_severity=150.0,
        vulnerability=-20.0,
    )

    assert 0.0 <= score <= 100.0
    assert level is RiskLevel.VERY_HIGH