/**
 * Agent and orchestration contracts.
 */

import type { RiskLevel } from '../domain';

export interface AgentPermissions {
  read: string[];
  analyze: string[];
  recommend: string[];
  prepare: string[];
  execute: string[];
}

export interface AIAgent {
  id: string;
  name: string;
  department: string;
  role: string;
  status: 'online' | 'busy' | 'idle' | 'offline';
  avatarUrl: string;
  workloadPercent: number;
  successRate: number;
  currentTask: string;
  permissions: AgentPermissions;
  recentActivity: string;
  executionCount: number;
  tools: string[];
  config: {
    maxDailySpendLimit: number;
    autoApprovalConfidence: number;
    modelTier: string;
  };
}

export interface OrchestrationStep {
  id: string;
  title: string;
  agentId: string;
  agentName: string;
  status: 'pending' | 'running' | 'completed' | 'requires_human_review';
  description: string;
  outputSummary?: string;
  resultPayload?: unknown;
  timestamp: string;
}

export interface WorkBuddyReportMetric {
  label: string;
  value: string;
  change?: string;
}

export interface WorkBuddySession {
  id: string;
  prompt: string;
  status: 'idle' | 'decomposing' | 'orchestrating' | 'awaiting_approval' | 'completed';
  steps: OrchestrationStep[];
  consolidatedReport?: {
    title: string;
    summary: string;
    metrics: WorkBuddyReportMetric[];
    recommendations: string[];
    actionRequired?: string;
    approvalRequestId?: string;
  };
  createdAt: string;
}

