'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import Link from 'next/link';
import { api } from '@/lib/api';
import { PageHeader } from '@/components/shared/page-header';
import { StatusBadge } from '@/components/shared/status-badge';
import { EmptyState } from '@/components/shared/empty-state';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

interface Log {
  id: number;
  automation_name: string;
  lead_name?: string;
  channel: string;
  status: string;
  scheduled_at: string;
  error_message?: string;
}

export default function AutomationLogsPage() {
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(0);
  const limit = 20;

  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(page * limit),
    ...(status !== 'all' ? { status } : {}),
  });

  const { data, isLoading } = useQuery<{ data: Log[]; total: number } | Log[]>({
    queryKey: ['automation-logs', status, page],
    queryFn: () => api.get(`/api/automations/logs?${params}`),
  });

  const logs: Log[] = Array.isArray(data) ? data : (data?.data ?? []);
  const total = Array.isArray(data) ? logs.length : (data?.total ?? logs.length);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Logs d'exécution"
        actions={
          <Link href="/automations">
            <Button variant="outline" size="sm">Automations</Button>
          </Link>
        }
      />

      <div className="flex items-center gap-3">
        <Select value={status} onValueChange={(v) => { setStatus(v); setPage(0); }}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les statuts</SelectItem>
            <SelectItem value="pending">En attente</SelectItem>
            <SelectItem value="sent">Envoyés</SelectItem>
            <SelectItem value="failed">Échoués</SelectItem>
            <SelectItem value="cancelled">Annulés</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      ) : !logs.length ? (
        <EmptyState title="Aucun log" description="Les automations n'ont pas encore été exécutées" />
      ) : (
        <>
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Automation</TableHead>
                  <TableHead>Lead</TableHead>
                  <TableHead>Canal</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-medium">{log.automation_name}</TableCell>
                    <TableCell className="text-muted-foreground">{log.lead_name ?? '—'}</TableCell>
                    <TableCell className="capitalize">{log.channel}</TableCell>
                    <TableCell>
                      <StatusBadge status={log.status} />
                      {log.error_message && (
                        <p className="mt-0.5 text-xs text-destructive">{log.error_message}</p>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {format(new Date(log.scheduled_at), 'dd MMM yyyy HH:mm', { locale: fr })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {total > limit && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {page * limit + 1}–{Math.min((page + 1) * limit, total)} sur {total}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                  Précédent
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={(page + 1) * limit >= total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Suivant
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
