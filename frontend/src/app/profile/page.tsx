'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { User, Ship, LogOut, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function ProfilePage() {
  const [Loading, Setloading] = useState(true);
  const [Saving, Setsaving] = useState(false);
  const [Usr, Setusr] = useState<any>(null);
  const [Fullname, Setfullname] = useState('');
  const [Vesselname, Setvesselname] = useState('');
  const [Message, Setmessage] = useState('');
  const Router = useRouter();

  useEffect(() => {
    async function Loadprofile() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        Router.push('/login');
        return;
      }
      Setusr(session.user);

      const { data } = await supabase
        .from('profiles')
        .select('full_name, vessel_name')
        .eq('id', session.user.id)
        .single();

      if (data) {
        Setfullname(data.full_name || '');
        Setvesselname(data.vessel_name || '');
      }
      Setloading(false);
    }
    Loadprofile();
  }, [Router]);

  const Updateprofile = async (e: React.FormEvent) => {
    e.preventDefault();
    Setsaving(true);
    Setmessage('');

    const { error } = await supabase.from('profiles').upsert({
      id: Usr.id,
      full_name: Fullname,
      vessel_name: Vesselname,
    });

    if (error) {
      Setmessage(`Error: ${error.message}`);
    } else {
      Setmessage('Profile updated successfully.');
    }
    Setsaving(false);
  };

  const Handlelogout = async () => {
    await supabase.auth.signOut();
    Router.push('/login');
  };

  if (Loading) return null;

  return (
    <div className="min-h-screen p-6 bg-[#030712] text-slate-200">
      <div className="max-w-2xl mx-auto mt-10">
        <div className="flex items-center justify-between mb-8">
          <Link href="/" className="flex items-center gap-2 text-sm text-cyan-500 hover:text-cyan-400 transition-colors">
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <button
            onClick={Handlelogout}
            className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>

        <div className="glass-card-dark p-8">
          <h1 className="text-2xl font-bold tracking-widest text-white mb-6 uppercase">Vessel Profile</h1>
          
          {Message && (
            <div className={`p-3 rounded-lg text-sm mb-6 ${Message.includes('Error') ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
              {Message}
            </div>
          )}

          <form onSubmit={Updateprofile} className="space-y-6">
            <div>
              <label className="block text-xs text-slate-400 uppercase tracking-wider mb-2">Account Email</label>
              <input
                type="text"
                disabled
                value={Usr?.email || ''}
                className="w-full bg-slate-900/50 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-500 cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 uppercase tracking-wider mb-2">Captain / Full Name</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="w-4 h-4 text-slate-500" />
                </div>
                <input
                  type="text"
                  value={Fullname}
                  onChange={(e) => Setfullname(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 uppercase tracking-wider mb-2">Vessel Name</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Ship className="w-4 h-4 text-slate-500" />
                </div>
                <input
                  type="text"
                  value={Vesselname}
                  onChange={(e) => Setvesselname(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={Saving}
              className="px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-900 font-semibold rounded-lg text-sm transition-colors"
            >
              {Saving ? 'Saving...' : 'Save Profile'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
