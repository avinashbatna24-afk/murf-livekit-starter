'use client';

import React from 'react';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';

interface CallEndedViewProps {
  onRestart: () => void;
}

function BookIcon() {
  return (
    <svg
      width="80"
      height="80"
      viewBox="0 0 80 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Book body */}
      <rect x="12" y="14" width="56" height="52" rx="4" fill="url(#bookGrad)" opacity="0.15" />
      <rect x="12" y="14" width="56" height="52" rx="4" stroke="url(#bookGrad)" strokeWidth="2" />
      {/* Spine */}
      <line x1="28" y1="14" x2="28" y2="66" stroke="url(#bookGrad)" strokeWidth="2" />
      {/* Pages */}
      <line x1="36" y1="28" x2="58" y2="28" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.4" strokeLinecap="round" />
      <line x1="36" y1="36" x2="58" y2="36" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.4" strokeLinecap="round" />
      <line x1="36" y1="44" x2="52" y2="44" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.4" strokeLinecap="round" />
      {/* Star */}
      <path
        d="M40 4L42.47 9.62L48.51 10.24L44.15 14.26L45.53 20.18L40 17.02L34.47 20.18L35.85 14.26L31.49 10.24L37.53 9.62L40 4Z"
        fill="url(#starGrad)"
      />
      <defs>
        <linearGradient id="bookGrad" x1="12" y1="14" x2="68" y2="66" gradientUnits="userSpaceOnUse">
          <stop stopColor="#F97316" />
          <stop offset="1" stopColor="#6366F1" />
        </linearGradient>
        <linearGradient id="starGrad" x1="31" y1="4" x2="49" y2="20" gradientUnits="userSpaceOnUse">
          <stop stopColor="#F97316" />
          <stop offset="1" stopColor="#FDBA74" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export const CallEndedView = ({
  onRestart,
  ref,
}: React.ComponentProps<'div'> & CallEndedViewProps) => {
  return (
    <div ref={ref} className="flex h-svh w-full flex-col items-center justify-center px-6 text-center">
      {/* Animated illustration */}
      <motion.div
        initial={{ scale: 0.7, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
        className="animate-float mb-8"
      >
        <div className="relative mx-auto flex h-32 w-32 items-center justify-center rounded-3xl border border-white/10 bg-white/5 backdrop-blur-sm">
          <BookIcon />
        </div>
      </motion.div>

      {/* Heading */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25, duration: 0.5 }}
        className="mb-3"
      >
        <h1 className="text-3xl font-extrabold tracking-tight text-white">
          Great session! 🎉
        </h1>
        <p className="mt-2 text-base text-white/50 font-medium">
          మీరు చాలా బాగా చేశారు! — You did amazing!
        </p>
      </motion.div>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
        className="mb-8 w-full max-w-sm rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm"
      >
        <p className="text-sm text-white/60 leading-relaxed">
          Your call with EduVoice has ended. Every question you asked brings you
          one step closer to mastering your subject. Keep that curiosity alive! 🌟
        </p>
        <div className="mt-4 flex items-center justify-center gap-2">
          {['Maths', 'Science', 'Code', 'English'].map((sub) => (
            <span
              key={sub}
              className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white/70"
            >
              {sub}
            </span>
          ))}
        </div>
      </motion.div>

      {/* CTA */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.55, duration: 0.4 }}
      >
        <Button
          id="restart-call-button"
          size="lg"
          onClick={onRestart}
          className="animate-glow-saffron w-64 rounded-full bg-gradient-to-r from-[#F97316] to-[#EA580C] py-6 text-sm font-extrabold tracking-widest text-white uppercase shadow-xl hover:opacity-90 transition-opacity"
        >
          🎓 Start Again
        </Button>
      </motion.div>

      {/* Footer */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7, duration: 0.5 }}
        className="mt-10 text-xs text-white/25 font-mono tracking-wider"
      >
        Powered by Murf Falcon · VoiceForBharat
      </motion.p>
    </div>
  );
}
