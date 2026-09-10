from __future__ import annotations
from typing import Any, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import re
import html


def _sanitize(text: str) -> str:
    cleaned = html.escape(text.strip())
    cleaned = re.sub(r'[<>{}]', '', cleaned)
    return cleaned[:2000]


class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class TimeWindow(BaseModel):
    start: datetime
    end: datetime
    description: str = ""


class WeatherObservation(BaseModel):
    source: str
    retrieved_at: datetime
    forecast_time: datetime
    latitude: float
    longitude: float
    wind_speed_kmh: float
    wind_direction_deg: float
    temperature_c: float
    precipitation_mm: float
    weather_condition: str
    is_demo: bool = False


class MarineObservation(BaseModel):
    source: str
    retrieved_at: datetime
    forecast_time: datetime
    latitude: float
    longitude: float
    wave_height_m: float
    wave_direction_deg: float
    wave_period_s: float
    swell_height_m: float = 0.0
    current_speed_ms: float = 0.0
    current_direction_deg: float = 0.0
    is_demo: bool = False


class OceanObservation(BaseModel):
    source: str
    retrieved_at: datetime
    latitude: float
    longitude: float
    sst_celsius: Optional[float] = None
    chlorophyll_mgm3: Optional[float] = None
    data_type: Literal["EO", "MODEL", "DEMO"] = "EO"
    is_demo: bool = False


class WarningEvent(BaseModel):
    id: str
    source: str
    severity: Literal["INFO", "YELLOW", "ORANGE", "RED"]
    title: str
    description: str
    affected_area: str
    effective_time: datetime
    expiry_time: Optional[datetime] = None
    is_active: bool = True


class GeoRestriction(BaseModel):
    id: str
    name: str
    type: Literal["IMBL", "EEZ", "RESTRICTED", "PROTECTED"]
    geometry: dict
    description: str = ""


class BoundaryStatus(BaseModel):
    nearest_restriction_id: str
    nearest_restriction_name: str
    distance_km: float
    status: Literal["NORMAL", "YELLOW", "ORANGE", "RED"]
    inside: bool = False


class PFZCandidate(BaseModel):
    id: str
    latitude: float
    longitude: float
    score: float
    distance_km: float
    sst_celsius: Optional[float] = None
    chlorophyll_level: Optional[str] = None
    explanation: str
    suitability: Literal["HIGH", "MODERATE", "LOW"]


class SafetyFactor(BaseModel):
    name: str
    value: str
    penalty: float
    status: Literal["GOOD", "MODERATE", "CAUTION", "WARNING", "CRITICAL"]


class SafetyAssessment(BaseModel):
    score: int
    label: Literal["EXCELLENT", "GOOD", "CAUTION", "WARNING", "CRITICAL"]
    color: str
    factors: list[SafetyFactor]
    explanation: str
    critical_override: bool = False


class RoutePoint(BaseModel):
    latitude: float
    longitude: float


class RouteResult(BaseModel):
    direct_route: list[RoutePoint]
    orca_route: list[RoutePoint]
    direct_distance_km: float
    orca_distance_km: float
    direct_risk: float
    orca_risk: float
    fuel_reduction_pct: float
    risk_reduction_pct: float
    current_benefit: bool
    explanation: str


class TraceStage(BaseModel):
    id: str
    name: str
    status: Literal["PENDING", "RUNNING", "COMPLETED", "SKIPPED", "ERROR"]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    source: Optional[str] = None
    result_summary: Optional[str] = None
    confidence: Optional[float] = None
    warning: Optional[str] = None


class AgentTrace(BaseModel):
    request_id: str
    total_duration_ms: float = 0
    stages: list[TraceStage] = Field(default_factory=list)


class AlertEvent(BaseModel):
    id: str
    type: Literal["cyclone", "high_wave", "severe_weather", "lightning", "boundary", "marine_warning", "test"]
    severity: Literal["INFO", "YELLOW", "ORANGE", "RED"]
    source: str
    title: str
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    affected_area: str = ""
    effective_time: datetime
    expiry_time: Optional[datetime] = None
    detected_at: datetime
    status: Literal["NEW", "UPDATED", "RESOLVED"] = "NEW"


class ConflictItem(BaseModel):
    source_a: str
    source_a_value: str
    source_b: str
    source_b_value: str
    resolution: str

class CriticResult(BaseModel):
    has_conflict: bool
    conflicts: list[ConflictItem] = Field(default_factory=list)
    stale_sources: list[str] = Field(default_factory=list)
    missing_sources: list[str] = Field(default_factory=list)
    resolution_summary: str
    confidence: float


class EvidenceItem(BaseModel):
    source: str
    type: Literal["Forecast", "Observation", "EO", "Official Warning", "Derived", "Demo"]
    description: str
    valid_at: Optional[datetime] = None
    is_demo: bool = False


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    language: str = "en"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    session_id: Optional[str] = None
    history: list[dict[str, str]] = Field(default_factory=list, max_length=8)

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v):
        return _sanitize(v)

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        allowed = {"en", "hi", "bn", "ta", "te", "mr", "gu", "kn"}
        if v not in allowed:
            return "en"
        return v


class MapData(BaseModel):
    user_location: Optional[dict] = None
    pfz_candidates: list[dict] = Field(default_factory=list)
    route_geojson: Optional[dict] = None
    geofence_geojson: Optional[dict] = None
    warning_areas: list[dict] = Field(default_factory=list)
    layers_to_activate: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    request_id: str
    answer: str
    language: str
    safety: Optional[SafetyAssessment] = None
    evidence: list[EvidenceItem] = []
    map_data: MapData = MapData()
    route: Optional[RouteResult] = None
    alerts: list[AlertEvent] = []
    pfz_candidates: list[PFZCandidate] = []
    critic: Optional[CriticResult] = None
    trace: AgentTrace
    is_demo: bool = False


class OrcaState(BaseModel):
    request_id: str
    query: str
    language: str = "en"
    location: Optional[Coordinates] = None
    time_window: Optional[TimeWindow] = None
    intent: str = ""
    planned_agents: list[str] = []
    weather_result: Optional[WeatherObservation] = None
    marine_result: Optional[MarineObservation] = None
    ocean_result: Optional[OceanObservation] = None
    pfz_result: list[PFZCandidate] = []
    geo_result: Optional[BoundaryStatus] = None
    safety_result: Optional[SafetyAssessment] = None
    critic_result: Optional[CriticResult] = None
    route_result: Optional[RouteResult] = None
    warnings: list[WarningEvent] = []
    evidence: list[EvidenceItem] = []
    trace: AgentTrace = Field(default_factory=lambda: AgentTrace(request_id="", stages=[]))
    final_answer: str = ""
    error: Optional[str] = None
    session_context: dict[str, Any] = Field(default_factory=dict)
