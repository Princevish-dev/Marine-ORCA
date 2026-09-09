'use client';

import { useState, useRef, useCallback } from 'react';

export interface VoiceHookReturn {
  isListening: boolean;
  transcript: string;
  isSpeaking: boolean;
  startListening: (lang: string) => void;
  stopListening: () => void;
  speak: (text: string, lang: string) => void;
  stopSpeaking: () => void;
  supported: boolean;
}

export function useVoice(): VoiceHookReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const recognitionRef = useRef<any>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const supported =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) &&
    'speechSynthesis' in window;

  const startListening = useCallback((lang: string) => {
    if (!supported) return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const rec = new SpeechRecognition();
    rec.lang = lang === 'hi' ? 'hi-IN' :
                lang === 'bn' ? 'bn-BD' :
                lang === 'ta' ? 'ta-IN' :
                lang === 'te' ? 'te-IN' :
                lang === 'mr' ? 'mr-IN' :
                lang === 'gu' ? 'gu-IN' :
                lang === 'kn' ? 'kn-IN' : 'en-IN';
    rec.continuous = false;
    rec.interimResults = true;

    rec.onstart = () => setIsListening(true);
    rec.onend = () => setIsListening(false);
    rec.onerror = () => setIsListening(false);
    rec.onresult = (e: any) => {
      const result = Array.from(e.results)
        .map((r: any) => r[0].transcript)
        .join('');
      setTranscript(result);
    };

    recognitionRef.current = rec;
    rec.start();
  }, [supported]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const speak = useCallback((text: string, lang: string) => {
    if (!supported || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text.slice(0, 800));
    utter.lang = lang === 'hi' ? 'hi-IN' :
                  lang === 'ta' ? 'ta-IN' :
                  lang === 'te' ? 'te-IN' :
                  lang === 'bn' ? 'bn-BD' : 'en-IN';
    utter.rate = 0.9;
    utter.onstart = () => setIsSpeaking(true);
    utter.onend = () => setIsSpeaking(false);
    utter.onerror = () => setIsSpeaking(false);
    utteranceRef.current = utter;
    window.speechSynthesis.speak(utter);
  }, [supported]);

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);
  }, []);

  return { isListening, transcript, isSpeaking, startListening, stopListening, speak, stopSpeaking, supported };
}
