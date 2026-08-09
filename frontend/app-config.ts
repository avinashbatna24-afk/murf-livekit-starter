export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorDark?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;

  // agent dispatch configuration
  agentName?: string;

  // LiveKit Cloud Sandbox configuration
  sandboxId?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  // ── EduVoice Branding ───────────────────────────────────────────────
  companyName: 'EduVoice',
  pageTitle: 'EduVoice — AI Voice Tutor for Indian Students',
  pageDescription:
    'Learn Maths, Science, Programming & English with EduVoice — your AI tutor powered by Murf Falcon, the fastest TTS API. Speak in Telugu, English, or both!',

  // ── Feature flags ───────────────────────────────────────────────────
  supportsChatInput: true, // keep live transcript
  supportsVideoInput: false, // no camera needed for voice tutor
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  // ── Visual identity ─────────────────────────────────────────────────
  logo: '/murf-logo.svg',
  logoDark: '/murf-logo-dark.svg',
  accent: '#F97316', // saffron
  accentDark: '#FDBA74', // lighter saffron for dark
  startButtonText: 'Start Learning',

  // ── Audio visualiser — aura style in saffron/indigo ─────────────────
  audioVisualizerType: 'aura',
  audioVisualizerColor: '#F97316',
  audioVisualizerColorDark: '#FDBA74',
  audioVisualizerColorShift: 0.4,

  // ── Agent dispatch ──────────────────────────────────────────────────
  agentName: process.env.AGENT_NAME ?? undefined,

  // ── LiveKit Cloud Sandbox ───────────────────────────────────────────
  sandboxId: undefined,
};
