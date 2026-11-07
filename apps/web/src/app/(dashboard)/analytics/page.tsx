import type { Metadata } from 'next';
import { BusinessAnalytics } from '@/features/analytics/business-analytics';

export const metadata: Metadata = {
  title: 'DEXTRA · Analytics',
};

export default function AnalyticsPage() {
  return <BusinessAnalytics />;
}
