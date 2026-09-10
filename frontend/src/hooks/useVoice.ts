'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

export interface VoiceHookReturn {
  isListening: boolean;
  transcript: string;
  isSpeaking: boolean;
  startListening: (lang: string) => void;
  stopListening: () => void;
  speak: (text: string, lang: string) => void;
  stopSpeaking: () => void;
  supported: boolean;
  useBhashini: boolean;
}

const BHASHINI_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getLanguageCode(lang: string): string {
  return lang === 'hi' ? 'hi-IN' :
         lang === 'bn' ? 'bn-BD' :
         lang === 'ta' ? 'ta-IN' :
         lang === 'te' ? 'te-IN' :
         lang === 'mr' ? 'mr-IN' :
         lang === 'gu' ? 'gu-IN' :
         lang === 'kn' ? 'kn-IN' : 'en-IN';
}

function getBhashiniLang(lang: string): string {
  return lang === 'hi' ? 'hi' :
         lang === 'bn' ? 'bn' :
         lang === 'ta' ? 'ta' :
         lang === 'te' ? 'te' :
         lang === 'mr' ? 'mr' :
         lang === 'gu' ? 'gu' :
         lang === 'kn' ? 'kn' : 'en';
}

function audioBlobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function base64ToAudioBlob(base64: string, mimeType: string): Blob {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
}

export function useVoice(): VoiceHookReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [useBhashini, setUseBhashini] = useState(false);
  const recognitionRef = useRef<any>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const supported =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) &&
    'speechSynthesis' in window;

  useEffect(() => {
    const checkBhashini = async () => {
      try {
        const res = await fetch(`${BHASHINI_API_URL}/api/bhashini/health`);
        const data = await res.json();
        setUseBhashini(data.configured === true);
      } catch {
        setUseBhashini(false);
      }
    };
    checkBhashini();
  }, []);

  const startListening = useCallback(async (lang: string) => {
    if (!supported) return;

    if (useBhashini) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm;codecs=opus' });
          const base64Audio = await audioBlobToBase64(audioBlob);
          
          try {
            const res = await fetch(`${BHASHINI_API_URL}/api/bhashini/asr`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                audio_base64: base64Audio,
                language: getBhashiniLang(lang),
                sample_rate: 16000,
              }),
            });
            if (res.ok) {
              const data = await res.json();
              setTranscript(data.transcript || '');
            }
          } catch (err) {
            console.error('Bhashini ASR error:', err);
          }
          stream.getTracks().forEach(t => t.stop());
        };

        mediaRecorder.start();
        setIsListening(true);
      } catch (err) {
        console.error('Microphone access error:', err);
        setIsListening(false);
      }
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const rec = new SpeechRecognition();
    rec.lang = getLanguageCode(lang);
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
  }, [supported, useBhashini]);

  const stopListening = useCallback(() => {
    if (useBhashini && mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    } else {
      recognitionRef.current?.stop();
    }
    setIsListening(false);
  }, [useBhashini]);

  const speak = useCallback(async (text: string, lang: string) => {
    if (!supported) return;

    if (useBhashini) {
      try {
        const res = await fetch(`${BHASHINI_API_URL}/api/bhashini/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text.slice(0, 800),
            language: getBhashiniLang(lang),
          }),
        });
        if (res.ok) {
          const data = await res.json();
          const audioBlob = base64ToAudioBlob(data.audio_base64, data.mime_type || 'audio/wav');
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          audio.onplay = () => setIsSpeaking(true);
          audio.onended = () => {
            setIsSpeaking(false);
            URL.revokeObjectURL(audioUrl);
          };
          audio.onerror = () => {
            setIsSpeaking(false);
            URL.revokeObjectURL(audioUrl);
          };
          await audio.play();
        }
      } catch (err) {
        console.error('Bhashini TTS error:', err);
      }
      return;
    }

    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text.slice(0, 800));
    utter.lang = getLanguageCode(lang);
    utter.rate = 0.9;
    utter.onstart = () => setIsSpeaking(true);
    utter.onend = () => setIsSpeaking(false);
    utter.onerror = () => setIsSpeaking(false);
    utteranceRef.current = utter;
    window.speechSynthesis.speak(utter);
  }, [supported, useBhashini]);

  const stopSpeaking = useCallback(() => {
    if (useBhashini) {
      // For Bhashini, we can't easily stop the audio playback
      // This would require storing the Audio reference
    } else {
      window.speechSynthesis?.cancel();
    }
    setIsSpeaking(false);
  }, [useBhashini]);

  return { isListening, transcript, isSpeaking, startListening, stopListening, speak, stopSpeaking, supported, useBhashini };
}
