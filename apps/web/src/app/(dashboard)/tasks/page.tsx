import type { Metadata } from 'next';
import { OperationsTasks } from '@/features/operations/operations-tasks';

export const metadata: Metadata = {
  title: 'Tasks & Workflows · DEXTRA',
  description:
    'Synchronized execution across human operational specialists and autonomous AI agent workers.',
};

export default function TasksPage() {
  return <OperationsTasks />;
}
