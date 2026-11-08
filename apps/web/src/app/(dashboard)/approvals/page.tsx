import type { Metadata } from 'next';
import { DemoNotice } from '@/components/demo-notice';
import { ApprovalCenter } from '@/features/approvals/approval-center';

export const metadata: Metadata = {
  title: 'DEXTRA — Approvals',
};

export default function ApprovalsPage() {
  return (
    <>
      <DemoNotice />
      <ApprovalCenter />
    </>
  );
}
