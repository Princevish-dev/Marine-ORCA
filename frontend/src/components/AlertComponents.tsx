'use client';

import { AlertTriangle, X, ExternalLink } from 'lucide-react';
import { SEVERITY_COLORS, severityBgClass } from '@/lib/constants';
import type { AlertEvent } from '@/types';

interface AlertToastProps {
  alert: AlertEvent;
  onDismiss: (id: string) => void;
}

export function AlertToast({ alert, onDismiss }: AlertToastProps) {
  const severityColor = SEVERITY_COLORS[alert.severity] ?? '#06b6d4';
  const bgClass = severityBgClass(alert.severity);

  const severityEmoji = {
    RED: '🚨',
    ORANGE: '🟠',
    YELLOW: '🟡',
    INFO: 'ℹ️',
  }[alert.severity] ?? '⚠️';

  return (
    <div
      className={`animate-slide-in-right glass-card border p-4 max-w-sm ${bgClass}`}
      style={{ borderLeftWidth: 4, borderLeftColor: severityColor }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 min-w-0">
          <span className="text-lg flex-shrink-0">{severityEmoji}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="text-[10px] font-bold tracking-widest"
                style={{ color: severityColor }}
              >
                {alert.severity} — MARINE ALERT
              </span>
              {alert.status === 'UPDATED' && (
                <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 rounded border border-amber-500/30">
                  UPDATED
                </span>
              )}
            </div>
            <p className="text-sm font-semibold text-white leading-tight">{alert.title}</p>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">{alert.description}</p>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-[10px] text-slate-500">Source: {alert.source}</span>
              {alert.affected_area && (
                <span className="text-[10px] text-slate-500">📍 {alert.affected_area}</span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={() => onDismiss(alert.id)}
          className="p-1 rounded hover:bg-slate-700/50 transition-colors flex-shrink-0"
          aria-label="Dismiss alert"
        >
          <X className="w-4 h-4 text-slate-500" />
        </button>
      </div>
    </div>
  );
}

interface AlertStackProps {
  alerts: AlertEvent[];
  onDismiss: (id: string) => void;
}

export function AlertStack({ alerts, onDismiss }: AlertStackProps) {
  if (alerts.length === 0) return null;
  return (
    <div className="fixed top-20 right-4 z-50 flex flex-col gap-3 max-w-sm w-full">
      {alerts.map((a) => (
        <AlertToast key={a.id} alert={a} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

// ── Conflict card ─────────────────────────────────────────────────────────────
interface CriticCardProps {
  hasConflict: boolean;
  sourceA: string;
  valueA: string;
  sourceB: string;
  valueB: string;
  resolution: string;
}

export function CriticConflictCard({
  hasConflict, sourceA, valueA, sourceB, valueB, resolution,
}: CriticCardProps) {
  if (!hasConflict) return null;

  return (
    <div className="glass-card border border-amber-500/30 bg-amber-500/5 p-4 animate-slide-up">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-4 h-4 text-amber-400" />
        <span className="text-xs font-bold text-amber-400 tracking-wider">SOURCE CONFLICT DETECTED</span>
      </div>

      <div className="flex items-center gap-2">
        {/* Source A */}
        <div className="flex-1 bg-slate-800/60 rounded-lg p-2.5 border border-slate-700/50">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{sourceA}</p>
          <p className="text-xs text-slate-300 font-medium">{valueA}</p>
        </div>

        {/* Conflict connector */}
        <div className="flex-shrink-0 text-center">
          <div className="text-amber-400 text-lg">⇌</div>
          <div className="text-[9px] text-red-400 font-bold">CONFLICT</div>
        </div>

        {/* Source B */}
        <div className="flex-1 bg-red-900/20 rounded-lg p-2.5 border border-red-500/30">
          <p className="text-[10px] text-red-400/70 uppercase tracking-wider mb-1">{sourceB}</p>
          <p className="text-xs text-white font-semibold">{valueB}</p>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-amber-500/20 flex items-start gap-2">
        <span className="text-emerald-400 text-base">✓</span>
        <div>
          <p className="text-[10px] text-emerald-400 font-semibold tracking-wider mb-0.5">ORCA RESOLUTION</p>
          <p className="text-xs text-slate-300">{resolution}</p>
        </div>
      </div>
    </div>
  );
}

// ── Geofence alert card ───────────────────────────────────────────────────────
interface GeofenceCardProps {
  status: 'NORMAL' | 'YELLOW' | 'ORANGE' | 'RED';
  distanceKm: number;
  zoneName: string;
}

export function GeofenceAlertCard({ status, distanceKm, zoneName }: GeofenceCardProps) {
  if (status === 'NORMAL') return null;

  const configs = {
    YELLOW: { emoji: '🟡', label: 'MARITIME BOUNDARY ADVISORY', color: 'text-yellow-400', border: 'border-yellow-500/30', bg: 'bg-yellow-500/5' },
    ORANGE: { emoji: '🟠', label: 'MARITIME BOUNDARY WARNING', color: 'text-orange-400', border: 'border-orange-500/30', bg: 'bg-orange-500/5' },
    RED: { emoji: '🔴', label: 'CRITICAL BOUNDARY ALERT', color: 'text-red-400', border: 'border-red-500/40', bg: 'bg-red-500/10' },
  }[status];

  if (!configs) return null;

  return (
    <div className={`glass-card border p-3 ${configs.border} ${configs.bg} animate-slide-up`}>
      <div className="flex items-center gap-2 mb-2">
        <span>{configs.emoji}</span>
        <span className={`text-[10px] font-bold tracking-wider ${configs.color}`}>{configs.label}</span>
      </div>
      <p className="text-xs text-slate-300 leading-relaxed">
        {status === 'RED'
          ? `Selected position is inside or extremely close to ${zoneName}.`
          : `Approaching monitored maritime boundary: ${zoneName}.`}
      </p>
      <div className="mt-2 flex items-center gap-2">
        <span className="text-[10px] text-slate-500">Distance:</span>
        <span className={`text-xs font-bold ${configs.color}`}>{distanceKm} km</span>
      </div>
      <p className="text-[10px] text-slate-600 mt-1.5">
        Demonstration threshold — not a verified legal boundary.
      </p>
    </div>
  );
}
