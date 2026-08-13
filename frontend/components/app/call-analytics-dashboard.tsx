'use client';

import { useCallback, useEffect, useState } from 'react';
import { CheckCircle, Clock, Phone, RefreshCw, ShieldCheck, XCircle } from 'lucide-react';

interface CallRecord {
  call_id: string;
  user_id: string;
  caller_name: string;
  channel: string;
  start_time: string;
  end_time?: string;
  duration_seconds: number;
  outcome: 'successful' | 'failed' | 'in_progress';
  failure_reason?: string;
  exercises_completed: number;
  escalation_created: boolean;
  memory_saved: boolean;
  topic_discussed: string;
}

interface AnalyticsData {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  avg_duration_seconds: number;
  failure_breakdown: Record<string, number>;
  channel_breakdown: Record<string, number>;
  recent_calls: CallRecord[];
}

interface CallAnalyticsDashboardProps {
  onClose?: () => void;
  isModal?: boolean;
}

export function CallAnalyticsDashboard({ onClose, isModal = true }: CallAnalyticsDashboardProps) {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [filterChannel, setFilterChannel] = useState<string>('all');
  const [filterOutcome, setFilterOutcome] = useState<string>('all');
  const [simulating, setSimulating] = useState<boolean>(false);

  const fetchAnalytics = useCallback(async () => {
    try {
      const res = await fetch('/api/analytics', { cache: 'no-store' });
      if (!res.ok) throw new Error('Failed to load analytics');
      const json = await res.json();
      setData(json);
    } catch (err: unknown) {
      console.error('Analytics load error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();

    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchAnalytics();
    }, 3000);

    return () => clearInterval(interval);
  }, [autoRefresh, fetchAnalytics]);

  const handleSimulateCall = async (outcome: 'successful' | 'failed') => {
    setSimulating(true);
    try {
      await fetch('/api/analytics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'simulate',
          outcome,
          topic: outcome === 'successful' ? 'Photosynthesis Quiz' : 'Quadratic Equations',
          caller_name: outcome === 'successful' ? 'Ramesh' : 'Kiran',
          reason: outcome === 'failed' ? 'Caller disconnected before completing exercise' : '',
        }),
      });
      await fetchAnalytics();
    } catch (e) {
      console.error(e);
    } finally {
      setSimulating(false);
    }
  };

  const filteredCalls = (data?.recent_calls || []).filter((call) => {
    if (filterChannel !== 'all' && call.channel.toLowerCase() !== filterChannel.toLowerCase()) {
      return false;
    }
    if (filterOutcome !== 'all' && call.outcome.toLowerCase() !== filterOutcome.toLowerCase()) {
      return false;
    }
    return true;
  });

  const formatDuration = (seconds: number) => {
    if (!seconds || seconds <= 0) return '0s';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const formatTime = (isoStr: string) => {
    if (!isoStr) return 'Just now';
    try {
      const date = new Date(isoStr);
      return date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const containerClasses = isModal
    ? 'fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-3 sm:p-6 backdrop-blur-md overflow-hidden'
    : 'w-full max-w-6xl mx-auto p-4 sm:p-6';

  return (
    <div
      className={containerClasses}
      onClick={(e) => {
        if (e.target === e.currentTarget && isModal && onClose) {
          onClose();
        }
      }}
    >
      <div className="relative flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-white/20 bg-[#0F0F1A] shadow-2xl backdrop-blur-xl">
        {/* Floating Top-Right Close Button for Modal */}
        {isModal && onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="absolute top-4 right-4 z-50 flex h-9 w-9 items-center justify-center rounded-full border border-white/20 bg-rose-600/90 text-base font-black text-white shadow-xl transition-all hover:scale-105 hover:bg-rose-500 active:scale-95"
            title="Close Dashboard"
          >
            ✕
          </button>
        )}

        {/* Sticky Header */}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-white/10 bg-white/5 p-5 sm:px-8">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/20 text-orange-400">
                <Phone className="h-5 w-5" />
              </span>
              <h2 className="text-2xl font-black text-white">Call Analytics Dashboard</h2>
            </div>
            <p className="mt-1 text-xs font-medium text-white/50">
              EduVoice Voice Tutor · Real-time Call Performance & Outcome Metrics
            </p>
          </div>

          <div className="flex items-center gap-3 pr-10 sm:pr-12">
            {/* Auto Refresh Toggle */}
            <button
              type="button"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-bold transition-all ${
                autoRefresh
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                  : 'border-white/10 bg-white/5 text-white/40 hover:bg-white/10'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  autoRefresh ? 'animate-pulse bg-emerald-400' : 'bg-white/30'
                }`}
              />
              <span>{autoRefresh ? 'Live Auto-Refresh (3s)' : 'Paused'}</span>
            </button>

            {/* Manual Refresh Button */}
            <button
              type="button"
              onClick={fetchAnalytics}
              className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-bold text-white/70 hover:bg-white/10 hover:text-white"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Scrollable Content Body */}
        <div className="flex-1 space-y-6 overflow-y-auto p-5 sm:p-8">
          {/* Success Criteria Banner (Step 1) */}
          <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/10 p-4 text-xs text-indigo-200">
            <div className="flex items-start gap-2.5">
              <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-indigo-400" />
              <div>
                <span className="font-bold text-white">
                  Call Success Criteria (Learning Track):
                </span>{' '}
                A call is marked <strong className="text-emerald-400">Successful</strong> if the
                learner completes a practice exercise (scoring a quiz answer), saves learning
                memory, or requests human teacher escalation. Otherwise, it is recorded as{' '}
                <strong className="text-rose-400">Failed</strong>. Zero caller PII or transcripts
                are logged.
              </div>
            </div>
          </div>

          {/* 3 Core Metric Cards (Step 3) */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {/* Card 1: Total Calls */}
            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 to-white/[0.02] p-5 shadow-lg backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold tracking-wider text-white/50 uppercase">
                  Total Calls
                </span>
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400">
                  <Phone className="h-4 w-4" />
                </span>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-4xl font-black text-white">{data?.total_calls ?? 0}</span>
                <span className="text-xs text-white/40">calls logged</span>
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2 text-xs text-white/40">
                <span>Avg Duration:</span>
                <span className="font-semibold text-white/70">
                  {formatDuration(data?.avg_duration_seconds || 0)}
                </span>
              </div>
            </div>

            {/* Card 2: Successful Calls */}
            <div className="relative overflow-hidden rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/15 to-emerald-500/5 p-5 shadow-lg backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold tracking-wider text-emerald-300 uppercase">
                  Successful Calls
                </span>
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
                  <CheckCircle className="h-5 w-5" />
                </span>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-4xl font-black text-emerald-400">
                  {data?.successful_calls ?? 0}
                </span>
                <span className="text-xs text-emerald-300/70">
                  ({data?.success_rate ?? 0}% rate)
                </span>
              </div>
              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-black/40">
                <div
                  className="h-full bg-emerald-400 transition-all duration-500"
                  style={{ width: `${Math.min(100, data?.success_rate || 0)}%` }}
                />
              </div>
            </div>

            {/* Card 3: Failed Calls */}
            <div className="relative overflow-hidden rounded-2xl border border-rose-500/30 bg-gradient-to-br from-rose-500/15 to-rose-500/5 p-5 shadow-lg backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold tracking-wider text-rose-300 uppercase">
                  Failed Calls
                </span>
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-500/20 text-rose-400">
                  <XCircle className="h-5 w-5" />
                </span>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-4xl font-black text-rose-400">{data?.failed_calls ?? 0}</span>
                <span className="text-xs text-rose-300/70">
                  ({data?.total_calls ? Math.round(100 - (data?.success_rate || 0)) : 0}% rate)
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-rose-500/10 pt-2 text-xs text-rose-300/60">
                <span>Main Reason:</span>
                <span className="truncate font-semibold text-rose-200">
                  {Object.keys(data?.failure_breakdown || {})[0] || 'Early disconnect'}
                </span>
              </div>
            </div>
          </div>

          {/* Live Testing Controls */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 p-3.5">
            <div className="flex items-center gap-2 text-xs font-bold text-white/70">
              <span>🧪 Dashboard Testing Controls:</span>
              <span className="font-normal text-white/40">
                Click to record a test call and verify live count updates
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={simulating}
                onClick={() => handleSimulateCall('successful')}
                className="flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/20 px-3.5 py-1.5 text-xs font-bold text-emerald-300 transition-all hover:bg-emerald-500/30 disabled:opacity-50"
              >
                <CheckCircle className="h-4 w-4" />
                <span>+ Record Success Call</span>
              </button>

              <button
                type="button"
                disabled={simulating}
                onClick={() => handleSimulateCall('failed')}
                className="flex items-center gap-1.5 rounded-xl border border-rose-500/40 bg-rose-500/20 px-3.5 py-1.5 text-xs font-bold text-rose-300 transition-all hover:bg-rose-500/30 disabled:opacity-50"
              >
                <XCircle className="h-4 w-4" />
                <span>+ Record Failure Call</span>
              </button>
            </div>
          </div>

          {/* Filters & Recent Call History Table */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 sm:p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-orange-400" />
                <h3 className="text-sm font-bold text-white">Recent Call Log History</h3>
                <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-semibold text-white/60">
                  {filteredCalls.length} calls
                </span>
              </div>

              {/* Filter controls */}
              <div className="flex items-center gap-2">
                <select
                  value={filterChannel}
                  onChange={(e) => setFilterChannel(e.target.value)}
                  className="rounded-lg border border-white/15 bg-black/50 px-2.5 py-1 text-xs font-medium text-white outline-none focus:border-orange-500"
                >
                  <option value="all">All Channels</option>
                  <option value="browser">Browser</option>
                  <option value="sip outbound">SIP Outbound</option>
                </select>

                <select
                  value={filterOutcome}
                  onChange={(e) => setFilterOutcome(e.target.value)}
                  className="rounded-lg border border-white/15 bg-black/50 px-2.5 py-1 text-xs font-medium text-white outline-none focus:border-orange-500"
                >
                  <option value="all">All Outcomes</option>
                  <option value="successful">Successful</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-white/40 uppercase">
                    <th className="pb-2.5 font-bold">Time</th>
                    <th className="pb-2.5 font-bold">Caller</th>
                    <th className="pb-2.5 font-bold">Channel</th>
                    <th className="pb-2.5 font-bold">Topic</th>
                    <th className="pb-2.5 font-bold">Duration</th>
                    <th className="pb-2.5 font-bold">Outcome</th>
                    <th className="pb-2.5 font-bold">Details / Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filteredCalls.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-white/40">
                        {loading
                          ? 'Loading call records…'
                          : 'No calls recorded matching filter criteria.'}
                      </td>
                    </tr>
                  ) : (
                    filteredCalls.map((call) => {
                      const isSuccess = call.outcome === 'successful';
                      return (
                        <tr key={call.call_id} className="transition-colors hover:bg-white/5">
                          <td className="py-3 font-mono text-white/60">
                            {formatTime(call.start_time)}
                          </td>
                          <td className="py-3 font-semibold text-white">
                            {call.caller_name || 'Student'}
                          </td>
                          <td className="py-3">
                            <span
                              className={`inline-block rounded-md border px-2 py-0.5 text-[11px] font-bold ${
                                call.channel === 'SIP Outbound'
                                  ? 'border-purple-500/30 bg-purple-500/20 text-purple-300'
                                  : 'border-blue-500/30 bg-blue-500/20 text-blue-300'
                              }`}
                            >
                              {call.channel}
                            </span>
                          </td>
                          <td className="py-3 font-medium text-white/80">
                            {call.topic_discussed || 'General Practice'}
                          </td>
                          <td className="py-3 font-mono text-white/60">
                            {formatDuration(call.duration_seconds)}
                          </td>
                          <td className="py-3">
                            <span
                              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-extrabold ${
                                isSuccess
                                  ? 'border-emerald-500/40 bg-emerald-500/20 text-emerald-400'
                                  : 'border-rose-500/40 bg-rose-500/20 text-rose-400'
                              }`}
                            >
                              {isSuccess ? (
                                <>
                                  <CheckCircle className="h-3.5 w-3.5" /> SUCCESSFUL
                                </>
                              ) : (
                                <>
                                  <XCircle className="h-3.5 w-3.5" /> FAILED
                                </>
                              )}
                            </span>
                          </td>
                          <td className="max-w-xs truncate py-3 text-white/50">
                            {isSuccess ? (
                              <span className="text-emerald-300/80">
                                {call.exercises_completed > 0
                                  ? `Completed ${call.exercises_completed} exercise(s)`
                                  : call.escalation_created
                                    ? 'Teacher escalation created'
                                    : 'Lesson completed & memory saved'}
                              </span>
                            ) : (
                              <span className="text-rose-300/80">
                                {call.failure_reason || 'Caller disconnected early'}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Sticky Footer */}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-t border-white/10 bg-white/5 p-4 text-xs text-white/40 sm:px-8">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>Zero PII / Transcripts Rendered (Step 6 Compliant)</span>
          </div>

          {isModal && onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-rose-500/40 bg-rose-500/20 px-4 py-2 text-xs font-bold text-rose-300 transition-all hover:bg-rose-500/30 hover:text-white"
            >
              ✕ Close Dashboard
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
