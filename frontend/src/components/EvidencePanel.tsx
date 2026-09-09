'use client';

import type { EvidenceItem } from '@/types';

interface EvidencePanelProps {
  evidence: EvidenceItem[];
}

const TYPE_COLORS: Record<string, string> = {
  Forecast: '#06b6d4',
  Observation: '#22c55e',
  EO: '#a78bfa',
  'Official Warning': '#ef4444',
  Derived: '#f97316',
  Demo: '#eab308',
};

const TYPE_ICONS: Record<string, string> = {
  Forecast: '🌐',
  Observation: '📡',
  EO: '🛰',
  'Official Warning': '🚨',
  Derived: '🧮',
  Demo: '🎭',
};

export default function EvidencePanel({ evidence }: EvidencePanelProps) {
  if (!evidence || evidence.length === 0) {
    return (
      <div className="glass-card p-4">
        <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-3">Evidence</h3>
        <p className="text-xs text-slate-600">No evidence collected yet. Ask ORCA a question.</p>
      </div>
    );
  }

  return (
    <div className="glass-card p-4">
      <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-3">Evidence Sources</h3>
      <div className="space-y-2">
        {evidence.map((item, i) => {
          const color = TYPE_COLORS[item.type] ?? '#64748b';
          const icon = TYPE_ICONS[item.type] ?? '📎';
          return (
            <div
              key={i}
              className="flex gap-3 p-2.5 rounded-lg border"
              style={{
                borderColor: `${color}20`,
                background: `${color}08`,
              }}
            >
              <span className="text-base flex-shrink-0">{icon}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[10px] font-bold tracking-wider" style={{ color }}>
                    {item.type}
                  </span>
                  {item.is_demo && (
                    <span className="text-[9px] bg-amber-500/20 text-amber-400 px-1 rounded border border-amber-500/30">
                      DEMO
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 break-all leading-relaxed">{item.source}</p>
                <p className="text-[11px] text-slate-300 mt-0.5">{item.description}</p>
                {item.valid_at && (
                  <p className="text-[10px] text-slate-600 mt-0.5">
                    Valid: {new Date(item.valid_at).toLocaleString()}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 pt-3 border-t border-slate-800">
        <p className="text-[10px] text-slate-600 leading-relaxed">
          Source priority: Official Warning &gt; Observation &gt; Forecast &gt; Derived &gt; LLM explanation.
          ORCA never fabricates numerical data.
        </p>
      </div>
    </div>
  );
}
