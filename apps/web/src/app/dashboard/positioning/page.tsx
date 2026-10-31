import PageContainer from '@/components/layout/page-container';
import { PositioningView } from '@/features/positioning/components/positioning-view';

export const metadata = {
  title: 'Positioning'
};

export default function PositioningPage() {
  return (
    <PageContainer
      pageTitle='Positioning'
      pageDescription='How large speculators are positioned in each market, from the weekly CFTC reports.'
    >
      <PositioningView />
    </PageContainer>
  );
}
