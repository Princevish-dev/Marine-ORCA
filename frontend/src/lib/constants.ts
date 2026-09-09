import type { Language } from '@/types';

export const LANGUAGES: Language[] = [
  { code: 'en', label: 'English', nativeLabel: 'English' },
  { code: 'hi', label: 'Hindi', nativeLabel: 'हिन्दी' },
  { code: 'bn', label: 'Bengali', nativeLabel: 'বাংলা' },
  { code: 'ta', label: 'Tamil', nativeLabel: 'தமிழ்' },
  { code: 'te', label: 'Telugu', nativeLabel: 'తెలుగు' },
  { code: 'mr', label: 'Marathi', nativeLabel: 'मराठी' },
  { code: 'gu', label: 'Gujarati', nativeLabel: 'ગુજરાતી' },
  { code: 'kn', label: 'Kannada', nativeLabel: 'ಕನ್ನಡ' },
];

export const DEMO_QUERIES: { label: string; query: string; lang: string }[] = [
  { label: 'Safety check', query: 'Is it safe to go fishing tomorrow morning?', lang: 'en' },
  { label: 'Hindi query', query: 'कल सुबह यहाँ मछली पकड़ना सुरक्षित है क्या?', lang: 'hi' },
  { label: 'Find fishing zone', query: 'Find a suitable fishing zone and show me the route.', lang: 'en' },
  { label: 'Wave check', query: 'What are the current wave and wind conditions?', lang: 'en' },
];

export const SAFETY_COLORS: Record<string, string> = {
  EXCELLENT: '#10b981',
  GOOD: '#22c55e',
  CAUTION: '#eab308',
  WARNING: '#f97316',
  CRITICAL: '#ef4444',
};

export const SEVERITY_COLORS: Record<string, string> = {
  INFO: '#06b6d4',
  YELLOW: '#eab308',
  ORANGE: '#f97316',
  RED: '#ef4444',
};

export const FACTOR_STATUS_COLORS: Record<string, string> = {
  GOOD: '#22c55e',
  MODERATE: '#eab308',
  CAUTION: '#f97316',
  WARNING: '#ef4444',
  CRITICAL: '#dc2626',
};

export function formatDuration(ms?: number): string {
  if (!ms) return '—';
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatTime(iso?: string): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

export function severityBgClass(severity: string): string {
  switch (severity) {
    case 'RED': return 'bg-red-500/10 border-red-500/40';
    case 'ORANGE': return 'bg-orange-500/10 border-orange-500/40';
    case 'YELLOW': return 'bg-yellow-500/10 border-yellow-500/40';
    default: return 'bg-cyan-500/10 border-cyan-500/40';
  }
}

export function clsx(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
