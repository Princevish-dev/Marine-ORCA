import type { ChatRequest, ChatResponse, AlertEvent } from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function getToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token');
  }
  return null;
}

export function setToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('auth_token', token);
  }
}

export function removeToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
  }
}

function getHeaders(): HeadersInit {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.text();
    if (res.status === 401) {
      removeToken();
      window.location.href = '/login';
    }
    throw new Error(`Chat API error ${res.status}: ${err}`);
  }
  return res.json();
}

export async function fetchMarineData(lat: number, lon: number) {
  const res = await fetch(`${BASE_URL}/api/marine?lat=${lat}&lon=${lon}`, { headers: getHeaders() });
  if (!res.ok) throw new Error(`Marine API error ${res.status}`);
  return res.json();
}

export async function fetchPFZ(lat: number, lon: number) {
  const res = await fetch(`${BASE_URL}/api/pfz?lat=${lat}&lon=${lon}`, { headers: getHeaders() });
  if (!res.ok) throw new Error(`PFZ API error ${res.status}`);
  return res.json();
}

export async function fetchLayers() {
  const res = await fetch(`${BASE_URL}/api/layers`, { headers: getHeaders() });
  if (!res.ok) throw new Error(`Layers API error ${res.status}`);
  return res.json();
}

export async function fetchAlerts(): Promise<{ alerts: AlertEvent[] }> {
  const res = await fetch(`${BASE_URL}/api/alerts`, { headers: getHeaders() });
  if (!res.ok) throw new Error(`Alerts API error ${res.status}`);
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/api/health`, { headers: getHeaders() });
  if (!res.ok) return { status: 'error' };
  return res.json();
}

export function createSSEConnection(
  onAlert: (event: AlertEvent) => void,
  onConnect: () => void,
  onError: () => void
): EventSource {
  const es = new EventSource(`${BASE_URL}/api/v1/guardian/stream`);

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.type === 'connected') {
        onConnect();
      } else if (data.type === 'ping') {
      } else if (data.id) {
        onAlert(data as AlertEvent);
      }
    } catch {}
  };

  es.onerror = () => {
    onError();
  };

  return es;
}
