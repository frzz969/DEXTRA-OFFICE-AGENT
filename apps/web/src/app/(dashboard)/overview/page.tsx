import type { Metadata } from 'next';
import { ExecutiveOverview } from '@/features/overview/executive-overview';

export const metadata: Metadata = {
  title: 'Executive Overview · DEXTRA',
  description:
    'Real-time status of multi-agent workforce orchestration, ERP pipelines, and human governance.',
};

export default function OverviewPage() {
  return <ExecutiveOverview />;
}
