import PageContainer from '@/components/layout/page-container';
import { AdminHealth } from '@/features/macro/components/admin-health';

export const metadata = {
  title: 'Data health'
};

export default function DataHealthPage() {
  return (
    <PageContainer
      pageTitle='Data health'
      pageDescription='Release check per source, with seasonal adjustment coverage.'
    >
      <AdminHealth />
    </PageContainer>
  );
}
