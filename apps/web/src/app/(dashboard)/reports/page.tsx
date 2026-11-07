import type { Metadata } from 'next';
import { ReportsCenter } from '@/features/reports/reports-center';

export const metadata: Metadata = {
  title: 'DEXTRA · Reports',
};

export default function ReportsPage() {
  return <ReportsCenter />;
}
