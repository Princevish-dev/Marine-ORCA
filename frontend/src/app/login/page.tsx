'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { Shield, Mail, Lock, User, Ship } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
  const [Islogin, Setislogin] = useState(true);
  const [Email, Setemail] = useState('');
  const [Password, Setpassword] = useState('');
  const [Fullname, Setfullname] = useState('');
  const [Vesselname, Setvesselname] = useState('');
  const [Loading, Setloading] = useState(false);
  const [Error, Seterror] = useState('');
  const Router = useRouter();

  const Handleauth = async (e: React.FormEvent) => {
    e.preventDefault();
    Setloading(true);
    Seterror('');

    try {
      if (Islogin) {
        const { error } = await supabase.auth.signInWithPassword({
          email: Email,
          password: Password,
        });
        if (error) throw error;
        Router.push('/');
      } else {
        const { error } = await supabase.auth.signUp({
          email: Email,
          password: Password,
          options: {
            data: {
              full_name: Fullname,
              vessel_name: Vesselname,
            },
          },
        });
        if (error) throw error;
        Setislogin(true);
        Seterror('Signup successful! You can now log in.');
      }
    } catch (err: any) {
      Seterror(err.message);
    } finally {
      Setloading(false);
    }
  };

  const Handlegooglelogin = async () => {
    Setloading(true);
    Seterror('');
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/`,
        }
      });
      if (error) throw error;
    } catch (err: any) {
      Seterror(err.message);
    } finally {
      Setloading(false);
    }
  };

  const [Mounted, Setmounted] = useState(false);
  useEffect(() => Setmounted(true), []);

  if (!Mounted) return null;

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#030712] relative overflow-hidden">
      <div className="absolute inset-0 z-0 opacity-20">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-500/30 rounded-full blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-teal-500/30 rounded-full blur-[100px]" />
      </div>

      <div className="w-full max-w-md z-10">
        <div className="glass-card-dark p-8 border-cyan-500/20">
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-teal-500/20 border border-cyan-500/40 flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-cyan-400" />
            </div>
            <h1 className="text-2xl font-bold tracking-widest text-white uppercase">ORCA</h1>
            <p className="text-xs text-slate-400 tracking-widest uppercase mt-1">Marine Intelligence</p>
          </div>

          {Error && (
            <div className={`p-3 rounded-lg text-xs font-medium mb-6 ${Error.includes('successful') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
              {Error}
            </div>
          )}

          <form onSubmit={Handleauth} className="space-y-4">
            {!Islogin && (
              <>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="w-4 h-4 text-slate-500" />
                  </div>
                  <input
                    type="text"
                    required
                    placeholder="Full Name"
                    value={Fullname}
                    onChange={(e) => Setfullname(e.target.value)}
                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50 transition-colors"
                  />
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Ship className="w-4 h-4 text-slate-500" />
                  </div>
                  <input
                    type="text"
                    placeholder="Vessel Name (Optional)"
                    value={Vesselname}
                    onChange={(e) => Setvesselname(e.target.value)}
                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50 transition-colors"
                  />
                </div>
              </>
            )}

            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Mail className="w-4 h-4 text-slate-500" />
              </div>
              <input
                type="email"
                required
                placeholder="Email Address"
                value={Email}
                onChange={(e) => Setemail(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50 transition-colors"
              />
            </div>

            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="w-4 h-4 text-slate-500" />
              </div>
              <input
                type="password"
                required
                placeholder="Password"
                value={Password}
                onChange={(e) => Setpassword(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={Loading}
              className="w-full bg-cyan-500 hover:bg-cyan-400 text-slate-900 font-semibold py-2.5 rounded-lg text-sm transition-colors mt-2"
            >
              {Loading ? 'Authenticating...' : Islogin ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <div className="my-6 flex items-center before:mt-0.5 before:flex-1 before:border-t before:border-slate-700 after:mt-0.5 after:flex-1 after:border-t after:border-slate-700">
            <p className="mx-4 mb-0 text-center text-xs font-semibold text-slate-500 uppercase">OR</p>
          </div>

          <button
            onClick={Handlegooglelogin}
            disabled={Loading}
            className="w-full bg-white hover:bg-slate-50 text-slate-900 font-semibold py-2.5 rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign in with Google
          </button>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                Setislogin(!Islogin);
                Seterror('');
              }}
              className="text-xs text-cyan-500/70 hover:text-cyan-400 transition-colors"
            >
              {Islogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
