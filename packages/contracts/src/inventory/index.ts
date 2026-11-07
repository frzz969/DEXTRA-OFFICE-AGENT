/**
 * Inventory contracts.
 */

export interface InventoryItem {
  sku: string;
  name: string;
  category: string;
  stockLevel: number;
  minThreshold: number;
  reorderQuantity: number;
  unitCost: number;
  supplier: string;
  status: 'in_stock' | 'low_stock' | 'critical' | 'reordered';
  location: string;
}

export interface PurchaseOrderLine {
  sku: string;
  name: string;
  qty: number;
  unitCost: number;
}

export interface PurchaseOrder {
  id: string;
  poNumber: string;
  supplier: string;
  date: string;
  items: PurchaseOrderLine[];
  totalAmount: number;
  status: 'draft' | 'pending_approval' | 'approved' | 'received' | 'rejected';
  generatedBy: string;
  approvalRequestId?: string;
}
