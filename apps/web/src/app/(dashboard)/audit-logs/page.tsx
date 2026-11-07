import type { Metadata } from 'next';
import { AuditLogs } from '@/features/audit-logs/audit-logs';

export const metadata: Metadata = {
  title: 'DEXTRA · Audit Logs',
};

export default function AuditLogsPage() {
  return <AuditLogs />;
}
