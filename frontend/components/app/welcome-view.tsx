'use client';

import { useState } from 'react';
import { EscalationsDashboard } from '@/components/app/escalations-dashboard';

const SUBJECTS = [
  {
    label: 'Maths',
    emoji: '📐',
    color: 'from-orange-500/20 to-orange-500/5 border-orange-500/30 text-orange-300',
  },
  {
    label: 'Science',
    emoji: '🔬',
    color: 'from-teal-500/20 to-teal-500/5 border-teal-500/30 text-teal-300',
  },
  {
    label: 'Python',
    emoji: '🐍',
    color: 'from-indigo-500/20 to-indigo-500/5 border-indigo-500/30 text-indigo-300',
  },
  {
    label: 'Java',
    emoji: '☕',
    color: 'from-amber-500/20 to-amber-500/5 border-amber-500/30 text-amber-300',
  },
  {
    label: 'English',
    emoji: '📚',
    color: 'from-pink-500/20 to-pink-500/5 border-pink-500/30 text-pink-300',
  },
  {
    label: 'GK',
    emoji: '🌍',
    color: 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/30 text-cyan-300',
  },
];

function MortarBoardMic() {
  return (
    <svg
      width="88"
      height="88"
      viewBox="0 0 88 88"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Glow circle */}
      <circle cx="44" cy="44" r="42" fill="url(#welcomeGlow)" opacity="0.12" />

      {/* Mortarboard hat */}
      <polygon points="44,14 78,28 44,42 10,28" fill="url(#hatGrad)" opacity="0.95" />
      <rect x="36" y="28" width="16" height="18" rx="3" fill="url(#hatGrad)" opacity="0.7" />
      {/* Tassel */}
      <line
        x1="78"
        y1="28"
        x2="78"
        y2="44"
        stroke="#F97316"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="78" cy="46" r="3" fill="#F97316" />

      {/* Microphone body */}
      <rect x="35" y="46" width="14" height="20" rx="7" fill="url(#micGrad)" />
      {/* Mic stand */}
      <path d="M44 66 Q44 74 44 74" stroke="#6366F1" strokeWidth="2" strokeLinecap="round" />
      <line
        x1="37"
        y1="74"
        x2="51"
        y2="74"
        stroke="#6366F1"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {/* Sound waves */}
      <path
        d="M30 53 Q26 56 26 60 Q26 64 30 67"
        stroke="#14B8A6"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
        opacity="0.8"
      />
      <path
        d="M25 50 Q18 55 18 60 Q18 65 25 70"
        stroke="#14B8A6"
        strokeWidth="1.4"
        strokeLinecap="round"
        fill="none"
        opacity="0.5"
      />
      <path
        d="M58 53 Q62 56 62 60 Q62 64 58 67"
        stroke="#14B8A6"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
        opacity="0.8"
      />
      <path
        d="M63 50 Q70 55 70 60 Q70 65 63 70"
        stroke="#14B8A6"
        strokeWidth="1.4"
        strokeLinecap="round"
        fill="none"
        opacity="0.5"
      />

      <defs>
        <linearGradient id="hatGrad" x1="10" y1="14" x2="78" y2="42" gradientUnits="userSpaceOnUse">
          <stop stopColor="#F97316" />
          <stop offset="1" stopColor="#6366F1" />
        </linearGradient>
        <linearGradient id="micGrad" x1="35" y1="46" x2="49" y2="66" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366F1" />
          <stop offset="1" stopColor="#14B8A6" />
        </linearGradient>
        <radialGradient id="welcomeGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#F97316" />
          <stop offset="100%" stopColor="#6366F1" />
        </radialGradient>
      </defs>
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  studentName?: string;
  setStudentName?: (name: string) => void;
  onStartCall: (userName: string) => void;
}

export const WelcomeView = ({
  startButtonText,
  studentName: externalStudentName,
  setStudentName: externalSetStudentName,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const [internalName, setInternalName] = useState('Ramesh');
  const [showEscalations, setShowEscalations] = useState(false);

  const currentName = externalStudentName !== undefined ? externalStudentName : internalName;
  const updateName = (val: string) => {
    setInternalName(val);
    if (externalSetStudentName) {
      externalSetStudentName(val);
    }
  };

  const handleStart = () => {
    const nameToUse = currentName.trim() || 'Student';
    onStartCall(nameToUse);
  };

  return (
    <div
      ref={ref}
      className="relative flex h-svh w-full flex-col items-center justify-center px-6 text-center"
    >
      {/* Mascot icon */}
      <div className="animate-float mb-4 flex h-24 w-24 items-center justify-center rounded-3xl border border-white/10 bg-white/5 shadow-2xl backdrop-blur-sm">
        <MortarBoardMic />
      </div>

      {/* Main heading */}
      <h1 className="mb-1 text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
        <span className="eduvoice-text-gradient">EduVoice</span>
      </h1>

      {/* English subtitle */}
      <p className="mb-1 text-base font-semibold text-white/70">
        Your AI Voice Tutor with Persistent Memory
      </p>

      {/* Telugu tagline */}
      <p className="mb-4 text-sm font-medium text-white/40" lang="te">
        మీ AI చదువుల గురువు (సంగతులు గుర్తుంచుకునే వాయిస్ ఏజెంట్)
      </p>

      {/* Subject chips */}
      <div className="mb-5 flex flex-wrap items-center justify-center gap-2">
        {SUBJECTS.map(({ label, emoji, color }) => (
          <span
            key={label}
            className={`flex items-center gap-1.5 rounded-full border bg-gradient-to-b px-3 py-1 text-xs font-bold ${color}`}
          >
            <span>{emoji}</span>
            <span>{label}</span>
          </span>
        ))}
      </div>

      {/* Student Login Card */}
      <div
        suppressHydrationWarning
        className="mb-6 w-full max-w-sm rounded-2xl border border-white/10 bg-white/5 p-4 shadow-xl backdrop-blur-md"
      >
        <label
          htmlFor="student-name-input"
          className="mb-2 block text-left text-xs font-bold tracking-wider text-orange-400 uppercase"
        >
          👤 Student Profile / Login Identity
        </label>
        <div className="relative mb-3">
          <input
            suppressHydrationWarning
            id="student-name-input"
            type="text"
            value={currentName}
            onChange={(e) => updateName(e.target.value)}
            placeholder="Enter your name (e.g. Ramesh)..."
            className="w-full rounded-xl border border-white/15 bg-black/40 px-4 py-2.5 text-sm font-medium text-white placeholder-white/30 transition-all outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
          />
        </div>

        {/* Quick select profile chips */}
        <div className="flex items-center justify-between gap-1.5 text-xs">
          <span className="font-medium text-white/40">Quick login:</span>
          <div className="flex gap-1.5">
            <button
              suppressHydrationWarning
              type="button"
              onClick={() => updateName('Ramesh')}
              className={`rounded-lg border px-2.5 py-1 text-xs font-bold transition-all ${
                currentName.toLowerCase() === 'ramesh'
                  ? 'border-orange-500 bg-orange-500/20 text-orange-300'
                  : 'border-white/10 bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              🎓 Ramesh
            </button>
            <button
              suppressHydrationWarning
              type="button"
              onClick={() => updateName('Priya')}
              className={`rounded-lg border px-2.5 py-1 text-xs font-bold transition-all ${
                currentName.toLowerCase() === 'priya'
                  ? 'border-teal-500 bg-teal-500/20 text-teal-300'
                  : 'border-white/10 bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              🔬 Priya
            </button>
          </div>
        </div>
      </div>

      {/* CTA button */}
      <button
        suppressHydrationWarning
        id="start-call-button"
        onClick={handleStart}
        className="animate-glow-saffron group relative mb-4 overflow-hidden rounded-full bg-gradient-to-r from-[#F97316] to-[#EA580C] px-10 py-4 text-sm font-extrabold tracking-widest text-white uppercase shadow-2xl transition-all duration-300 hover:scale-105 hover:opacity-95 active:scale-95"
      >
        <span className="relative z-10 flex items-center gap-2">
          🎓{' '}
          <span>
            {startButtonText} ({currentName.trim() || 'Student'})
          </span>
        </span>
        {/* Shimmer overlay */}
        <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
      </button>

      {/* Instruction text */}
      <p className="mb-4 text-xs font-medium text-white/35">
        Speak in Telugu, English, or both — I remember your facts across calls!
      </p>

      {/* Teacher Escalation Desk button */}
      <button
        type="button"
        onClick={() => setShowEscalations(true)}
        className="mb-6 flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-xs font-bold text-orange-300 backdrop-blur-sm transition-all hover:border-orange-500/50 hover:bg-orange-500/10 hover:text-white"
      >
        <span>📋</span>
        <span>Teacher Escalation Desk</span>
      </button>

      {/* Escalation Dashboard Modal */}
      {showEscalations && <EscalationsDashboard onClose={() => setShowEscalations(false)} />}

      {/* Divider */}
      <div className="mb-4 h-px w-32 bg-gradient-to-r from-transparent via-white/15 to-transparent" />

      {/* Footer */}
      <p className="font-mono text-xs tracking-wider text-white/25">
        Powered by{' '}
        <a
          href="https://murf.ai"
          target="_blank"
          rel="noopener noreferrer"
          className="text-white/40 underline underline-offset-2 transition-colors hover:text-white/60"
        >
          Murf Falcon
        </a>{' '}
        · LiveKit Agents · #VoiceForBharat
      </p>
    </div>
  );
};
