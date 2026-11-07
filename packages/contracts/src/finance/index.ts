/**
 * Finance contracts.
 */

export interface LedgerTransaction {
  id: string;
  date: string;
  description: string;
  category: string;
  department: string;
  amount: number;
  type: 'income' | 'expense';
  status: 'cleared' | 'pending' | 'flagged';
  approvedBy?: string;
}

export interface DepartmentBudget {
  department: string;
  allocated: number;
  spent: number;
  remaining: number;
  projectedVariance: number;
}

export interface PayrollBatch {
  id: string;
  month: string;
  totalGross: number;
  netPay: number;
  employeesCount: number;
  status: 'draft' | 'pending_approval' | 'approved' | 'processed';
  processedDate?: string;
}
