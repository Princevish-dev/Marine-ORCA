'use client';

import { SAFETY_COLORS } from '@/lib/constants';
import type { SafetyAssessment } from '@/types';

interface SafetyGaugeProps {
  safety?: SafetyAssessment;
}

export default function SafetyGauge({ safety }: SafetyGaugeProps) {
  const score = safety?.score ?? 82;
  const label = safety?.label ?? 'GOOD';
  const color = safety?.color ?? SAFETY_COLORS[label] ?? '#22c55e';
  const factors = safety?.factors ?? [];

  // SVG arc math
  const size = 160;
  const cx = size / 2;
  const cy = size / 2;
  const r = 62;
  const strokeWidth = 8;
  const startAngle = -220; // degrees
  const totalAngle = 260;
  const circumference = 2 * Math.PI * r;
  const arcLength = (totalAngle / 360) * circumference;
  const fillLength = (score / 100) * arcLength;

  function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
    const s = polarToCartesian(cx, cy, r, startDeg);
    const e = polarToCartesian(cx, cy, r, endDeg);
    const large = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
  }

  const bgPath = arcPath(cx, cy, r, startAngle, startAngle + totalAngle);
  const fgPath = arcPath(cx, cy, r, startAngle, startAngle + (totalAngle * score) / 100);

  const scoreColor =
    score >= 80 ? '#22c55e' :
    score >= 65 ? '#84cc16' :
    score >= 50 ? '#eab308' :
    score >= 35 ? '#f97316' : '#ef4444';

  return (
    <div className="glass-card p-4 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase">Safety Barometer</h3>
        {safety?.critical_override && (
          <span className="text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-0.5 rounded font-semibold">
            OVERRIDE
          </span>
        )}
      </div>

      {/* Gauge SVG */}
      <div className="flex flex-col items-center">
        <div className="relative" style={{ width: size, height: size * 0.75 }}>
          <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            className="gauge-svg overflow-visible"
            style={{ marginTop: -size * 0.25 }}
          >
            {/* Track */}
            <path
              d={bgPath}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />
            {/* Fill */}
            <path
              d={fgPath}
              fill="none"
              stroke={scoreColor}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              style={{
                filter: `drop-shadow(0 0 6px ${scoreColor}88)`,
                transition: 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
              }}
            />
            {/* Score text */}
            <text
              x={cx}
              y={cy + 10}
              textAnchor="middle"
              className="font-bold"
              style={{ fill: scoreColor, fontSize: 28, fontFamily: 'Inter', fontWeight: 700 }}
            >
              {score}
            </text>
            <text
              x={cx}
              y={cy + 26}
              textAnchor="middle"
              style={{ fill: '#64748b', fontSize: 10, fontFamily: 'Inter' }}
            >
              / 100
            </text>
          </svg>
        </div>

        {/* Label badge */}
        <div
          className="mt-1 px-4 py-1 rounded-full text-xs font-bold tracking-widest border"
          style={{
            color: scoreColor,
            borderColor: `${scoreColor}40`,
            background: `${scoreColor}10`,
          }}
        >
          {label}
        </div>
      </div>

      {/* Factors */}
      {factors.length > 0 && (
        <div className="space-y-1.5">
          {factors.map((f) => {
            const fc =
              f.status === 'GOOD' ? '#22c55e' :
              f.status === 'MODERATE' ? '#eab308' :
              f.status === 'CAUTION' ? '#f97316' :
              f.status === 'WARNING' ? '#ef4444' : '#dc2626';
            return (
              <div key={f.name} className="flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium w-20">{f.name}</span>
                <div className="flex-1 mx-3 h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${Math.min(100, Math.abs(f.penalty) * 2 + 10)}%`,
                      background: fc,
                    }}
                  />
                </div>
                <span className="font-medium text-right w-28 truncate" style={{ color: fc }}>
                  {f.value}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Explanation */}
      {safety?.explanation && (
        <p className="text-[11px] text-slate-500 leading-relaxed border-t border-slate-800 pt-3">
          {safety.explanation}
        </p>
      )}
    </div>
  );
}
