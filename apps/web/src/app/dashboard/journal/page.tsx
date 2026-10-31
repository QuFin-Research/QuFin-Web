import PageContainer from '@/components/layout/page-container';
import { JournalView } from '@/features/journal/components/journal-view';

export const metadata = {
  title: 'Decision journal'
};

export default function JournalPage() {
  return (
    <PageContainer
      pageTitle='Decision journal'
      pageDescription='Every decision you log, with the backtest you saw when you made it.'
    >
      <JournalView />
    </PageContainer>
  );
}
