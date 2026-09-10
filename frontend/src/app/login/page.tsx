'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { setToken, getToken } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (getToken()) {
      router.push('/');
    }
  }, [router]);

  return (
    <div className="h-screen flex items-center justify-center" style={{ background: 'var(--navy-950)' }}>
      <div className="glass-card p-8 max-w-sm w-full text-center flex flex-col items-center">
        <h1 className="text-2xl font-bold text-white mb-2">ORCA Marine</h1>
        <p className="text-sm text-slate-400 mb-8">Sign in to access the decision-support platform</p>
        
        {error && (
          <div className="mb-4 text-xs text-red-400 bg-red-400/10 p-2 rounded border border-red-400/20">
            {error}
          </div>
        )}

        <button
          onClick={() => {
            setToken('local-dev-token');
            router.push('/');
          }}
          className="bg-cyan-500 hover:bg-cyan-400 text-slate-900 font-bold py-2 px-6 rounded-full transition-colors"
        >
          Enter Local Workspace
        </button>
      </div>
    </div>
  );
}
