import type { Metadata } from 'next';
import { FinanceManagement } from '@/features/finance/finance-management';

export const metadata: Metadata = {
  title: 'DEXTRA · Finance',
};

export default function FinancePage() {
  return <FinanceManagement />;
}
