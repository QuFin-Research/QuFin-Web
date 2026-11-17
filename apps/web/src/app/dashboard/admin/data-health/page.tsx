import PageContainer from '@/components/layout/page-container';
import { CoveragePanel } from '@/features/admin/components/coverage-panel';
import { AdminHealth } from '@/features/macro/components/admin-health';

export const metadata = {
  title: 'Data health'
};

export default function DataHealthPage() {
  return (
    <PageContainer
      pageTitle='Data health'
      pageDescription='Coverage by country and indicator, the data refresh, and the release check per source.'
    >
      <div className='space-y-4'>
        <CoveragePanel />
        <AdminHealth />
      </div>
    </PageContainer>
  );
}
