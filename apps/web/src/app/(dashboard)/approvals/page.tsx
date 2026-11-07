import type { Metadata } from 'next';
import { ApprovalCenter } from '@/features/approvals/approval-center';

export const metadata: Metadata = {
  title: 'DEXTRA · Approvals',
};

export default function ApprovalsPage() {
  return <ApprovalCenter />;
}
