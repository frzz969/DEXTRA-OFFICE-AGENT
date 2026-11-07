'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  VIEW_PATHS,
  viewPath,
  type AIAgent,
  type ApprovalRequest,
  type AuditLog,
  type DepartmentBudget,
  type Employee,
  type EnterpriseTask,
  type GovernancePolicy,
  type IntegrationService,
  type InventoryItem,
  type LedgerTransaction,
  type LeaveRequest,
  type NotificationItem,
  type PayrollBatch,
  type PurchaseOrder,
  type ViewMode,
  type WorkBuddySession,
} from '@dextra/contracts';
import {
  INITIAL_AGENTS,
  INITIAL_APPROVALS,
  INITIAL_AUDIT_LOGS,
  INITIAL_BUDGETS,
  INITIAL_EMPLOYEES,
  INITIAL_INTEGRATIONS,
  INITIAL_INVENTORY,
  INITIAL_LEAVE_REQUESTS,
  INITIAL_NOTIFICATIONS,
  INITIAL_PAYROLL,
  INITIAL_POLICIES,
  INITIAL_PURCHASE_ORDERS,
  INITIAL_TASKS,
  INITIAL_TRANSACTIONS,
  INITIAL_WORKBUDDY_SESSION,
} from '@/data/mock-store';

interface DextraContextType {
  currentView: ViewMode;
  setCurrentView: (view: ViewMode) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  isCommandPaletteOpen: boolean;
  setIsCommandPaletteOpen: (open: boolean) => void;
  isNotificationOpen: boolean;
  setIsNotificationOpen: (open: boolean) => void;
  selectedAgent: AIAgent | null;
  setSelectedAgent: (agent: AIAgent | null) => void;
  selectedEmployee: Employee | null;
  setSelectedEmployee: (emp: Employee | null) => void;
  agents: AIAgent[];
  approvals: ApprovalRequest[];
  tasks: EnterpriseTask[];
  employees: Employee[];
  leaveRequests: LeaveRequest[];
  inventory: InventoryItem[];
  purchaseOrders: PurchaseOrder[];
  budgets: DepartmentBudget[];
  transactions: LedgerTransaction[];
  payroll: PayrollBatch;
  policies: GovernancePolicy[];
  auditLogs: AuditLog[];
  integrations: IntegrationService[];
  notifications: NotificationItem[];
  activeSession: WorkBuddySession | null;
  isOrchestrating: boolean;
  currentJourney: number | null;
  handleApprove: (id: string, notes?: string) => void;
  handleReject: (id: string, reason?: string) => void;
  handleRequestChanges: (id: string, notes: string) => void;
  runWorkBuddyPrompt: (promptText: string) => Promise<void>;
  triggerJourney: (journeyId: 1 | 2 | 3 | 4) => void;
  syncIntegration: (id: string) => void;
  togglePolicy: (id: string) => void;
  markAllNotificationsRead: () => void;
}

const DextraContext = createContext<DextraContextType | undefined>(undefined);

/** Map a Next.js pathname back to a ViewMode (SSR-safe, returns null when unknown). */
function pathnameToView(pathname: string | null): ViewMode | null {
  if (!pathname) return null;
  const normalized = pathname.replace(/\/+$/, '') || '/';
  for (const [view, path] of Object.entries(VIEW_PATHS) as [ViewMode, string][]) {
    if (path === normalized) return view;
  }
  return null;
}

function generateHexHash(): string {
  const chars = '0123456789abcdef';
  let hash = '0x';
  for (let i = 0; i < 64; i++) {
    hash += chars[Math.floor(Math.random() * chars.length)];
  }
  return hash;
}

type ApprovalSupportingData = {
  vendor?: string;
  sku?: string;
  reorderQty?: number;
  unitCost?: number;
  employeeId?: string;
};

export const DextraProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();
  const router = useRouter();

  const [currentView, setCurrentViewState] = useState<ViewMode>(
    () => pathnameToView(pathname) ?? 'overview'
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AIAgent | null>(null);
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  const [currentJourney, setCurrentJourney] = useState<number | null>(null);

  const [agents, setAgents] = useState<AIAgent[]>(INITIAL_AGENTS);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>(INITIAL_APPROVALS);
  const [tasks, setTasks] = useState<EnterpriseTask[]>(INITIAL_TASKS);
  const [employees, setEmployees] = useState<Employee[]>(INITIAL_EMPLOYEES);
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>(INITIAL_LEAVE_REQUESTS);
  const [inventory, setInventory] = useState<InventoryItem[]>(INITIAL_INVENTORY);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>(INITIAL_PURCHASE_ORDERS);
  const [budgets] = useState<DepartmentBudget[]>(INITIAL_BUDGETS);
  const [transactions, setTransactions] = useState<LedgerTransaction[]>(INITIAL_TRANSACTIONS);
  const [payroll, setPayroll] = useState<PayrollBatch>(INITIAL_PAYROLL);
  const [policies, setPolicies] = useState<GovernancePolicy[]>(INITIAL_POLICIES);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>(INITIAL_AUDIT_LOGS);
  const [integrations, setIntegrations] = useState<IntegrationService[]>(INITIAL_INTEGRATIONS);
  const [notifications, setNotifications] = useState<NotificationItem[]>(INITIAL_NOTIFICATIONS);

  const [isOrchestrating, setIsOrchestrating] = useState(false);
  const [activeSession, setActiveSession] = useState<WorkBuddySession | null>(
    INITIAL_WORKBUDDY_SESSION
  );

  // Keep the tracked view in sync with the actual route (mount + browser navigation).
  useEffect(() => {
    const view = pathnameToView(pathname);
    if (view && view !== currentView) setCurrentViewState(view);
  }, [pathname, currentView]);

  // Global keydown for Command Palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const setCurrentView = (view: ViewMode) => {
    setCurrentViewState(view);
    const target = viewPath(view);
    if (typeof window !== 'undefined' && pathnameToView(window.location.pathname) !== view) {
      router.push(target);
    }
  };

  const handleApprove = (id: string, notes?: string) => {
    const targetApproval = approvals.find((a) => a.id === id);
    if (!targetApproval) return;
    const data = targetApproval.supportingData as ApprovalSupportingData;

    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const hash = generateHexHash();

    // 1. Update Approval item
    setApprovals((prev) =>
      prev.map((appr) =>
        appr.id === id
          ? {
              ...appr,
              status: 'approved',
              reviewedBy: 'Elena Rostova (Executive Operator)',
              reviewedAt: timestamp,
              notes: notes || appr.notes,
            }
          : appr
      )
    );

    // 2. Cascade side-effects based on actionType
    if (targetApproval.actionType === 'procurement_po') {
      // Update or insert PO
      setPurchaseOrders((prev) => {
        const existing = prev.find((po) => po.id === 'PO-8822');
        if (existing) {
          return prev.map((po) => (po.id === 'PO-8822' ? { ...po, status: 'approved' } : po));
        } else {
          return [
            {
              id: 'PO-8822',
              poNumber: 'PO-2026-8822',
              supplier: data.vendor || 'AeroTek Industrial Silicon',
              date: '2026-11-07',
              items: [
                {
                  sku: data.sku || 'EDG-GW-V3',
                  name: 'Enterprise Edge Gateway V3',
                  qty: data.reorderQty || 100,
                  unitCost: data.unitCost || 142.0,
                },
              ],
              totalAmount: targetApproval.amount || 14200.0,
              status: 'approved',
              generatedBy: 'Inventory & Procurement Agent',
              approvalRequestId: id,
            },
            ...prev,
          ];
        }
      });

      // Update inventory item status to 'reordered'
      setInventory((prev) =>
        prev.map((item) =>
          item.sku === (data.sku || 'EDG-GW-V3')
            ? { ...item, status: 'reordered', stockLevel: item.stockLevel }
            : item
        )
      );

      // Add cleared ledger expense
      setTransactions((prev) => [
        {
          id: `TX-${Math.floor(1000 + Math.random() * 9000)}`,
          date: '2026-11-07',
          description: `PO-2026-8822 Dispatch: 100x Edge Gateways (${data.vendor})`,
          category: 'Procurement',
          department: 'Operations',
          amount: targetApproval.amount || 14200.0,
          type: 'expense',
          status: 'cleared',
          approvedBy: 'Elena Rostova',
        },
        ...prev,
      ]);
    } else if (targetApproval.actionType === 'payroll_disbursement') {
      setPayroll((prev) => ({
        ...prev,
        status: 'approved',
        processedDate: timestamp,
      }));
    } else if (targetApproval.actionType === 'leave_approval') {
      setLeaveRequests((prev) =>
        prev.map((lr) =>
          lr.employeeId === data.employeeId ? { ...lr, status: 'approved' } : lr
        )
      );
    }

    // 3. Log Audit Record
    const newLog: AuditLog = {
      id: `LOG-${Math.floor(7800 + Math.random() * 1000)}`,
      timestamp,
      actorType: 'user',
      actorId: 'user-exec',
      actorName: 'Elena Rostova (Executive Operator)',
      action: `HUMAN_APPROVED_${targetApproval.actionType.toUpperCase()}`,
      targetResource: `${targetApproval.id} (${targetApproval.title})`,
      riskLevel: targetApproval.riskLevel,
      result: 'success',
      approvalId: id,
      hash,
      details: `Operator authorized request. Business justification verified: "${targetApproval.businessJustification}". Notes: ${notes || 'Standard sign-off.'}`,
    };
    setAuditLogs((prev) => [newLog, ...prev]);

    // 4. Notification
    setNotifications((prev) => [
      {
        id: `notif-${Date.now()}`,
        timestamp: 'Just now',
        title: 'Action Approved & Executed',
        message: `${targetApproval.title} signed off. Recorded to immutable audit log.`,
        type: 'approval',
        isRead: false,
        linkView: 'audit-logs',
      },
      ...prev,
    ]);
  };

  const handleReject = (id: string, reason?: string) => {
    const targetApproval = approvals.find((a) => a.id === id);
    if (!targetApproval) return;

    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const hash = generateHexHash();

    setApprovals((prev) =>
      prev.map((appr) =>
        appr.id === id
          ? {
              ...appr,
              status: 'rejected',
              reviewedBy: 'Elena Rostova (Executive Operator)',
              reviewedAt: timestamp,
              notes: reason || 'Operation denied by human oversight.',
            }
          : appr
      )
    );

    const newLog: AuditLog = {
      id: `LOG-${Math.floor(7800 + Math.random() * 1000)}`,
      timestamp,
      actorType: 'user',
      actorId: 'user-exec',
      actorName: 'Elena Rostova (Executive Operator)',
      action: `HUMAN_REJECTED_${targetApproval.actionType.toUpperCase()}`,
      targetResource: `${targetApproval.id} (${targetApproval.title})`,
      riskLevel: targetApproval.riskLevel,
      result: 'blocked',
      approvalId: id,
      hash,
      details: `Operator rejected action: ${reason || 'Denied by policy threshold'}. Execution halted.`,
    };
    setAuditLogs((prev) => [newLog, ...prev]);

    setNotifications((prev) => [
      {
        id: `notif-${Date.now()}`,
        timestamp: 'Just now',
        title: 'Action Blocked by Operator',
        message: `${targetApproval.title} was rejected. Agent execution cancelled.`,
        type: 'alert',
        isRead: false,
        linkView: 'audit-logs',
      },
      ...prev,
    ]);
  };

  const handleRequestChanges = (id: string, notes: string) => {
    setApprovals((prev) =>
      prev.map((appr) => (appr.id === id ? { ...appr, status: 'changes_requested', notes } : appr))
    );
  };

  const runWorkBuddyPrompt = async (promptText: string) => {
    setIsOrchestrating(true);
    setCurrentView('ai-workspace');

    // Create session template
    const newSessionId = `SESSION-${Date.now()}`;
    const initialSession: WorkBuddySession = {
      id: newSessionId,
      prompt: promptText,
      status: 'decomposing',
      createdAt: new Date().toISOString().replace('T', ' ').substring(0, 19),
      steps: [
        {
          id: 'step-1',
          title: 'Semantic Intent Parsing & Policy Boundary Validation',
          agentId: 'workbuddy-core',
          agentName: 'WorkBuddy Central Orchestrator',
          status: 'running',
          description: 'Analyzing user request, mapping required business domains, and verifying agent execution boundaries.',
          timestamp: 'Step 1/4',
        },
      ],
    };
    setActiveSession(initialSession);

    // Simulated staggered multi-agent delegation
    await new Promise((r) => setTimeout(r, 600));

    // Phase 2: Delegate to HR Agent
    setActiveSession((prev) =>
      prev
        ? {
            ...prev,
            status: 'orchestrating',
            steps: [
              { ...prev.steps[0]!, status: 'completed' },
              {
                id: 'step-2',
                title: 'Delegated: Workforce Attendance & Anomaly Ingestion',
                agentId: 'agent-hr',
                agentName: 'HR Intelligence Agent',
                status: 'running',
                description: 'Scanning employee attendance logs across engineering, finance, and operations. Isolating statistical variances.',
                timestamp: 'Step 2/4',
              },
            ],
          }
        : prev
    );

    await new Promise((r) => setTimeout(r, 700));

    // Phase 3: Delegate to Finance Agent
    setActiveSession((prev) =>
      prev
        ? {
            ...prev,
            steps: [
              prev.steps[0]!,
              {
                ...prev.steps[1]!,
                status: 'completed',
                outputSummary: 'Extracted 8 employee timesheets. Flagged EMP-1002 (Marcus Vance, 86.2% remote attendance variance).',
              },
              {
                id: 'step-3',
                title: 'Delegated: Ledger Reconciliation & Payroll Projections',
                agentId: 'agent-finance',
                agentName: 'Finance & Ledger Agent',
                status: 'running',
                description: 'Computing statutory withholdings, factoring overtime adjustments, and preparing ACH payroll draft.',
                timestamp: 'Step 3/4',
              },
            ],
          }
        : prev
    );

    await new Promise((r) => setTimeout(r, 700));

    // Phase 4: Consolidate & Human Governance Gate
    setActiveSession((prev) =>
      prev
        ? {
            ...prev,
            status: 'awaiting_approval',
            steps: [
              prev.steps[0]!,
              prev.steps[1]!,
              {
                ...prev.steps[2]!,
                status: 'completed',
                outputSummary: 'Calculated Gross Payroll: $412,850.00 | Net: $308,420.00. Overtime ledger entries verified.',
              },
              {
                id: 'step-4',
                title: 'Human Governance Gate Enforced (Policy POL-02)',
                agentId: 'agent-finance',
                agentName: 'Finance & Ledger Agent',
                status: 'requires_human_review',
                description: 'Autonomous payroll execution restricted by enterprise governance policy. Approval ticket APR-1050 generated for executive authorization.',
                outputSummary: 'Approval Ticket APR-1050 generated with cryptographic hash.',
                timestamp: 'Step 4/4',
              },
            ],
            consolidatedReport: {
              title: 'Multi-Agent Operations & Attendance Audit Report',
              summary: 'WorkBuddy successfully coordinated HR Agent and Finance Agent. Engineering pod attendance anomaly identified (Marcus Vance), and November mid-cycle payroll estimated at $412,850.00 (+0.8% variance). Governance policy POL-02 halted auto-disbursement until human sign-off.',
              metrics: [
                { label: 'Workforce Sample', value: '8 Salaried FTEs', change: '100% Data Confidence' },
                { label: 'Attendance Mean', value: '96.6%', change: '1 anomaly flagged' },
                { label: 'Gross Payroll Draft', value: '$412,850.00', change: '+0.8% variance' },
                { label: 'Governance Status', value: 'Pending Approval', change: 'Ticket APR-1050' },
              ],
              recommendations: [
                'Authorize medical leave request LR-3082 to normalize the attendance anomaly.',
                'Sign off on November mid-cycle payroll disbursement (APR-1050) in Approval Center.',
                'Dispatch automated notification to Engineering lead confirming scheduled coverage.',
              ],
              actionRequired: 'Human sign-off required for Payroll Batch (APR-1050).',
              approvalRequestId: 'APR-1050',
            },
          }
        : prev
    );

    setIsOrchestrating(false);
  };

  const triggerJourney = (journeyId: 1 | 2 | 3 | 4) => {
    setCurrentJourney(journeyId);
    if (journeyId === 1) {
      // Journey 1: AI Multi-Agent Orchestration
      void runWorkBuddyPrompt(
        'Prepare monthly employee attendance report, calculate payroll estimates, and identify departments with unusual attendance patterns.'
      );
    } else if (journeyId === 2) {
      // Journey 2: Human Approval
      setCurrentView('approvals');
    } else if (journeyId === 3) {
      // Journey 3: HR Workflow
      setCurrentView('hr');
    } else if (journeyId === 4) {
      // Journey 4: Inventory Workflow
      setCurrentView('inventory');
    }
  };

  const syncIntegration = (id: string) => {
    setIntegrations((prev) =>
      prev.map((int) => (int.id === id ? { ...int, status: 'syncing' } : int))
    );
    setTimeout(() => {
      setIntegrations((prev) =>
        prev.map((int) =>
          int.id === id ? { ...int, status: 'connected', lastSync: 'Just now' } : int
        )
      );
      setNotifications((prev) => [
        {
          id: `notif-${Date.now()}`,
          timestamp: 'Just now',
          title: 'Integration Synced',
          message: `Integration updated successfully with 0 telemetry errors.`,
          type: 'system',
          isRead: false,
        },
        ...prev,
      ]);
    }, 1000);
  };

  const togglePolicy = (id: string) => {
    setPolicies((prev) =>
      prev.map((pol) => (pol.id === id ? { ...pol, isEnforced: !pol.isEnforced } : pol))
    );
  };

  const markAllNotificationsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
  };

  return (
    <DextraContext.Provider
      value={{
        currentView,
        setCurrentView,
        searchQuery,
        setSearchQuery,
        isCommandPaletteOpen,
        setIsCommandPaletteOpen,
        isNotificationOpen,
        setIsNotificationOpen,
        selectedAgent,
        setSelectedAgent,
        selectedEmployee,
        setSelectedEmployee,
        agents,
        approvals,
        tasks,
        employees,
        leaveRequests,
        inventory,
        purchaseOrders,
        budgets,
        transactions,
        payroll,
        policies,
        auditLogs,
        integrations,
        notifications,
        activeSession,
        isOrchestrating,
        currentJourney,
        handleApprove,
        handleReject,
        handleRequestChanges,
        runWorkBuddyPrompt,
        triggerJourney,
        syncIntegration,
        togglePolicy,
        markAllNotificationsRead,
      }}
    >
      {children}
    </DextraContext.Provider>
  );
};

export const useDextra = () => {
  const context = useContext(DextraContext);
  if (!context) {
    throw new Error('useDextra must be used within a DextraProvider');
  }
  return context;
};
