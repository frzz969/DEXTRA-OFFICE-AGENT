import type { Metadata } from 'next';
import { GovernancePolicies } from '@/features/governance/governance-policies';

export const metadata: Metadata = {
  title: 'DEXTRA · Governance',
};

export default function GovernancePage() {
  return <GovernancePolicies />;
}
