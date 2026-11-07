import type { Metadata } from 'next';
import { AIWorkspace } from '@/features/ai-workspace/ai-workspace';

export const metadata: Metadata = {
  title: 'AI Workspace · DEXTRA',
  description:
    'Instruct the WorkBuddy orchestrator to decompose enterprise operations across specialized agents.',
};

export default function AIWorkspacePage() {
  return <AIWorkspace />;
}
