import { Metadata } from 'next';
import { CallAnalyticsDashboard } from '@/components/app/call-analytics-dashboard';

export const metadata: Metadata = {
  title: 'Call Analytics Dashboard | EduVoice AI',
  description:
    'Real-time call performance metrics, success rate, and call history for EduVoice AI Voice Tutor.',
};

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-[#0A0A1A] py-8 text-white">
      <CallAnalyticsDashboard isModal={false} />
    </main>
  );
}
