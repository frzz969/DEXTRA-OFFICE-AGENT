/**
 * Employee and leave-request contracts.
 */

export interface Employee {
  id: string;
  fullName: string;
  role: string;
  department: string;
  email: string;
  phone: string;
  status: 'active' | 'on_leave' | 'remote';
  attendanceRate: number;
  performanceScore: number;
  salary: number;
  joinDate: string;
  location: string;
}

export interface LeaveRequest {
  id: string;
  employeeId: string;
  employeeName: string;
  department: string;
  type: 'Annual Leave' | 'Sick Leave' | 'Parental' | 'Unpaid';
  startDate: string;
  endDate: string;
  days: number;
  status: 'pending' | 'approved' | 'rejected';
  reason: string;
  submittedAt: string;
}
