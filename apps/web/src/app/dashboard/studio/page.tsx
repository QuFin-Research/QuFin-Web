import PageContainer from '@/components/layout/page-container';
import { StudioView } from '@/features/macro/components/studio-view';

export const metadata = {
  title: 'Comparison studio'
};

export default function StudioPage() {
  return (
    <PageContainer
      pageTitle='Comparison studio'
      pageDescription='One indicator across up to 10 countries, or several indicators for one country, on one frequency, as actual values or percentage of change.'
    >
      <StudioView />
    </PageContainer>
  );
}
