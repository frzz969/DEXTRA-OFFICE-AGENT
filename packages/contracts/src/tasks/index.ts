/**
 * Task contracts.
 */

import type { RiskLevel } from '../domain';

export interface EnterpriseTask {
  id: string;
  title: string;
  department: string;
  assigneeType: 'human' | 'agent';
  assigneeId: string;
  assigneeName: string;
  priority: RiskLevel;
  status: 'backlog' | 'in_progress' | 'pending_approval' | 'completed' | 'failed';
  dueDate: string;
  progress: number;
  workflowId?: string;
  tags: string[];
}
