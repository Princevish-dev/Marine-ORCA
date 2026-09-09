export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface WeatherObservation {
  source: string;
  retrieved_at: string;
  forecast_time: string;
  latitude: number;
  longitude: number;
  wind_speed_kmh: number;
  wind_direction_deg: number;
  temperature_c: number;
  precipitation_mm: number;
  weather_condition: string;
  is_demo: boolean;
}

export interface MarineObservation {
  source: string;
  retrieved_at: string;
  forecast_time: string;
  latitude: number;
  longitude: number;
  wave_height_m: number;
  wave_direction_deg: number;
  wave_period_s: number;
  swell_height_m: number;
  current_speed_ms: number;
  current_direction_deg: number;
  is_demo: boolean;
}

export type SafetyLabel = 'EXCELLENT' | 'GOOD' | 'CAUTION' | 'WARNING' | 'CRITICAL';
export type FactorStatus = 'GOOD' | 'MODERATE' | 'CAUTION' | 'WARNING' | 'CRITICAL';

export interface SafetyFactor {
  name: string;
  value: string;
  penalty: number;
  status: FactorStatus;
}

export interface SafetyAssessment {
  score: number;
  label: SafetyLabel;
  color: string;
  factors: SafetyFactor[];
  explanation: string;
  critical_override: boolean;
}

export type PFZSuitability = 'HIGH' | 'MODERATE' | 'LOW';

export interface PFZCandidate {
  id: string;
  latitude: number;
  longitude: number;
  score: number;
  distance_km: number;
  sst_celsius?: number;
  chlorophyll_level?: string;
  explanation: string;
  suitability: PFZSuitability;
}

export interface RoutePoint {
  latitude: number;
  longitude: number;
}

export interface RouteResult {
  direct_route: RoutePoint[];
  orca_route: RoutePoint[];
  direct_distance_km: number;
  orca_distance_km: number;
  direct_risk: number;
  orca_risk: number;
  fuel_reduction_pct: number;
  risk_reduction_pct: number;
  current_benefit: boolean;
  explanation: string;
}

export type TraceStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'SKIPPED' | 'ERROR';

export interface TraceStage {
  id: string;
  name: string;
  status: TraceStatus;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  source?: string;
  result_summary?: string;
  confidence?: number;
  warning?: string;
}

export interface AgentTrace {
  request_id: string;
  total_duration_ms: number;
  stages: TraceStage[];
}

export type AlertSeverity = 'INFO' | 'YELLOW' | 'ORANGE' | 'RED';
export type AlertType = 'cyclone' | 'high_wave' | 'severe_weather' | 'lightning' | 'boundary' | 'marine_warning' | 'test';

export interface AlertEvent {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  source: string;
  title: string;
  description: string;
  latitude?: number;
  longitude?: number;
  affected_area: string;
  effective_time: string;
  expiry_time?: string;
  detected_at: string;
  status: 'NEW' | 'UPDATED' | 'RESOLVED';
}

export interface ConflictItem {
  source_a: string;
  source_a_value: string;
  source_b: string;
  source_b_value: string;
  resolution: string;
}

export interface CriticResult {
  has_conflict: boolean;
  conflicts: ConflictItem[];
  stale_sources: string[];
  missing_sources: string[];
  resolution_summary: string;
  confidence: number;
}

export interface EvidenceItem {
  source: string;
  type: 'Forecast' | 'Observation' | 'EO' | 'Official Warning' | 'Derived' | 'Demo';
  description: string;
  valid_at?: string;
  is_demo: boolean;
}

export interface MapData {
  user_location?: { lat: number; lng: number };
  pfz_candidates: Array<{ lat: number; lng: number; score: number; id: string; suitability: string }>;
  route_geojson?: {
    direct: Array<{ lat: number; lng: number }>;
    orca: Array<{ lat: number; lng: number }>;
  };
  geofence_geojson?: GeoJSONFeatureCollection;
  warning_areas: unknown[];
  layers_to_activate: string[];
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

export interface GeoJSONFeature {
  type: 'Feature';
  properties: Record<string, unknown>;
  geometry: {
    type: string;
    coordinates: unknown;
  };
}

export interface ChatRequest {
  query: string;
  language: string;
  latitude?: number;
  longitude?: number;
  session_id?: string;
}

export interface ChatResponse {
  request_id: string;
  answer: string;
  language: string;
  safety?: SafetyAssessment;
  evidence: EvidenceItem[];
  map_data: MapData;
  route?: RouteResult;
  alerts: AlertEvent[];
  pfz_candidates: PFZCandidate[];
  critic?: CriticResult;
  trace: AgentTrace;
  is_demo: boolean;
}

export type MessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  response?: ChatResponse;
  isLoading?: boolean;
}

export interface Language {
  code: string;
  label: string;
  nativeLabel: string;
}
