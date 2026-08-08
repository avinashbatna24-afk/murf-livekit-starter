'use client';

import { useState, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';
import { CallEndedView } from '@/components/app/call-ended-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);
const MotionCallEndedView = motion.create(CallEndedView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: { opacity: 1 as number, scale: 1 as number },
    hidden:  { opacity: 0 as number, scale: 0.97 as number },
  },
  initial: 'hidden' as const,
  animate: 'visible' as const,
  exit: 'hidden' as const,
  transition: {
    duration: 0.45,
    ease: 'easeInOut' as const,
  },
};

type ViewState = 'welcome' | 'connecting' | 'session' | 'ended';

interface ViewControllerProps {
  appConfig: AppConfig;
}

/** Connecting overlay — shown while LiveKit session is establishing */
function ConnectingOverlay() {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0A0A1A]">
      <div className="relative mb-8 flex items-center justify-center">
        <div className="animate-pulse-ring absolute h-36 w-36 rounded-full border border-indigo-500/20" style={{ animationDelay: '0s' }} />
        <div className="animate-pulse-ring absolute h-28 w-28 rounded-full border border-indigo-500/30" style={{ animationDelay: '0.3s' }} />
        <div className="animate-pulse-ring absolute h-20 w-20 rounded-full border border-indigo-500/40" style={{ animationDelay: '0.6s' }} />
        <div className="relative z-10 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-[#F97316] to-[#6366F1] shadow-lg">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M12 3L14.55 8.43L20.5 9.24L16.25 13.27L17.36 19.18L12 16.41L6.64 19.18L7.75 13.27L3.5 9.24L9.45 8.43L12 3Z" fill="white" fillOpacity="0.95" />
          </svg>
        </div>
      </div>
      <h2 className="text-xl font-extrabold text-white mb-2">Joining your session…</h2>
      <p className="text-sm text-white/45 font-medium">EduVoice is getting ready to help you learn</p>
      <div className="mt-4 flex items-center gap-1.5">
        <span className="dot-1 h-2 w-2 rounded-full bg-[#F97316]" />
        <span className="dot-2 h-2 w-2 rounded-full bg-[#F97316]" />
        <span className="dot-3 h-2 w-2 rounded-full bg-[#F97316]" />
      </div>
    </div>
  );
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start } = useSessionContext();
  const { state: agentState } = useAgent();
  const [viewState, setViewState] = useState<ViewState>('welcome');

  /**
   * Track whether the user intentionally clicked END CALL.
   * Stays false for error disconnects (agent not joined, crash, etc.).
   * Only true disconnects show the "Great session!" screen.
   */
  const userEndedRef = useRef(false);

  const handleUserEnd = () => {
    userEndedRef.current = true;
  };

  useEffect(() => {
    if (isConnected) {
      userEndedRef.current = false;
      setViewState('session');
    } else if (viewState === 'session' || viewState === 'connecting') {
      // Decide where to land based on how the session ended
      if (agentState === 'failed' || !userEndedRef.current) {
        // Error / forced disconnect → silently return to welcome
        setViewState('welcome');
      } else {
        // Normal user-clicked END CALL → celebration screen
        setViewState('ended');
      }
      userEndedRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected]);

  const handleStart = () => {
    setViewState('connecting');
    start();
  };

  const handleRestart = () => {
    setViewState('welcome');
  };

  return (
    <>
      <AnimatePresence>
        {viewState === 'connecting' && !isConnected && (
          <motion.div
            key="connecting"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-50"
          >
            <ConnectingOverlay />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {viewState === 'welcome' && (
          <MotionWelcomeView
            key="welcome"
            {...VIEW_MOTION_PROPS}
            startButtonText={appConfig.startButtonText}
            onStartCall={handleStart}
          />
        )}

        {viewState === 'session' && isConnected && (
          <MotionSessionView
            key="session-view"
            {...VIEW_MOTION_PROPS}
            supportsChatInput={appConfig.supportsChatInput}
            supportsVideoInput={appConfig.supportsVideoInput}
            supportsScreenShare={appConfig.supportsScreenShare}
            isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
            audioVisualizerType={appConfig.audioVisualizerType}
            audioVisualizerColor={appConfig.audioVisualizerColor}
            audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
            audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
            audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
            audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
            audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
            audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
            audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
            onUserEnd={handleUserEnd}
            className="fixed inset-0"
          />
        )}

        {viewState === 'ended' && (
          <MotionCallEndedView
            key="call-ended"
            {...VIEW_MOTION_PROPS}
            onRestart={handleRestart}
          />
        )}
      </AnimatePresence>
    </>
  );
}
