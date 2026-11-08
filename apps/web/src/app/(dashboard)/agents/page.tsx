import type { Metadata } from 'next';
import { DemoNotice } from '@/components/demo-notice';
import { AgentWorkforce } from '@/features/agents/agent-workforce';

export const metadata: Metadata = {
  title: 'Agent Workforce — DEXTRA',
  description:
    'Manage domain-specific AI agents, governance boundaries, and autonomous task loads.',
};

export default function AgentsPage() {
  return (
    <>
      <DemoNotice />
      <AgentWorkforce />
    </>
  );
}
