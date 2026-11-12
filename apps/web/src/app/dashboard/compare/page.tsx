import PageContainer from '@/components/layout/page-container';
import { CompareView } from '@/features/macro/components/compare-view';

export const metadata = {
  title: 'Compare countries'
};

export default function ComparePage() {
  return (
    <PageContainer
      pageTitle='Compare countries'
      pageDescription='One indicator across countries on one basis: prices as year-on-year change, unemployment as a share of the labour force.'
    >
      <CompareView />
    </PageContainer>
  );
}
