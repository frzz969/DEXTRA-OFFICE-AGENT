import type { Metadata } from 'next';
import { OperationsTasks } from '@/features/operations/operations-tasks';

export const metadata: Metadata = {
  title: 'Operations & SLAs · DEXTRA',
  description:
    'Task orchestration, SLA delivery and workflow execution across human and AI workers.',
};

export default function OperationsPage() {
  return <OperationsTasks />;
}
