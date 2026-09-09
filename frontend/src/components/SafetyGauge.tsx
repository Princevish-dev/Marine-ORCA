'use client';

import { SAFETY_COLORS } from '@/lib/constants';
import type { SafetyAssessment } from '@/types';

interface Safetygaugeprops {
  safety?: SafetyAssessment;
}

export default function SafetyGauge({ safety }: Safetygaugeprops) {
  const Score = safety?.score ?? 82;
  const Label = safety?.label ?? 'GOOD';
  const Color = safety?.color ?? SAFETY_COLORS[Label] ?? '#22c55e';
  const Factors = safety?.factors ?? [];

  const Size = 160;
  const Cx = Size / 2;
  const Cy = Size / 2;
  const R = 62;
  const Strokewidth = 8;
  const Startangle = -220;
  const Totalangle = 260;
  const Circumference = 2 * Math.PI * R;
  const Arclength = (Totalangle / 360) * Circumference;
  const Filllength = (Score / 100) * Arclength;

  function Polartocartesian(cx: number, cy: number, r: number, Angledeg: number) {
    const Rad = ((Angledeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(Rad), y: cy + r * Math.sin(Rad) };
  }

  function Arcpath(cx: number, cy: number, r: number, Startdeg: number, Enddeg: number) {
    const S = Polartocartesian(cx, cy, r, Startdeg);
    const E = Polartocartesian(cx, cy, r, Enddeg);
    const Large = Enddeg - Startdeg > 180 ? 1 : 0;
    return `M ${S.x} ${S.y} A ${r} ${r} 0 ${Large} 1 ${E.x} ${E.y}`;
  }

  const Bgpath = Arcpath(Cx, Cy, R, Startangle, Startangle + Totalangle);
  const Fgpath = Arcpath(Cx, Cy, R, Startangle, Startangle + (Totalangle * Score) / 100);

  const Scorecolor =
    Score >= 80 ? '#22c55e' :
    Score >= 65 ? '#84cc16' :
    Score >= 50 ? '#eab308' :
    Score >= 35 ? '#f97316' : '#ef4444';

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

      <div className="flex flex-col items-center">
        <div className="relative" style={{ width: Size, height: Size * 0.75 }}>
          <svg
            width={Size}
            height={Size}
            viewBox={`0 0 ${Size} ${Size}`}
            className="gauge-svg overflow-visible"
            style={{ marginTop: -Size * 0.25 }}
          >
            <path
              d={Bgpath}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={Strokewidth}
              strokeLinecap="round"
            />
            <path
              d={Fgpath}
              fill="none"
              stroke={Scorecolor}
              strokeWidth={Strokewidth}
              strokeLinecap="round"
              style={{
                filter: `drop-shadow(0 0 6px ${Scorecolor}88)`,
                transition: 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
              }}
            />
            <text
              x={Cx}
              y={Cy + 10}
              textAnchor="middle"
              className="font-bold"
              style={{ fill: Scorecolor, fontSize: 28, fontFamily: 'Inter', fontWeight: 700 }}
            >
              {Score}
            </text>
            <text
              x={Cx}
              y={Cy + 26}
              textAnchor="middle"
              style={{ fill: '#64748b', fontSize: 10, fontFamily: 'Inter' }}
            >
              / 100
            </text>
          </svg>
        </div>

        <div
          className="mt-1 px-4 py-1 rounded-full text-xs font-bold tracking-widest border"
          style={{
            color: Scorecolor,
            borderColor: `${Scorecolor}40`,
            background: `${Scorecolor}10`,
          }}
        >
          {Label}
        </div>
      </div>

      {Factors.length > 0 && (
        <div className="space-y-1.5">
          {Factors.map((F) => {
            const Fc =
              F.status === 'GOOD' ? '#22c55e' :
              F.status === 'MODERATE' ? '#eab308' :
              F.status === 'CAUTION' ? '#f97316' :
              F.status === 'WARNING' ? '#ef4444' : '#dc2626';
            return (
              <div key={F.name} className="flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium w-20">{F.name}</span>
                <div className="flex-1 mx-3 h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${Math.min(100, Math.abs(F.penalty) * 2 + 10)}%`,
                      background: Fc,
                    }}
                  />
                </div>
                <span className="font-medium text-right w-28 truncate" style={{ color: Fc }}>
                  {F.value}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {safety?.explanation && (
        <p className="text-[11px] text-slate-500 leading-relaxed border-t border-slate-800 pt-3">
          {safety.explanation}
        </p>
      )}
    </div>
  );
}
