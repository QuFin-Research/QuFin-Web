import { cn } from '@/lib/utils';

/** QuFin mark: a rising signal line inside a rounded square, plus the wordmark */
export function QuFinLogo({ className, showWordmark = true }: { className?: string; showWordmark?: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <svg viewBox='0 0 32 32' className='size-7 shrink-0' aria-hidden>
        <rect width='32' height='32' rx='8' fill='oklch(0.32 0.06 230)' />
        <path
          d='M6 21.5 11.5 16l4 3.5L25 10'
          fill='none'
          stroke='oklch(0.72 0.14 235)'
          strokeWidth='2.6'
          strokeLinecap='round'
          strokeLinejoin='round'
        />
        <circle cx='25' cy='10' r='2.4' fill='oklch(0.74 0.15 163)' />
      </svg>
      {showWordmark && (
        <span className='text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden'>
          Qu<span className='text-primary'>Fin</span>
        </span>
      )}
    </span>
  );
}
