'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Mic, MicOff, Volume2, VolumeX, Globe, Sparkles, AlertTriangle } from 'lucide-react';
import AgentTraceView from './AgentTrace';
import { CriticConflictCard } from './AlertComponents';
import { LANGUAGES, DEMO_QUERIES } from '@/lib/constants';
import { sendChatMessage } from '@/lib/api';
import { useVoice } from '@/hooks/useVoice';
import type { ChatMessage, ChatResponse, Language } from '@/types';

interface ChatPanelProps {
  onResponse?: (response: ChatResponse) => void;
  defaultLat?: number;
  defaultLon?: number;
}

// Stage messages for progressive loading display
const LOADING_STAGES = [
  'Fetching Marine Data...',
  'Analysing Weather...',
  'Calculating Safety Score...',
  'Checking Boundaries...',
  'Resolving Conflicts...',
  'Generating Response...',
];

function ThinkingBubble({ stage }: { stage: string }) {
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
          <p className="text-slate-400 text-[11px] mt-0.5 animate-pulse">{stage}</p>
        </div>
      </div>
    </div>
  );
}

function UserMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex items-end gap-2 justify-end animate-slide-up">
      <div className="chat-bubble-user">
        <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        <p className="text-[10px] text-white/50 mt-1">
          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}

function AssistantMessage({ msg }: { msg: ChatMessage }) {
  const r = msg.response;
  const isDemo = r?.is_demo;

  return (
    <div className="flex items-start gap-3 animate-slide-up">
      {/* Avatar */}
      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-500 to-teal-600 flex items-center justify-center flex-shrink-0 mt-1">
        <span className="text-white text-xs font-bold">O</span>
      </div>

      <div className="flex flex-col gap-2 min-w-0 flex-1">
        {/* Demo banner */}
        {isDemo && (
          <div className="flex items-center gap-1.5 text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-2.5 py-1.5">
            <AlertTriangle className="w-3 h-3" />
            <span className="font-semibold">DEMO DATA — Not live observation</span>
          </div>
        )}

        {/* Main answer bubble */}
        <div className="chat-bubble-assistant">
          <p className="leading-relaxed whitespace-pre-wrap text-slate-200">{msg.content}</p>
          <p className="text-[10px] text-slate-600 mt-2">
            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            {r?.request_id && <span className="ml-2 font-mono">#{r.request_id}</span>}
          </p>
        </div>

        {/* Critic conflict */}
        {r?.critic?.has_conflict && r.critic.conflicts.length > 0 && (
          <CriticConflictCard
            hasConflict
            sourceA={r.critic.conflicts[0].source_a}
            valueA={r.critic.conflicts[0].source_a_value}
            sourceB={r.critic.conflicts[0].source_b}
            valueB={r.critic.conflicts[0].source_b_value}
            resolution={r.critic.conflicts[0].resolution}
          />
        )}

        {/* Agent trace */}
        {r?.trace && (
          <AgentTraceView trace={r.trace} />
        )}
      </div>
    </div>
  );
}

export default function ChatPanel({ onResponse, defaultLat = 13.0827, defaultLon = 80.2707 }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'system',
      content: '',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState('');
  const [language, setLanguage] = useState<Language>(LANGUAGES[0]);
  const [showLangMenu, setShowLangMenu] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const stageTimerRef = useRef<NodeJS.Timeout>();
  const stageIdx = useRef(0);

  const { isListening, transcript, isSpeaking, startListening, stopListening, speak, stopSpeaking, supported: voiceSupported } = useVoice();

  // Sync voice transcript to input
  useEffect(() => {
    if (transcript) setInput(transcript);
  }, [transcript]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Cycling loading stages for UX
  const startLoadingCycle = () => {
    stageIdx.current = 0;
    setLoadingStage(LOADING_STAGES[0]);
    stageTimerRef.current = setInterval(() => {
      stageIdx.current = (stageIdx.current + 1) % LOADING_STAGES.length;
      setLoadingStage(LOADING_STAGES[stageIdx.current]);
    }, 1400);
  };

  const stopLoadingCycle = () => {
    if (stageTimerRef.current) clearInterval(stageTimerRef.current);
    setLoadingStage('');
  };

  const handleSend = useCallback(async (queryOverride?: string) => {
    const q = (queryOverride ?? input).trim();
    if (!q || isLoading) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: q,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    startLoadingCycle();

    try {
      const resp = await sendChatMessage({
        query: q,
        language: language.code,
        latitude: defaultLat,
        longitude: defaultLon,
      });

      const assistMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: resp.answer,
        timestamp: new Date(),
        response: resp,
      };

      setMessages((prev) => [...prev, assistMsg]);
      onResponse?.(resp);

      // Auto-speak response
      if (voiceSupported && resp.answer) {
        speak(resp.answer, language.code);
      }
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'ORCA could not complete the reasoning workflow. Please check the backend is running and retry.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      stopLoadingCycle();
    }
  }, [input, isLoading, language, defaultLat, defaultLon, onResponse, speak, voiceSupported]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="px-4 py-3 border-b border-slate-800/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-semibold text-slate-200">Conversational Assistant</span>
        </div>
        {/* Language selector */}
        <div className="relative">
          <button
            onClick={() => setShowLangMenu((v) => !v)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/60 border border-slate-700/50 hover:border-cyan-500/30 transition-colors"
          >
            <Globe className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-300">{language.nativeLabel}</span>
          </button>
          {showLangMenu && (
            <div className="absolute right-0 top-8 z-50 glass-card-dark border border-cyan-500/15 rounded-xl p-1.5 w-44 shadow-xl animate-slide-up">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => { setLanguage(lang); setShowLangMenu(false); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex justify-between
                    ${language.code === lang.code ? 'bg-cyan-500/15 text-cyan-400' : 'text-slate-400 hover:bg-slate-700/50 hover:text-slate-200'}`}
                >
                  <span>{lang.label}</span>
                  <span className="text-slate-500">{lang.nativeLabel}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Welcome */}
        <div className="text-center py-4 animate-fade-in">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-teal-600/20 border border-cyan-500/20 mb-3">
            <span className="text-2xl">🌊</span>
          </div>
          <h2 className="text-sm font-semibold text-slate-300 mb-1">Welcome to ORCA</h2>
          <p className="text-xs text-slate-500 max-w-xs mx-auto leading-relaxed">
            Ask anything about marine safety, fishing zones, weather, or routes. I&apos;ll reason across real data and explain my findings.
          </p>
          {/* Quick demo buttons */}
          <div className="mt-4 flex flex-wrap gap-2 justify-center">
            {DEMO_QUERIES.map((dq) => (
              <button
                key={dq.query}
                onClick={() => handleSend(dq.query)}
                disabled={isLoading}
                className="text-[11px] px-3 py-1.5 rounded-full border border-cyan-500/20 text-cyan-400/70 hover:border-cyan-500/50 hover:text-cyan-400 transition-all bg-cyan-500/5 hover:bg-cyan-500/10 disabled:opacity-40"
              >
                {dq.label}
              </button>
            ))}
          </div>
        </div>

        {messages.filter((m) => m.role !== 'system').map((msg) =>
          msg.role === 'user' ? (
            <UserMessage key={msg.id} msg={msg} />
          ) : (
            <AssistantMessage key={msg.id} msg={msg} />
          )
        )}

        {/* Loading bubble */}
        {isLoading && <ThinkingBubble stage={loadingStage} />}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-slate-800/60 p-4">
        <div className="flex items-end gap-2">
          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              id="chat-input"
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask ORCA anything about the sea..."
              disabled={isLoading}
              className="w-full bg-slate-800/50 border border-slate-700/50 hover:border-cyan-500/30 focus:border-cyan-500/50 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 resize-none outline-none transition-colors leading-relaxed disabled:opacity-50"
              style={{ maxHeight: 120 }}
            />
          </div>

          {/* Voice */}
          {voiceSupported && (
            <button
              id="voice-btn"
              onClick={() => isListening ? stopListening() : startListening(language.code)}
              disabled={isLoading}
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

          {/* TTS toggle */}
          {voiceSupported && (
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

          {/* Send */}
          <button
            id="send-btn"
            onClick={() => handleSend()}
            disabled={isLoading || !input.trim()}
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
