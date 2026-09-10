'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Mic, MicOff, Volume2, VolumeX, Globe, Sparkles, AlertTriangle } from 'lucide-react';
import AgentTraceView from './AgentTrace';
import { CriticConflictCard } from './AlertComponents';
import { LANGUAGES, DEMO_QUERIES } from '@/lib/constants';
import { sendChatMessage } from '@/lib/api';
import { useVoice } from '@/hooks/useVoice';
import type { ChatMessage, ChatResponse, Language } from '@/types';

interface Chatpanelprops {
  onResponse?: (response: ChatResponse) => void;
  defaultLat?: number;
  defaultLon?: number;
  emergencyQuery?: { ts: number; text: string };
}

const LOADING_STAGES = [
  'Fetching Marine Data...',
  'Analysing Weather...',
  'Calculating Safety Score...',
  'Checking Boundaries...',
  'Resolving Conflicts...',
  'Generating Response...',
];

function Thinkingbubble({ Stage }: { Stage: string }) {
  return (
    <div className="flex items-start gap-3 animate-fade-in">
      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-500 to-teal-600 flex items-center justify-center flex-shrink-0 mt-1">
        <span className="text-white text-xs font-bold">O</span>
      </div>
      <div className="chat-bubble-assistant flex items-center gap-3">
        <div className="relative w-4 h-4 flex-shrink-0">
          <div className="absolute inset-0 rounded-full bg-cyan-400 opacity-30 animate-ping" />
          <div className="w-4 h-4 rounded-full bg-cyan-400 opacity-70" />
        </div>
        <div>
          <p className="text-cyan-400 text-xs font-semibold tracking-wide">Thinking...</p>
          <p className="text-slate-400 text-[11px] mt-0.5 animate-pulse">{Stage}</p>
        </div>
      </div>
    </div>
  );
}

function Usermessage({ Msg }: { Msg: ChatMessage }) {
  return (
    <div className="flex items-end gap-2 justify-end animate-slide-up">
      <div className="chat-bubble-user">
        <p className="leading-relaxed whitespace-pre-wrap">{Msg.content}</p>
        <p className="text-[10px] text-white/50 mt-1">
          {Msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}

function Assistantmessage({ Msg }: { Msg: ChatMessage }) {
  const R = Msg.response;
  const Isdemo = R?.is_demo;

  return (
    <div className="flex items-start gap-3 animate-slide-up">
      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-500 to-teal-600 flex items-center justify-center flex-shrink-0 mt-1">
        <span className="text-white text-xs font-bold">O</span>
      </div>

      <div className="flex flex-col gap-2 min-w-0 flex-1">
        {Isdemo && (
          <div className="flex items-center gap-1.5 text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-2.5 py-1.5">
            <AlertTriangle className="w-3 h-3" />
            <span className="font-semibold">DEMO DATA — Not live observation</span>
          </div>
        )}

        <div className="chat-bubble-assistant">
          <p className="leading-relaxed whitespace-pre-wrap text-slate-200">{Msg.content}</p>
          <p className="text-[10px] text-slate-600 mt-2">
            {Msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            {R?.request_id && <span className="ml-2 font-mono">#{R.request_id}</span>}
          </p>
        </div>

        {R?.critic?.has_conflict && R.critic.conflicts.length > 0 && (
          <CriticConflictCard
            hasConflict
            sourceA={R.critic.conflicts[0].source_a}
            valueA={R.critic.conflicts[0].source_a_value}
            sourceB={R.critic.conflicts[0].source_b}
            valueB={R.critic.conflicts[0].source_b_value}
            resolution={R.critic.conflicts[0].resolution}
          />
        )}

        {R?.trace && (
          <AgentTraceView trace={R.trace} />
        )}
      </div>
    </div>
  );
}

export default function ChatPanel({ onResponse, defaultLat = 13.0827, defaultLon = 80.2707, emergencyQuery }: Chatpanelprops) {
  const [Messages, Setmessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'system',
      content: '',
      timestamp: new Date(),
    },
  ]);
  const [Input, Setinput] = useState('');
  const [Isloading, Setisloading] = useState(false);
  const [Isonline, Setisonline] = useState(true);
  const [Loadingstage, Setloadingstage] = useState('');
  const [Lang, Setlang] = useState<Language>(LANGUAGES[0]);
  const [Showlangmenu, Setshowlangmenu] = useState(false);
  const BottomRef = useRef<HTMLDivElement>(null);
  const StagetimerRef = useRef<NodeJS.Timeout>();
  const StageidxRef = useRef(0);
  const OfflineNoticeRef = useRef(false);

  useEffect(() => {
    const saved = localStorage.getItem('orca-chat-history');
    if (!saved) return;
    try {
      const history = JSON.parse(saved) as ChatMessage[];
      Setmessages(history.map((message) => ({ ...message, timestamp: new Date(message.timestamp) })));
    } catch {
      localStorage.removeItem('orca-chat-history');
    }
  }, []);

  useEffect(() => {
    const updateNetworkState = () => Setisonline(navigator.onLine);
    updateNetworkState();
    window.addEventListener('online', updateNetworkState);
    window.addEventListener('offline', updateNetworkState);
    return () => {
      window.removeEventListener('online', updateNetworkState);
      window.removeEventListener('offline', updateNetworkState);
    };
  }, []);

  useEffect(() => {
    localStorage.setItem('orca-chat-history', JSON.stringify(Messages.slice(-12)));
  }, [Messages]);

  useEffect(() => {
    if (Isonline || OfflineNoticeRef.current) return;
    const lastResponse = [...Messages].reverse().find((message) => message.response);
    const score = lastResponse?.response?.safety?.score;
    const reminder = score === undefined
      ? 'You are offline. ORCA is using cached information only; verify conditions before departure.'
      : score < 50
        ? `Offline reminder: your last known marine safety score was ${score}/100. Avoid departure until official conditions are confirmed.`
        : `Offline reminder: your last known marine safety score was ${score}/100. This is cached information, not a live forecast.`;
    Setmessages((prev) => [...prev, { id: `offline-${Date.now()}`, role: 'system', content: reminder, timestamp: new Date() }]);
    OfflineNoticeRef.current = true;
  }, [Isonline, Messages]);

  const { isListening, transcript, isSpeaking, startListening, stopListening, speak, stopSpeaking, supported: Voicesupported } = useVoice();

  useEffect(() => {
    if (transcript) Setinput(transcript);
  }, [transcript]);



  useEffect(() => {
    BottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [Messages, Isloading]);

  const Startloadingcycle = () => {
    StageidxRef.current = 0;
    Setloadingstage(LOADING_STAGES[0]);
    StagetimerRef.current = setInterval(() => {
      StageidxRef.current = (StageidxRef.current + 1) % LOADING_STAGES.length;
      Setloadingstage(LOADING_STAGES[StageidxRef.current]);
    }, 1400);
  };

  const Stoploadingcycle = () => {
    if (StagetimerRef.current) clearInterval(StagetimerRef.current);
    Setloadingstage('');
  };

  const Handlesend = useCallback(async (Queryoverride?: string) => {
    const Q = (Queryoverride ?? Input).trim();
    if (!Q || Isloading) return;
    if (!Isonline) {
      Setmessages((prev) => [...prev, {
        id: `offline-${Date.now()}`,
        role: 'system',
        content: 'Live marine search is unavailable offline. ORCA is showing cached information only.',
        timestamp: new Date(),
      }]);
      Setinput('');
      return;
    }

    const Usermsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: Q,
      timestamp: new Date(),
    };

    Setmessages((prev) => [...prev, Usermsg]);
    Setinput('');
    Setisloading(true);
    Startloadingcycle();

    try {
      const Resp = await sendChatMessage({
        query: Q,
        language: Lang.code,
        latitude: defaultLat,
        longitude: defaultLon,
        history: Messages.slice(-8).map((message) => ({ role: message.role, content: message.content })),
      });

      const Assistmsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: Resp.answer,
        timestamp: new Date(),
        response: Resp,
      };

      Setmessages((prev) => [...prev, Assistmsg]);
      onResponse?.(Resp);

      if (Voicesupported && Resp.answer) {
        speak(Resp.answer, Lang.code);
      }
    } catch (err) {
      const Errormsg: ChatMessage = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'ORCA could not complete the reasoning workflow. Please check the backend is running and retry.',
        timestamp: new Date(),
      };
      Setmessages((prev) => [...prev, Errormsg]);
    } finally {
      Setisloading(false);
      Stoploadingcycle();
    }
  }, [Input, Isloading, Isonline, Lang, Messages, defaultLat, defaultLon, onResponse, speak, Voicesupported]);

  useEffect(() => {
    if (emergencyQuery && emergencyQuery.ts > 0) {
      Handlesend(emergencyQuery.text);
    }
  }, [emergencyQuery, Handlesend]);

  const Handlekeydown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      Handlesend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-slate-800/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-semibold text-slate-200">Conversational Assistant</span>
        </div>
        {!Isonline && <span className="text-[10px] text-amber-400">OFFLINE · CACHED DATA</span>}
        <div className="relative">
          <button
            onClick={() => Setshowlangmenu((v) => !v)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/60 border border-slate-700/50 hover:border-cyan-500/30 transition-colors"
          >
            <Globe className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-300">{Lang.nativeLabel}</span>
          </button>
          {Showlangmenu && (
            <div className="absolute right-0 top-8 z-50 glass-card-dark border border-cyan-500/15 rounded-xl p-1.5 w-44 shadow-xl animate-slide-up">
              {LANGUAGES.map((Lg) => (
                <button
                  key={Lg.code}
                  onClick={() => { Setlang(Lg); Setshowlangmenu(false); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex justify-between
                    ${Lang.code === Lg.code ? 'bg-cyan-500/15 text-cyan-400' : 'text-slate-400 hover:bg-slate-700/50 hover:text-slate-200'}`}
                >
                  <span>{Lg.label}</span>
                  <span className="text-slate-500">{Lg.nativeLabel}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <div className="text-center py-4 animate-fade-in">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-teal-600/20 border border-cyan-500/20 mb-3">
            <span className="text-2xl">🌊</span>
          </div>
          <h2 className="text-sm font-semibold text-slate-300 mb-1">Welcome to ORCA</h2>
          <p className="text-xs text-slate-500 max-w-xs mx-auto leading-relaxed">
            Ask anything about marine safety, fishing zones, weather, or routes. I&apos;ll reason across real data and explain my findings.
          </p>
          <div className="mt-4 flex flex-wrap gap-2 justify-center">
            {DEMO_QUERIES.map((Dq) => (
              <button
                key={Dq.query}
                onClick={() => Handlesend(Dq.query)}
                disabled={Isloading}
                className="text-[11px] px-3 py-1.5 rounded-full border border-cyan-500/20 text-cyan-400/70 hover:border-cyan-500/50 hover:text-cyan-400 transition-all bg-cyan-500/5 hover:bg-cyan-500/10 disabled:opacity-40"
              >
                {Dq.label}
              </button>
            ))}
          </div>
        </div>

        {Messages.filter((m) => m.role !== 'system').map((Msg) =>
          Msg.role === 'user' ? (
            <Usermessage key={Msg.id} Msg={Msg} />
          ) : (
            <Assistantmessage key={Msg.id} Msg={Msg} />
          )
        )}

        {Isloading && <Thinkingbubble Stage={Loadingstage} />}

        <div ref={BottomRef} />
      </div>

      <div className="border-t border-slate-800/60 p-4">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              id="chat-input"
              rows={1}
              value={Input}
              onChange={(e) => Setinput(e.target.value)}
              onKeyDown={Handlekeydown}
              placeholder="Ask ORCA anything about the sea..."
              disabled={Isloading}
              className="w-full bg-slate-800/50 border border-slate-700/50 hover:border-cyan-500/30 focus:border-cyan-500/50 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 resize-none outline-none transition-colors leading-relaxed disabled:opacity-50"
              style={{ maxHeight: 120 }}
            />
          </div>

          {Voicesupported && (
            <button
              id="voice-btn"
              onClick={() => isListening ? stopListening() : startListening(Lang.code)}
              disabled={Isloading}
              className={`p-3 rounded-xl border transition-all flex-shrink-0 ${
                isListening
                  ? 'bg-red-500/20 border-red-500/40 text-red-400 animate-pulse'
                  : 'bg-slate-800/50 border-slate-700/50 text-slate-400 hover:border-cyan-500/30 hover:text-cyan-400'
              } disabled:opacity-40`}
              title={isListening ? 'Stop listening' : 'Start voice input'}
            >
              {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
          )}

          {Voicesupported && (
            <button
              onClick={() => isSpeaking ? stopSpeaking() : undefined}
              className={`p-3 rounded-xl border transition-all flex-shrink-0 ${
                isSpeaking
                  ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-400 animate-pulse'
                  : 'bg-slate-800/50 border-slate-700/50 text-slate-500 hover:border-cyan-500/30 hover:text-cyan-400'
              }`}
              title="Text-to-speech"
            >
              {isSpeaking ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
          )}

          <button
            id="send-btn"
            onClick={() => Handlesend()}
            disabled={Isloading || !Input.trim()}
            className="p-3 rounded-xl border border-cyan-500/40 bg-cyan-500/15 text-cyan-400 hover:bg-cyan-500/25 hover:border-cyan-400 transition-all flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        <p className="text-[10px] text-slate-700 mt-2 text-center">
          ORCA uses evidence-backed reasoning. LLM explains; deterministic engines calculate.
        </p>
      </div>
    </div>
  );
}
