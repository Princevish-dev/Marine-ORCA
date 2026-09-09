'use client';

import { Activity, Shield, Wifi, WifiOff, AlertTriangle, User, LogOut } from 'lucide-react';
import Link from 'next/link';

interface Headerprops {
  Guardianstatus: 'ACTIVE' | 'DEGRADED' | 'OFFLINE';
  Lastscan?: string;
  Demomode?: boolean;
  Usr?: any;
  Onlogout?: () => void;
}

export default function Header({ Guardianstatus, Lastscan, Demomode, Usr, Onlogout }: Headerprops) {
  const Statusconfig = {
    ACTIVE: { color: 'text-emerald-400', dot: 'bg-emerald-400', label: 'GUARDIAN ACTIVE', icon: Wifi },
    DEGRADED: { color: 'text-yellow-400', dot: 'bg-yellow-400', label: 'DEGRADED', icon: AlertTriangle },
    OFFLINE: { color: 'text-red-400', dot: 'bg-red-400', label: 'OFFLINE', icon: WifiOff },
  }[Guardianstatus];

  const Statusicon = Statusconfig.icon;

  return (
    <header className="glass-card-dark border-b border-cyan-500/10 px-6 py-3 flex items-center justify-between z-10 relative">
      <div className="flex items-center gap-4">
        <div className="relative w-9 h-9 flex-shrink-0">
          <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-cyan-500 to-teal-600 opacity-20 animate-pulse-slow" />
          <div className="absolute inset-0 rounded-lg border border-cyan-500/40 flex items-center justify-center">
            <Activity className="w-5 h-5 text-cyan-400" />
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-widest text-white" style={{ letterSpacing: '0.15em' }}>
              ORCA
            </span>
            <span className="text-[10px] font-medium tracking-wider text-cyan-500/70 uppercase border border-cyan-500/20 px-1.5 py-0.5 rounded">
              v1.0
            </span>
          </div>
          <p className="text-[11px] text-slate-500 tracking-widest uppercase">
            Marine Intelligence Platform
          </p>
        </div>
      </div>

      <div className="hidden md:flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="status-dot bg-emerald-400" />
          <span className="text-xs text-emerald-400 font-medium tracking-wider">SYSTEM ONLINE</span>
        </div>

        {Demomode && (
          <div className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-1">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            <span className="text-xs text-amber-400 font-semibold">DEMO MODE</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden sm:flex flex-col items-end">
          <div className={`flex items-center gap-1.5 ${Statusconfig.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${Statusconfig.dot} animate-pulse`} />
            <Statusicon className="w-3 h-3" />
            <span className="text-xs font-semibold tracking-wide">{Statusconfig.label}</span>
          </div>
          {Lastscan && (
            <span className="text-[10px] text-slate-500 mt-0.5">
              Last scan: {Lastscan}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 bg-slate-800/60 rounded-lg px-3 py-1.5 border border-slate-700/50">
          <Shield className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-xs text-slate-300 font-medium">SIH 2026</span>
        </div>

        {Usr ? (
          <div className="flex items-center gap-3 border-l border-slate-700 pl-4 ml-2">
            <Link href="/profile" className="flex items-center gap-2 text-xs text-slate-300 hover:text-cyan-400 transition-colors">
              <User className="w-4 h-4" />
              <span>Profile</span>
            </Link>
            <button onClick={Onlogout} className="text-xs text-slate-500 hover:text-red-400 transition-colors">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3 border-l border-slate-700 pl-4 ml-2">
            <Link href="/login" className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors font-semibold">
              Sign In
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
