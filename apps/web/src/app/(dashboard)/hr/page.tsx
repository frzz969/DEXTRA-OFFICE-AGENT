import type { Metadata } from 'next';
import { HumanResources } from '@/features/human-resources/human-resources';

export const metadata: Metadata = {
  title: 'DEXTRA · Human Resources',
};

export default function HumanResourcesPage() {
  return <HumanResources />;
}
