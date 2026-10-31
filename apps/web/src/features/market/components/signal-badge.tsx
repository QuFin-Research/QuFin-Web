import { Badge } from '@/components/ui/badge';
import { Icons } from '@/components/icons';
import { cn } from '@/lib/utils';
import type { Conviction, Signal } from '../api/types';

export function DirectionBadge({ signal }: { signal: Signal }) {
  const long = signal.direction === 'long';
  if (signal.conviction === 'low') {
    return (
      <Badge variant='outline' className='text-muted-foreground'>
        Neutral
      </Badge>
    );
  }
  return (
    <Badge
      variant='outline'
      className={cn(
        'border-transparent',
        long ? 'bg-bull/12 text-bull' : 'bg-bear/12 text-bear'
      )}
    >
      {long ? <Icons.trendingUp /> : <Icons.trendingDown />}
      {long ? 'Bullish' : 'Bearish'}
    </Badge>
  );
}

const CONVICTION_BARS: Record<Conviction, number> = { low: 1, medium: 2, high: 3 };

export function ConvictionMeter({ conviction }: { conviction: Conviction }) {
  const filled = CONVICTION_BARS[conviction];
  return (
    <span className='inline-flex items-center gap-1.5' title={`${conviction} conviction`}>
      <span className='flex items-end gap-0.5' aria-hidden>
        {[1, 2, 3].map((bar) => (
          <span
            key={bar}
            className={cn(
              'w-1 rounded-sm',
              bar === 1 ? 'h-1.5' : bar === 2 ? 'h-2.5' : 'h-3.5',
              bar <= filled ? 'bg-primary' : 'bg-muted-foreground/25'
            )}
          />
        ))}
      </span>
      <span className='text-muted-foreground text-xs capitalize'>{conviction}</span>
    </span>
  );
}

/** Probability of an up move, shown as the side the model leans to */
export function ProbabilityLabel({ probUp }: { probUp: number }) {
  const lean = probUp >= 0.5 ? probUp : 1 - probUp;
  return <span className='font-mono tabular-nums'>{(lean * 100).toFixed(0)}%</span>;
}

export function ChangeText({ value, className }: { value: number; className?: string }) {
  return (
    <span
      className={cn(
        'font-mono tabular-nums',
        value > 0 ? 'text-bull' : value < 0 ? 'text-bear' : 'text-muted-foreground',
        className
      )}
    >
      {value > 0 ? '+' : ''}
      {value.toFixed(2)}%
    </span>
  );
}
