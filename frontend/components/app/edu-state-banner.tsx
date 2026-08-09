'use client';

import React from 'react';
import { AnimatePresence, motion } from 'motion/react';
import type { AgentState } from '@livekit/components-react';

interface EduStateBannerProps {
  agentState: AgentState | undefined;
  micBlocked?: boolean;
}

type StateConfig = {
  label: string;
  sublabel?: string;
  icon: React.ReactNode;
  color: string;
  showDots?: boolean;
  showWave?: boolean;
};

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 1C10.34 1 9 2.34 9 4V12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12V4C15 2.34 13.66 1 12 1Z"
        fill="currentColor"
      />
      <path
        d="M19 12C19 15.87 15.87 19 12 19C8.13 19 5 15.87 5 12H3C3 16.97 6.47 21.16 11 21.9V24H13V21.9C17.53 21.16 21 16.97 21 12H19Z"
        fill="currentColor"
      />
    </svg>
  );
}

function SpeakerIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M3 9V15H7L12 20V4L7 9H3ZM16.5 12C16.5 10.23 15.48 8.71 14 7.97V16.02C15.48 15.29 16.5 13.77 16.5 12ZM14 3.23V5.29C16.89 6.15 19 8.83 19 12C19 15.17 16.89 17.85 14 18.71V20.77C18.01 19.86 21 16.28 21 12C21 7.72 18.01 4.14 14 3.23Z"
        fill="currentColor"
      />
    </svg>
  );
}

function ThinkingIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8V12L14 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function ConnectingIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20ZM12.5 7H11V13L16.25 16.15L17 14.92L12.5 12.25V7Z"
        fill="currentColor"
      />
    </svg>
  );
}

function getStateConfig(agentState: AgentState | undefined, micBlocked: boolean): StateConfig {
  if (micBlocked) {
    return {
      label: 'Microphone blocked',
      sublabel: 'Open browser settings → allow mic access → refresh',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M19 11H7.83L13.42 5.41L12 4L4 12L12 20L13.41 18.59L7.83 13H19V11Z"
            fill="currentColor"
          />
          <line
            x1="2"
            y1="2"
            x2="22"
            y2="22"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      ),
      color: 'bg-red-500/15 border-red-500/30 text-red-400',
    };
  }

  switch (agentState) {
    case 'connecting':
      return {
        label: 'Joining your session…',
        icon: <ConnectingIcon />,
        color: 'bg-indigo-500/15 border-indigo-500/30 text-indigo-300',
        showDots: true,
      };
    case 'listening':
      return {
        label: 'Listening to you',
        icon: <MicIcon />,
        color: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
        showWave: true,
      };
    case 'thinking':
      return {
        label: 'EduVoice is thinking',
        icon: <ThinkingIcon />,
        color: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
        showDots: true,
      };
    case 'speaking':
      return {
        label: 'EduVoice is speaking',
        icon: <SpeakerIcon />,
        color: 'bg-orange-500/15 border-orange-500/30 text-orange-300',
        showWave: true,
      };
    default:
      return {
        label: 'Ready to help',
        icon: <MicIcon />,
        color: 'bg-white/5 border-white/10 text-white/50',
      };
  }
}

export function EduStateBanner({ agentState, micBlocked = false }: EduStateBannerProps) {
  const config = getStateConfig(agentState, micBlocked);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={micBlocked ? 'mic-blocked' : (agentState ?? 'idle')}
        initial={{ opacity: 0, y: -8, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.96 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className={`inline-flex flex-col items-center gap-1`}
      >
        {/* State pill */}
        <div
          className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold backdrop-blur-sm ${config.color}`}
        >
          <span className="flex-shrink-0">{config.icon}</span>
          <span>{config.label}</span>

          {/* Animated dots */}
          {config.showDots && (
            <span className="ml-1 flex items-center gap-0.5">
              <span className="dot-1 h-1.5 w-1.5 rounded-full bg-current" />
              <span className="dot-2 h-1.5 w-1.5 rounded-full bg-current" />
              <span className="dot-3 h-1.5 w-1.5 rounded-full bg-current" />
            </span>
          )}

          {/* Animated wave bars */}
          {config.showWave && (
            <span className="ml-1 flex h-4 items-end gap-0.5">
              <span
                className="animate-wave-1 inline-block w-1 rounded-sm bg-current"
                style={{ height: '60%' }}
              />
              <span
                className="animate-wave-2 inline-block w-1 rounded-sm bg-current"
                style={{ height: '100%' }}
              />
              <span
                className="animate-wave-3 inline-block w-1 rounded-sm bg-current"
                style={{ height: '80%' }}
              />
              <span
                className="animate-wave-4 inline-block w-1 rounded-sm bg-current"
                style={{ height: '40%' }}
              />
              <span
                className="animate-wave-5 inline-block w-1 rounded-sm bg-current"
                style={{ height: '70%' }}
              />
            </span>
          )}
        </div>

        {/* Sub-label for mic blocked */}
        {config.sublabel && (
          <p className="max-w-xs px-2 text-center text-xs leading-relaxed text-red-400/80">
            {config.sublabel}
          </p>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
