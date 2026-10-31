import { SampleDataBadge } from '@/components/sample-data';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { AssetDetail } from '../api/types';
import { ConvictionMeter, DirectionBadge, ProbabilityLabel } from './signal-badge';

/** Diverging bar list (Tremor BarList pattern) showing what pushes the score up or down */
function DriverBars({ drivers }: { drivers: AssetDetail['drivers'] }) {
  const max = Math.max(...drivers.map((d) => Math.abs(d.contribution)), 0.01);
  return (
    <ul className='flex flex-col gap-2.5'>
      {drivers.map((d) => {
        const width = `${(Math.abs(d.contribution) / max) * 50}%`;
        const positive = d.contribution >= 0;
        return (
          <li
            key={d.name}
            className='grid grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_3rem] items-center gap-3'
          >
            <div className='min-w-0'>
              <div className='truncate text-sm'>{d.name}</div>
              <div className='text-muted-foreground text-xs'>{d.category}</div>
            </div>
            <div className='bg-muted relative h-2 rounded-full'>
              <span className='bg-border absolute top-[-3px] left-1/2 h-[14px] w-px' aria-hidden />
              <span
                className={cn(
                  'absolute top-0 h-2 rounded-full',
                  positive ? 'bg-bull left-1/2' : 'bg-bear right-1/2'
                )}
                style={{ width }}
              />
            </div>
            <span
              className={cn(
                'text-right font-mono text-xs tabular-nums',
                positive ? 'text-bull' : 'text-bear'
              )}
            >
              {positive ? '+' : ''}
              {d.contribution.toFixed(2)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function SignalPanel({ detail }: { detail: AssetDetail }) {
  const { signal, regime, hitRate, drivers } = detail;
  return (
    <Card>
      <CardHeader>
        <CardTitle className='flex items-center gap-2'>
          QuFin signal
          <SampleDataBadge />
        </CardTitle>
        <CardDescription>
          {signal.horizonDays}-day outlook from the close of {signal.time}
        </CardDescription>
      </CardHeader>
      <CardContent className='flex flex-col gap-5'>
        <div className='grid grid-cols-2 gap-x-4 gap-y-3 text-sm'>
          <div>
            <div className='text-muted-foreground text-xs'>Direction</div>
            <div className='mt-1'>
              <DirectionBadge signal={signal} />
            </div>
          </div>
          <div>
            <div className='text-muted-foreground text-xs'>Probability</div>
            <div className='mt-1 text-lg leading-none'>
              <ProbabilityLabel probUp={signal.probUp} />
            </div>
          </div>
          <div>
            <div className='text-muted-foreground text-xs'>Conviction</div>
            <div className='mt-1'>
              <ConvictionMeter conviction={signal.conviction} />
            </div>
          </div>
          <div>
            <div className='text-muted-foreground text-xs'>Regime</div>
            <div className='mt-1'>{regime}</div>
          </div>
        </div>
        <div>
          <div className='mb-3 flex items-baseline justify-between'>
            <h3 className='text-sm font-medium'>Why the model leans this way</h3>
            <span className='text-muted-foreground text-xs'>score contribution</span>
          </div>
          <DriverBars drivers={drivers} />
        </div>
        <p className='text-muted-foreground border-t pt-3 text-xs'>
          Past signals on this asset were right {(hitRate * 100).toFixed(1)}% of the time over{' '}
          {signal.horizonDays} days. A probability, not a promise.
        </p>
      </CardContent>
    </Card>
  );
}
