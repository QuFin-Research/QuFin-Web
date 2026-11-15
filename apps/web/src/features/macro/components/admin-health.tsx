'use client';

import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { FRESHNESS_LABEL } from '@/lib/data-quality';
import { macroQueries } from '../api/queries';
import { macroAvailable } from '../api/service';
import { healthBySource, percent } from '../lib/admin-health';

export function AdminHealth() {
  const { data, error } = useQuery({ ...macroQueries.list(), enabled: macroAvailable });

  if (!macroAvailable) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>No API connected</EmptyTitle>
          <EmptyDescription>
            The data health view reads the release check from the QuFin API. Set NEXT_PUBLIC_API_URL
            to connect it.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (error) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>Could not load the release check</EmptyTitle>
          <EmptyDescription>{error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (!data) return <Skeleton className='h-96 w-full rounded-xl' />;

  const sources = healthBySource(data);
  const notOk = data.filter((s) => s.freshness.status !== 'ok');
  const total = data.length;
  return (
    <div className='space-y-4'>
      <Card>
        <CardHeader>
          <CardTitle className='flex flex-wrap items-center gap-2'>
            Release check
            <Badge variant={notOk.length === 0 ? 'secondary' : 'destructive'}>
              {notOk.length === 0 ? 'OK' : 'OVERDUE'}
            </Badge>
          </CardTitle>
          <CardDescription>
            {total - notOk.length} of {total} series are on schedule. This is the same check the API
            runs as <code>check-data</code>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Source</TableHead>
                <TableHead className='text-right'>Series</TableHead>
                <TableHead className='text-right'>OK</TableHead>
                <TableHead className='text-right'>Not OK</TableHead>
                <TableHead className='text-right'>SA</TableHead>
                <TableHead className='text-right'>NSA</TableHead>
                <TableHead className='text-right'>Other</TableHead>
                <TableHead className='text-right'>SA share</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sources.map((s) => (
                <TableRow key={s.source}>
                  <TableCell className='font-medium uppercase'>{s.source}</TableCell>
                  <TableCell className='text-right tabular-nums'>{s.total}</TableCell>
                  <TableCell className='text-right tabular-nums'>{s.ok}</TableCell>
                  <TableCell className='text-right tabular-nums'>
                    {s.notOk > 0 ? <Badge variant='destructive'>{s.notOk}</Badge> : 0}
                  </TableCell>
                  <TableCell className='text-right tabular-nums'>{s.sa}</TableCell>
                  <TableCell className='text-right tabular-nums'>{s.nsa}</TableCell>
                  <TableCell className='text-right tabular-nums'>{s.other}</TableCell>
                  <TableCell className='text-right tabular-nums'>
                    {percent(s.sa, s.total)}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {notOk.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className='text-base'>Series that need attention ({notOk.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Series</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {notOk.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell>
                      <div className='font-medium'>{s.name}</div>
                      <div className='text-muted-foreground font-mono text-xs'>{s.id}</div>
                    </TableCell>
                    <TableCell className='uppercase'>{s.source}</TableCell>
                    <TableCell>
                      <Badge variant='destructive'>{FRESHNESS_LABEL[s.freshness.status]}</Badge>
                    </TableCell>
                    <TableCell className='text-muted-foreground'>{s.freshness.reason}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
