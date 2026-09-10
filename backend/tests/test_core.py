import pytest
from datetime import datetime, timezone

from app.models import WeatherObservation, MarineObservation, WarningEvent, BoundaryStatus, PFZCandidate
from app.services.safety_calculator import calculate_safety, is_high_wave, is_severe_warning, is_cyclone
from app.geospatial.engine import haversine_km, check_boundary_status, calculate_pfz_score
from app.services.safety_calculator import WAVE_HIGH_THRESHOLD
from app.agents.critic import critic_agent
from app.agents.vision_anomaly import vision_anomaly_agent
from app.agents.orchestrator import planner_node, report_agent_node


def _weather(wind=10.0):
    return WeatherObservation(
        source="test", retrieved_at=datetime.now(timezone.utc),
        forecast_time=datetime.now(timezone.utc),
        latitude=13.0, longitude=80.0,
        wind_speed_kmh=wind, wind_direction_deg=180, temperature_c=28,
        precipitation_mm=0, weather_condition="Clear", is_demo=False,
    )


def _marine(wave=1.0):
    return MarineObservation(
        source="test", retrieved_at=datetime.now(timezone.utc),
        forecast_time=datetime.now(timezone.utc),
        latitude=13.0, longitude=80.0,
        wave_height_m=wave, wave_direction_deg=180, wave_period_s=8,
        swell_height_m=0.5, current_speed_ms=0.3, current_direction_deg=90,
        is_demo=False,
    )


def _warning(severity="YELLOW", title="Test", source="test"):
    return WarningEvent(
        id="w1", source=source, severity=severity, title=title,
        description="test warning", affected_area="test", effective_time=datetime.now(timezone.utc),
        is_active=True,
    )


class TestSafety:
    def test_calm_conditions_high_score(self):
        s = calculate_safety(_weather(wind=10), _marine(wave=0.8), [], None, [])
        assert s.score >= 80

    def test_high_wind_reduces_score(self):
        s = calculate_safety(_weather(wind=50), _marine(wave=0.8), [], None, [])
        assert s.score < 80

    def test_high_waves_reduce_score(self):
        s = calculate_safety(_weather(wind=10), _marine(wave=3.0), [], None, [])
        assert s.score < 75

    def test_red_warning_triggers_critical(self):
        s = calculate_safety(_weather(wind=10), _marine(wave=0.5), [_warning("RED", "Cyclone Alert")], None, [])
        assert s.score <= 30
        assert s.critical_override is True

    def test_pfz_bonus_added(self):
        pfz = [PFZCandidate(
            id="p1", latitude=13.2, longitude=80.3, score=80, distance_km=22,
            explanation="test", suitability="HIGH",
        )]
        s_no_pfz = calculate_safety(_weather(wind=10), _marine(wave=0.8), [], None, [])
        s_pfz = calculate_safety(_weather(wind=10), _marine(wave=0.8), [], None, pfz)
        assert s_pfz.score >= s_no_pfz.score

    def test_pfz_bonus_does_not_override_red_warning(self):
        pfz = [PFZCandidate(
            id="p2", latitude=13.2, longitude=80.3, score=95, distance_km=10,
            explanation="test", suitability="HIGH",
        )]
        s = calculate_safety(_weather(wind=10), _marine(wave=0.5), [_warning("RED", "Cyclone")], None, pfz)
        assert s.score <= 30
        assert s.critical_override is True


class TestAlertPredicates:
    def test_is_high_wave_true(self):
        assert is_high_wave(_marine(wave=WAVE_HIGH_THRESHOLD + 0.1))

    def test_is_high_wave_false(self):
        assert not is_high_wave(_marine(wave=1.0))

    def test_is_severe_warning_red(self):
        assert is_severe_warning([_warning("RED")])

    def test_is_severe_warning_orange(self):
        assert is_severe_warning([_warning("ORANGE")])

    def test_is_severe_warning_false_yellow(self):
        assert not is_severe_warning([_warning("YELLOW")])

    def test_is_cyclone_true(self):
        assert is_cyclone([_warning("RED", "Cyclone Mocha approaching")])

    def test_is_cyclone_false(self):
        assert not is_cyclone([_warning("RED", "High wave warning")])


class TestGeospatial:
    def test_haversine_known(self):
        d = haversine_km(13.0827, 80.2707, 18.9388, 72.8355)
        assert 1000 < d < 1200

    def test_haversine_zero(self):
        assert haversine_km(13.0, 80.0, 13.0, 80.0) == 0.0

    def test_boundary_normal_far_away(self):
        b = check_boundary_status(0.0, 60.0)
        assert b.status == "NORMAL"

    def test_boundary_normal_chennai(self):
        b = check_boundary_status(13.0827, 80.2707)
        assert not b.inside

    def test_pfz_score_optimal(self):
        score = calculate_pfz_score(sst=27.5, chlorophyll=1.5)
        assert score >= 70

    def test_pfz_score_low(self):
        score = calculate_pfz_score(sst=20.0, chlorophyll=0.1)
        assert score < 40


class TestRouting:
    def test_route_returns_result(self):
        from app.routing.astar import build_route_grid
        route = build_route_grid(13.0, 80.0, 13.5, 80.5, wave_height=1.5)
        assert route.direct_distance_km > 0
        assert route.orca_distance_km > 0
        assert len(route.direct_route) >= 2
        assert len(route.orca_route) >= 1

    def test_route_orca_risk_lower(self):
        from app.routing.astar import build_route_grid
        route = build_route_grid(13.0, 80.0, 13.5, 80.5, wave_height=2.5)
        assert route.orca_risk <= route.direct_risk


class TestAgentSafety:
    def test_greeting_skips_marine_agents(self):
        result = planner_node({
            "request_id": "test",
            "query": "hello",
            "language": "en",
            "trace": {"request_id": "test", "stages": []},
        })
        assert result["intent"] == "conversation"
        assert result["planned_agents"] == ["report"]

    def test_greeting_returns_conversational_response(self):
        result = report_agent_node({
            "request_id": "test",
            "query": "hello",
            "language": "en",
            "intent": "conversation",
            "planned_agents": ["report"],
            "trace": {"request_id": "test", "stages": []},
        })
        assert "marine query" in result["final_answer"].lower()

    def test_critic_overrides_pfz_for_severe_weather(self):
        result = critic_agent({"weather_data": {"severity": 3}, "pfz_score": 88, "messages": []})
        assert result["pfz_score"] == 0
        assert result["is_safe"] is False
        assert result["messages"][0]["priority"] == "high"

    def test_critic_preserves_pfz_for_normal_weather(self):
        result = critic_agent({"weather_data": {"severity": 2}, "pfz_score": 88, "messages": []})
        assert result["pfz_score"] == 88
        assert result["is_safe"] is True
        assert result["messages"] == []

    def test_dark_vessel_alert_requires_missing_ais_match(self):
        result = vision_anomaly_agent(
            {"latitude": 13.1, "longitude": 80.3},
            [],
            wake_detected=True,
        )
        assert result["alerts"][0]["tag"] == "DARK_VESSEL_DETECTED"

    def test_dark_vessel_with_ais_match_is_not_alerted(self):
        result = vision_anomaly_agent(
            {"latitude": 13.1, "longitude": 80.3},
            [{"latitude": 13.101, "longitude": 80.301, "mmsi": "123456789"}],
            wake_detected=True,
        )
        assert result["detected"] is False
