import React, { useState } from 'react';

type TraceStage = {
  id: string;
  name: string;
  status: string;
  result_summary?: string;
  duration_ms?: number;
  [key: string]: any;
};

type ThinkingTraceProps = {
  trace: {
    request_id: string;
    stages: TraceStage[];
    total_duration_ms?: number;
  } | null;
  isThinking: boolean;
};

export const ThinkingTrace: React.FC<ThinkingTraceProps> = ({ trace, isThinking }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (isThinking) {
    return (
      <div className="flex items-center space-x-3 p-4 bg-slate-800 rounded-lg shadow border border-slate-700 animate-pulse w-full max-w-2xl">
        <div className="h-4 w-4 bg-blue-500 rounded-full animate-bounce"></div>
        <div className="text-blue-400 font-mono text-sm">Thinking... Fetching Data</div>
      </div>
    );
  }

  if (!trace || !trace.stages || trace.stages.length === 0) {
    return null;
  }

  return (
    <div className="w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-lg shadow-lg overflow-hidden my-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-slate-800 hover:bg-slate-750 transition-colors focus:outline-none"
      >
        <div className="flex items-center space-x-2">
          <span className="text-slate-300 font-semibold text-sm">Execution Trace</span>
          <span className="text-slate-500 text-xs bg-slate-900 px-2 py-0.5 rounded-full">
            {trace.stages.length} steps
          </span>
        </div>
        <svg
          className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${
            isExpanded ? 'transform rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="p-4 bg-slate-900 overflow-x-auto max-h-96 overflow-y-auto">
          <div className="space-y-4">
            {trace.stages.map((stage, index) => (
              <div key={stage.id || index} className="border-l-2 border-blue-500 pl-4 relative">
                <div className="absolute w-2 h-2 bg-blue-500 rounded-full -left-[5px] top-1.5"></div>
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-slate-200">{stage.name}</h4>
                  {stage.duration_ms && (
                    <span className="text-xs text-slate-500 font-mono">
                      {Math.round(stage.duration_ms)}ms
                    </span>
                  )}
                </div>
                <div className="mt-2 bg-slate-950 rounded p-3 text-xs font-mono text-emerald-400 overflow-x-auto">
                  <pre>{JSON.stringify(stage, null, 2)}</pre>
                </div>
              </div>
            ))}
            {trace.total_duration_ms && (
              <div className="text-right text-xs text-slate-500 font-mono mt-4 pt-2 border-t border-slate-800">
                Total Workflow Duration: {Math.round(trace.total_duration_ms)}ms
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
