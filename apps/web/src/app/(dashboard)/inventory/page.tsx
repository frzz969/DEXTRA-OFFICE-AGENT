import type { Metadata } from 'next';
import { InventoryProcurement } from '@/features/inventory/inventory-procurement';

export const metadata: Metadata = {
  title: 'DEXTRA · Inventory',
};

export default function InventoryPage() {
  return <InventoryProcurement />;
}
