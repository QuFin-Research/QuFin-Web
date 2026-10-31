import PageContainer from '@/components/layout/page-container';
import { BacktestLab } from '@/features/backtest/components/backtest-lab';

export const metadata = {
  title: 'Backtest lab'
};

export default function BacktestPage() {
  return (
    <PageContainer
      pageTitle='Backtest lab'
      pageDescription='Test how QuFin signals would have traded an asset, with your own costs and rules.'
    >
      <BacktestLab />
    </PageContainer>
  );
}
