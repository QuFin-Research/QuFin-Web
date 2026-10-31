import PageContainer from '@/components/layout/page-container';
import { MacroView } from '@/features/macro/components/macro-view';

export const metadata = {
  title: 'Macro data'
};

export default function MacroPage() {
  return (
    <PageContainer
      pageTitle='Macro data'
      pageDescription='Official releases with their full revision history, viewable as of any date.'
    >
      <MacroView />
    </PageContainer>
  );
}
