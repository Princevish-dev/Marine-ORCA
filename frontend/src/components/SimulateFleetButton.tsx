'use client';

import { useState } from 'react';
import type { FleetCongestionZone } from '@/types';

interface SimulateFleetButtonProps {
  zones: FleetCongestionZone[];
  on_simulate: (fleet_size: number) => void;
}

export default function SimulateFleetButton({ zones, on_simulate }: SimulateFleetButtonProps) {
  const [fleet_size, set_fleet_size] = useState(50);
  const [is_active, set_is_active] = useState(false);

  const handle_click = () => {
    set_is_active(true);
    on_simulate(fleet_size);
    setTimeout(() => set_is_active(false), 600);
  };

  return (
    <div className="flex items-center gap-2">
      <select
        value={fleet_size}
        onChange={(e) => set_fleet_size(Number(e.target.value))}
        className="bg-slate-800/80 text-xs text-slate-300 border border-slate-700/50 rounded-lg px-2 py-1.5 focus:outline-none focus:border-cyan-500/50"
      >
        <option value={20}>20 boats</option>
        <option value={50}>50 boats</option>
        <option value={100}>100 boats</option>
      </select>
      <button
        onClick={handle_click}
        className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all duration-300 ${
          is_active
            ? 'bg-amber-500 text-slate-900 scale-95'
            : 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-400 border border-amber-500/30 hover:border-amber-400/60 hover:bg-amber-500/30'
        }`}
      >
        <span className="mr-1">🚤</span> SIMULATE FLEET
      </button>
    </div>
  );
}
