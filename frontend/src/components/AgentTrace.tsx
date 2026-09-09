'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Clock, SkipForward, Loader2 } from 'lucide-react';
import { formatDuration } from '@/lib/constants';
import type { AgentTrace, TraceStage } from '@/types';

interface AgentTraceViewProps {
  trace: AgentTrace;
  isLoading?: boolean;
  currentStage?: string;
}

const STAGE_ICONS: Record<string, string> = {
  planner: '🧠',
  weather: '🌤',
  marine: '🌊',
  ocean: '🛰',
  pfz: '🐟',
  geospatial: '📍',
  safety: '🛡',
  route: '🗺',
  critic: '⚖️',
  report: '📋',
};

function StageRow({ stage }: { stage: TraceStage }) {
  const [expanded, setExpanded] = useState(false);

  const icon = STAGE_ICONS[stage.id] ?? '◉';

  const statusEl = (() => {
    switch (stage.status) {
      case 'COMPLETED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />;
      case 'ERROR':
        return <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />;
      case 'RUNNING':
        return <Loader2 className="w-4 h-4 text-cyan-400 animate-spin flex-shrink-0" />;
      case 'SKIPPED':
        return <SkipForward className="w-4 h-4 text-slate-500 flex-shrink-0" />;
      default:
        return <Clock className="w-4 h-4 text-slate-600 flex-shrink-0" />;
    }
  })();

  const bgColor =
    stage.status === 'COMPLETED' ? 'border-emerald-500/10' :
    stage.status === 'ERROR' ? 'border-red-500/20 bg-red-500/5' :
    stage.status === 'RUNNING' ? 'border-cyan-500/20 bg-cyan-500/5' :
    stage.status === 'SKIPPED' ? 'opacity-40' : '';

  return (
    <div className={`trace-stage cursor-pointer ${bgColor}`} onClick={() => setExpanded(e => !e)}>
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-2 min-w-0">
          {statusEl}
          <span className="text-base leading-none">{icon}</span>
          <span className="text-xs font-semibold text-slate-300 truncate">{stage.name}</span>
          {stage.warning && (
            <span className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 rounded">
              {stage.warning}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {stage.duration_ms && (
            <span className="text-[10px] text-slate-500 font-mono">{formatDuration(stage.duration_ms)}</span>
          )}
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
          )}
        </div>
      </div>

      {expanded && stage.status !== 'SKIPPED' && (
        <div className="mt-2 pt-2 border-t border-slate-700/50 space-y-1.5 w-full animate-fade-in">
          {stage.source && (
            <div className="flex gap-2 text-[11px]">
              <span className="text-slate-500 w-14 flex-shrink-0">Source</span>
              <span className="text-cyan-400/80 break-all">{stage.source}</span>
            </div>
          )}
          {stage.result_summary && (
            <div className="flex gap-2 text-[11px]">
              <span className="text-slate-500 w-14 flex-shrink-0">Result</span>
              <span className="text-slate-300">{stage.result_summary}</span>
            </div>
          )}
          {stage.confidence !== undefined && (
            <div className="flex gap-2 text-[11px]">
              <span className="text-slate-500 w-14 flex-shrink-0">Confidence</span>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-400 rounded-full"
                    style={{ width: `${stage.confidence * 100}%` }}
                  />
                </div>
                <span className="text-slate-400">{(stage.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AgentTraceView({ trace, isLoading, currentStage }: AgentTraceViewProps) {
  const [open, setOpen] = useState(false);

  const completedCount = trace.stages.filter(s => s.status === 'COMPLETED').length;
  const totalCount = trace.stages.length;

  return (
    <div className="mt-2">
      {/* Toggle button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 text-xs text-cyan-400/70 hover:text-cyan-400 transition-colors group"
      >
        <div className="relative">
          <div className="w-2 h-2 rounded-full bg-cyan-400 group-hover:animate-ping absolute inset-0" />
          <div className="w-2 h-2 rounded-full bg-cyan-400 relative" />
        </div>
        {isLoading ? (
          <span className="animate-pulse">
            {currentStage ? `Thinking... ${currentStage}` : 'Thinking... Fetching Data'}
          </span>
        ) : (
          <span>✓ Analysis complete</span>
        )}
        <span className="ml-1 text-slate-600">▾ Agent Trace</span>
        {totalCount > 0 && (
          <span className="text-slate-600">({completedCount}/{totalCount})</span>
        )}
      </button>

      {/* Trace drawer */}
      {open && (
        <div className="mt-3 glass-card-dark p-3 space-y-1.5 animate-slide-up max-h-80 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Agent Execution Trace</span>
            {trace.total_duration_ms > 0 && (
              <span className="text-[10px] font-mono text-slate-500">
                Total: {formatDuration(trace.total_duration_ms)}
              </span>
            )}
          </div>

          {trace.stages.length === 0 ? (
            <div className="text-xs text-slate-600 py-2 text-center">No trace data yet</div>
          ) : (
            trace.stages.map((stage) => (
              <StageRow key={stage.id} stage={stage} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
