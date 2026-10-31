import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Icons } from '@/components/icons';
import { QuFinLogo } from '@/components/layout/logo';
import { ThemeModeToggle } from '@/components/themes/theme-mode-toggle';
import { authEnabled } from '@/features/auth/api/service';
import { getSnapshots } from '@/features/market/api/service';
import {
  ChangeText,
  ConvictionMeter,
  DirectionBadge,
  ProbabilityLabel
} from '@/features/market/components/signal-badge';
import { formatPrice } from '@/features/market/lib/format';
import { AS_OF } from '@/features/market/lib/mock-data';
import { cn } from '@/lib/utils';

const FEATURES = [
  {
    icon: 'world',
    title: 'Macro scorecards',
    body: 'Growth, inflation, labour, policy and sentiment scored for major economies from official releases.'
  },
  {
    icon: 'brain',
    title: 'Explainable AI signals',
    body: 'Calibrated probabilities with the drivers behind them: rates, positioning, PMIs, momentum and news.'
  },
  {
    icon: 'backtest',
    title: 'Backtest every decision',
    body: 'Replay your own entry, stop and target on years of history before you risk real money.'
  },
  {
    icon: 'journal',
    title: 'Decision journal',
    body: 'Log each trade with the signal and backtest you saw, then review what worked.'
  },
  {
    icon: 'chartLine',
    title: 'FX, metals, energy, crypto',
    body: 'One workspace across the markets that move together, with CFTC positioning and EIA data built in.'
  },
  {
    icon: 'shield',
    title: 'Built for institutions',
    body: 'SSO, audit trails and point-in-time data, so research is reproducible and compliant.'
  }
] as const;

// Placeholder pricing: final tiers and prices to be confirmed before launch.
const PLANS = [
  {
    name: 'Starter',
    price: '$0',
    cadence: 'forever',
    description: 'Learn the platform with delayed data.',
    features: ['Macro scorecards', 'Daily signals on 5 assets', 'Backtest lab (1 year)', 'Decision journal'],
    cta: 'Start free',
    featured: false
  },
  {
    name: 'Pro',
    price: '$39',
    cadence: 'per month',
    description: 'For active traders who want the full toolkit.',
    features: ['All assets and signals', 'Signal drivers and alerts', 'Backtest lab (full history)', 'Decision backtests', 'Priority data refresh'],
    cta: 'Start 14-day trial',
    featured: true
  },
  {
    name: 'Institutional',
    price: 'Custom',
    cadence: 'annual',
    description: 'Teams, APIs and compliance controls.',
    features: ['Everything in Pro', 'API and data exports', 'SSO and role-based access', 'Audit log and SLAs', 'Dedicated support'],
    cta: 'Talk to sales',
    featured: false
  }
];

export default async function LandingPage() {
  const snapshots = await getSnapshots();
  const preview = snapshots
    .toSorted((a, b) => Math.abs(b.signal.probUp - 0.5) - Math.abs(a.signal.probUp - 0.5))
    .slice(0, 5);

  return (
    <div className='bg-background min-h-screen'>
      <header className='bg-background/80 sticky top-0 z-30 border-b backdrop-blur-md'>
        <div className='mx-auto flex h-16 max-w-6xl items-center justify-between px-4'>
          <Link href='/' aria-label='QuFin home'>
            <QuFinLogo />
          </Link>
          <nav className='text-muted-foreground hidden items-center gap-6 text-sm md:flex'>
            <a href='#features' className='hover:text-foreground'>Features</a>
            <a href='#how' className='hover:text-foreground'>How it works</a>
            <a href='#pricing' className='hover:text-foreground'>Pricing</a>
          </nav>
          <div className='flex items-center gap-2'>
            <ThemeModeToggle />
            {authEnabled && (
              <Button variant='ghost' nativeButton={false} render={<Link href='/auth/sign-in' aria-label='Sign in' />}>
                Sign in
              </Button>
            )}
            <Button nativeButton={false} render={<Link href='/dashboard/overview' aria-label='Open dashboard' />}>
              Open dashboard
            </Button>
          </div>
        </div>
      </header>

      <main>
        <section className='mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 md:py-24 lg:grid-cols-2'>
          <div className='flex flex-col gap-6'>
            <Badge variant='outline' className='h-6 px-3'>
              <Icons.bolt />
              AI trading intelligence
            </Badge>
            <h1 className='text-4xl font-bold tracking-tight text-balance md:text-5xl'>
              Trade on evidence, <span className='text-primary'>not noise.</span>
            </h1>
            <p className='text-muted-foreground max-w-xl text-lg text-pretty'>
              QuFin turns official macro data, positioning and market structure into explainable
              signals, then lets you backtest your own decision before you place it.
            </p>
            <div className='flex flex-wrap gap-3'>
              <Button size='lg' className='h-11 px-5' nativeButton={false} render={<Link href='/dashboard/overview' aria-label='Explore the dashboard' />}>
                Explore the dashboard
                <Icons.arrowRight />
              </Button>
              <Button size='lg' variant='outline' className='h-11 px-5' nativeButton={false} render={<a href='#pricing' aria-label='See pricing' />}>
                See pricing
              </Button>
            </div>
            <p className='text-muted-foreground text-xs'>
              Research and decision support only. Not investment advice.
            </p>
          </div>

          <Card className='shadow-lg'>
            <CardHeader>
              <CardTitle>Today&apos;s strongest signals</CardTitle>
              <CardDescription>5-day outlook · sample data</CardDescription>
            </CardHeader>
            <CardContent className='flex flex-col divide-y'>
              {preview.map((s) => (
                <Link
                  key={s.asset.symbol}
                  href={`/dashboard/markets/${s.asset.symbol}`}
                  className='hover:bg-muted/50 -mx-2 grid grid-cols-[1fr_auto_auto] items-center gap-4 rounded-md px-2 py-2.5'
                >
                  <div>
                    <div className='font-medium'>{s.asset.symbol}</div>
                    <div className='text-muted-foreground font-mono text-xs tabular-nums'>
                      {formatPrice(s.lastPrice, s.asset.precision)} <ChangeText value={s.changePct} />
                    </div>
                  </div>
                  <div className='flex flex-col items-end gap-1'>
                    <DirectionBadge signal={s.signal} />
                    <ConvictionMeter conviction={s.signal.conviction} />
                  </div>
                  <div className='w-12 text-right text-lg'>
                    <ProbabilityLabel probUp={s.signal.probUp} />
                  </div>
                </Link>
              ))}
            </CardContent>
          </Card>
        </section>

        <section id='features' className='bg-muted/40 border-y'>
          <div className='mx-auto max-w-6xl px-4 py-16 md:py-20'>
            <h2 className='text-3xl font-bold tracking-tight'>Everything between the data and the decision</h2>
            <p className='text-muted-foreground mt-2 max-w-2xl'>
              Most platforms stop at charts or at black-box calls. QuFin shows the evidence, the
              odds, and how your plan would have done.
            </p>
            <div className='mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
              {FEATURES.map((f) => {
                const Icon = Icons[f.icon];
                return (
                  <Card key={f.title}>
                    <CardHeader>
                      <span className='bg-accent text-accent-foreground mb-2 inline-flex size-9 items-center justify-center rounded-lg'>
                        <Icon className='size-5' />
                      </span>
                      <CardTitle>{f.title}</CardTitle>
                      <CardDescription>{f.body}</CardDescription>
                    </CardHeader>
                  </Card>
                );
              })}
            </div>
          </div>
        </section>

        <section id='how' className='mx-auto max-w-6xl px-4 py-16 md:py-20'>
          <h2 className='text-3xl font-bold tracking-tight'>How it works</h2>
          <ol className='mt-10 grid gap-6 md:grid-cols-3'>
            {[
              ['Read the market', 'Start from the macro scorecard and today’s signals, ranked by conviction.'],
              ['Plan and backtest', 'Set direction, stop, target and size. See the win rate and R multiple your plan would have earned.'],
              ['Decide and review', 'Log the decision to your journal and track it against the latest close.']
            ].map(([title, body], i) => (
              <li key={title} className='flex flex-col gap-2'>
                <span className='text-primary font-mono text-sm'>0{i + 1}</span>
                <h3 className='text-lg font-semibold'>{title}</h3>
                <p className='text-muted-foreground'>{body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id='pricing' className='bg-muted/40 border-y'>
          <div className='mx-auto max-w-6xl px-4 py-16 md:py-20'>
            <h2 className='text-3xl font-bold tracking-tight'>Pricing</h2>
            <p className='text-muted-foreground mt-2'>Start free. Upgrade when it pays for itself.</p>
            <div className='mt-10 grid gap-4 lg:grid-cols-3'>
              {PLANS.map((plan) => (
                <Card key={plan.name} className={cn(plan.featured && 'ring-primary ring-2')}>
                  <CardHeader>
                    <div className='flex items-center justify-between'>
                      <CardTitle className='text-lg'>{plan.name}</CardTitle>
                      {plan.featured && <Badge>Most popular</Badge>}
                    </div>
                    <CardDescription>{plan.description}</CardDescription>
                  </CardHeader>
                  <CardContent className='flex flex-1 flex-col gap-5'>
                    <div>
                      <span className='text-4xl font-bold tracking-tight'>{plan.price}</span>{' '}
                      <span className='text-muted-foreground text-sm'>{plan.cadence}</span>
                    </div>
                    <ul className='flex flex-col gap-2 text-sm'>
                      {plan.features.map((f) => (
                        <li key={f} className='flex items-center gap-2'>
                          <Icons.check className='text-bull size-4' />
                          {f}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                  <CardFooter className='border-t pt-4'>
                    <Button
                      className='w-full'
                      variant={plan.featured ? 'default' : 'outline'}
                      nativeButton={false}
                      render={<Link href='/dashboard/overview' aria-label={plan.cta} />}
                    >
                      {plan.cta}
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className='mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10 text-sm md:flex-row md:items-start md:justify-between'>
        <div className='flex flex-col gap-2'>
          <QuFinLogo />
          <p className='text-muted-foreground'>© {AS_OF.slice(0, 4)} QuFin. Dubai, UAE.</p>
        </div>
        <p className='text-muted-foreground max-w-xl text-xs'>
          QuFin provides research and decision-support tools. Nothing on this site is investment
          advice or a recommendation to buy or sell any instrument. Trading involves risk, and past
          or backtested performance does not guarantee future results.
        </p>
      </footer>
    </div>
  );
}
