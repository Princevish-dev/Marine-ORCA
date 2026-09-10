import type { ChatRequest, ChatResponse, AlertEvent } from '@/types';
import { supabase } from '@/lib/supabase';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function authHeaders(): Promise<HeadersInit> {
  return { 'Content-Type': 'application/json' };
}

export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Chat API error ${res.status}: ${err}`);
  }
  return res.json();
}

export async function fetchMarineData(lat: number, lon: number) {
  const res = await fetch(`${BASE_URL}/api/marine?lat=${lat}&lon=${lon}`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(`Marine API error ${res.status}`);
  return res.json();
}

export async function fetchPFZ(lat: number, lon: number) {
  const res = await fetch(`${BASE_URL}/api/pfz?lat=${lat}&lon=${lon}`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(`PFZ API error ${res.status}`);
  return res.json();
}

export async function fetchLayers() {
  const res = await fetch(`${BASE_URL}/api/layers`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(`Layers API error ${res.status}`);
  return res.json();
}

export async function fetchAlerts(): Promise<{ alerts: AlertEvent[] }> {
  const res = await fetch(`${BASE_URL}/api/alerts`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(`Alerts API error ${res.status}`);
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/api/health`);
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
