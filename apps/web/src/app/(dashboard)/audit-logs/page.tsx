import type { Metadata } from 'next';
import { DemoNotice } from '@/components/demo-notice';
import { AuditLogs } from '@/features/audit-logs/audit-logs';

export const metadata: Metadata = {
  title: 'DEXTRA — Audit Logs',
};

export default function AuditLogsPage() {
  return (
    <>
      <DemoNotice />
      <AuditLogs />
    </>
  );
}
