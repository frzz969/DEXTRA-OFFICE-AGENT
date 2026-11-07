import type { Metadata } from 'next';
import { AgentWorkforce } from '@/features/agents/agent-workforce';

export const metadata: Metadata = {
  title: 'Agent Workforce · DEXTRA',
  description:
    'Manage domain-specific AI agents, governance boundaries, and autonomous task loads.',
};

export default function AgentsPage() {
  return <AgentWorkforce />;
}
