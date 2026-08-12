'use client';

import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import { useAgent, useSessionContext, useSessionMessages } from '@livekit/components-react';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { Shimmer } from '@/components/ai-elements/shimmer';
import { EduStateBanner } from '@/components/app/edu-state-banner';
import { EscalationsDashboard } from '@/components/app/escalations-dashboard';
import { cn } from '@/lib/shadcn/utils';
import { TileLayout } from './tile-view';

const MotionMessage = motion.create(Shimmer);

const BOTTOM_VIEW_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

const CHAT_MOTION_PROPS: MotionProps = {
  variants: {
    hidden: {
      opacity: 0,
      transition: { ease: 'easeOut', duration: 0.3 },
    },
    visible: {
      opacity: 1,
      transition: { delay: 0.2, ease: 'easeOut', duration: 0.3 },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const SHIMMER_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      transition: { ease: 'easeIn', duration: 0.5, delay: 0.8 },
    },
    hidden: {
      opacity: 0,
      transition: { ease: 'easeIn', duration: 0.5, delay: 0 },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

export interface AgentSessionView_01Props {
  /**
   * Message shown above the controls before the first chat message is sent.
   * @default 'Ask me anything — speak in Telugu or English!'
   */
  preConnectMessage?: string;
  /** Enables or disables the chat toggle and transcript input controls. @default true */
  supportsChatInput?: boolean;
  /** Enables or disables camera controls in the bottom control bar. @default false */
  supportsVideoInput?: boolean;
  /** Enables or disables screen sharing controls in the bottom control bar. @default false */
  supportsScreenShare?: boolean;
  /** Shows a pre-connect buffer state with a shimmer message before messages appear. @default true */
  isPreConnectBufferEnabled?: boolean;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;
  /** Called just before the session ends via the user's END CALL button. */
  onUserEnd?: () => void;
  className?: string;
}

/** Detect if the user has blocked microphone permissions */
function useMicPermission() {
  const [micBlocked, setMicBlocked] = useState(false);

  useEffect(() => {
    let permStatus: PermissionStatus | null = null;

    const check = async () => {
      try {
        permStatus = await navigator.permissions.query({
          name: 'microphone',
        } as PermissionDescriptor);
        setMicBlocked(permStatus.state === 'denied');
        permStatus.onchange = () => {
          setMicBlocked(permStatus?.state === 'denied');
        };
      } catch {
        // Permissions API not supported — ignore
      }
    };

    check();
    return () => {
      if (permStatus) permStatus.onchange = null;
    };
  }, []);

  return micBlocked;
}

export function AgentSessionView_01({
  preConnectMessage = 'Ask me anything — speak in Telugu or English!',
  supportsChatInput = true,
  supportsVideoInput = false,
  supportsScreenShare = false,
  isPreConnectBufferEnabled = true,

  audioVisualizerType,
  audioVisualizerColor,
  audioVisualizerColorShift,
  audioVisualizerBarCount,
  audioVisualizerGridRowCount,
  audioVisualizerGridColumnCount,
  audioVisualizerRadialBarCount,
  audioVisualizerRadialRadius,
  audioVisualizerWaveLineWidth,
  onUserEnd,
  ref,
  className,
  ...props
}: React.ComponentProps<'section'> & AgentSessionView_01Props) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(false);
  const [showEscalations, setShowEscalations] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { state: agentState } = useAgent();
  const micBlocked = useMicPermission();

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: supportsVideoInput,
    screenShare: supportsScreenShare,
  };

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;
    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section
      ref={ref}
      className={cn('bg-background relative z-10 h-full w-full overflow-hidden', className)}
      {...props}
    >
      <Fade top className="absolute inset-x-4 top-0 z-10 h-40" />

      {/* Floating Teacher Escalation Desk button in active session */}
      <button
        type="button"
        onClick={() => setShowEscalations(true)}
        className="fixed top-4 right-4 z-40 flex items-center gap-2 rounded-xl border border-white/15 bg-[#0F0F23]/80 px-3.5 py-2 text-xs font-bold text-orange-300 shadow-xl backdrop-blur-md transition-all hover:border-orange-500/50 hover:bg-orange-500/20 hover:text-white"
      >
        <span>📋</span>
        <span>Teacher Desk</span>
      </button>

      {/* Escalation Dashboard Modal */}
      {showEscalations && <EscalationsDashboard onClose={() => setShowEscalations(false)} />}

      {/* Microphone blocked — full-width error bar */}
      <AnimatePresence>
        {micBlocked && (
          <motion.div
            initial={{ opacity: 0, y: -40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -40 }}
            transition={{ duration: 0.35 }}
            className="absolute top-0 right-0 left-0 z-30 flex items-center justify-center gap-3 border-b border-red-500/30 bg-red-950/70 px-4 py-3 backdrop-blur-md"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              className="flex-shrink-0 text-red-400"
            >
              <path
                d="M12 22C17.5 22 22 17.5 22 12C22 6.5 17.5 2 12 2C6.5 2 2 6.5 2 12C2 17.5 6.5 22 12 22ZM11 7H13V13H11V7ZM11 15H13V17H11V15Z"
                fill="currentColor"
              />
            </svg>
            <div className="text-center">
              <p className="text-sm font-bold text-red-300">Microphone access blocked</p>
              <p className="text-xs text-red-400/80">
                Click the lock icon in your browser address bar → allow microphone → refresh the
                page
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Transcript */}
      <div className="absolute top-0 bottom-[135px] flex w-full flex-col md:bottom-[170px]">
        <AnimatePresence>
          {chatOpen && (
            <motion.div
              {...CHAT_MOTION_PROPS}
              className="flex h-full w-full flex-col gap-4 space-y-3 transition-opacity duration-300 ease-out"
            >
              <AgentChatTranscript
                agentState={agentState}
                messages={messages}
                className="mx-auto w-full max-w-2xl [&_.is-user>div]:rounded-[22px] [&>div>div]:px-4 [&>div>div]:pt-40 md:[&>div>div]:px-6"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Audio visualiser tile + state banner */}
      <TileLayout
        chatOpen={chatOpen}
        agentState={agentState}
        micBlocked={micBlocked}
        audioVisualizerType={audioVisualizerType}
        audioVisualizerColor={audioVisualizerColor}
        audioVisualizerColorShift={audioVisualizerColorShift}
        audioVisualizerBarCount={audioVisualizerBarCount}
        audioVisualizerRadialBarCount={audioVisualizerRadialBarCount}
        audioVisualizerRadialRadius={audioVisualizerRadialRadius}
        audioVisualizerGridRowCount={audioVisualizerGridRowCount}
        audioVisualizerGridColumnCount={audioVisualizerGridColumnCount}
        audioVisualizerWaveLineWidth={audioVisualizerWaveLineWidth}
      />

      {/* Bottom controls */}
      <motion.div
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="absolute inset-x-3 bottom-0 z-50 md:inset-x-12"
      >
        {/* Pre-connect message */}
        {isPreConnectBufferEnabled && (
          <AnimatePresence>
            {messages.length === 0 && (
              <MotionMessage
                key="pre-connect-message"
                duration={2}
                aria-hidden={messages.length > 0}
                {...SHIMMER_MOTION_PROPS}
                className="pointer-events-none mx-auto block w-full max-w-2xl pb-4 text-center text-sm font-semibold text-white/50"
              >
                {preConnectMessage}
              </MotionMessage>
            )}
          </AnimatePresence>
        )}

        <div className="bg-background relative mx-auto max-w-2xl pb-3 md:pb-12">
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />
          <AgentControlBar
            variant="livekit"
            controls={controls}
            isChatOpen={chatOpen}
            isConnected={session.isConnected}
            onDisconnect={() => {
              onUserEnd?.();
              session.end();
            }}
            onIsChatOpenChange={setChatOpen}
          />
        </div>
      </motion.div>
    </section>
  );
}
