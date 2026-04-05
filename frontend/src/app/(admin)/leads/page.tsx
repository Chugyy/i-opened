'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { PageHeader } from '@/components/shared/page-header';
import { StatusBadge } from '@/components/shared/status-badge';
import { EmptyState } from '@/components/shared/empty-state';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface Lead {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  score?: number;
  status: string;
  calendarId?: string;
  calendarName?: string;
  createdAt: string;
}

interface LeadsResponse {
  data: Lead[];
  pagination: { limit: number; offset: number; total: number; hasMore: boolean };
}

const STATUSES = ['tous', 'nouveau', 'qualifie', 'non_qualifie', 'booke', 'no_show'];
const LEAD_STATUSES = ['nouveau', 'qualifie', 'non_qualifie', 'booke', 'no_show'];
const STATUS_LABELS: Record<string, string> = {
  tous: 'Tous les statuts',
  nouveau: 'Nouveau',
  qualifie: 'Qualifié',
  non_qualifie: 'Non qualifié',
  booke: 'Booké',
  no_show: 'No-show',
};

export default function LeadsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('tous');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<Lead | null>(null);
  const limit = 50;

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/api/leads/${id}/status`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Statut mis à jour');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteLead = useMutation({
    mutationFn: (id: string) => api.delete(`/api/leads/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      setDeleteTarget(null);
      toast.success('Lead supprimé');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const queryParams = new URLSearchParams({
    limit: String(limit),
    offset: String(page * limit),
    ...(status !== 'tous' ? { status } : {}),
    ...(search ? { search } : {}),
  });

  const { data, isLoading } = useQuery<LeadsResponse>({
    queryKey: ['leads', status, search, page],
    queryFn: () => api.get(`/api/leads?${queryParams}`),
  });

  const leads = data?.data ?? [];
  const total = data?.pagination?.total ?? leads.length;

  return (
    <div className="space-y-6">
      <PageHeader title="Leads" description={`${total} leads au total`} />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Select value={status} onValueChange={(v) => { setStatus(v); setPage(0); }}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {STATUS_LABELS[s] ?? s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Rechercher..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          className="w-60"
        />
        {(status !== 'tous' || search) && (
          <Button variant="ghost" size="sm" onClick={() => { setStatus('tous'); setSearch(''); setPage(0); }}>
            Réinitialiser
          </Button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : !leads.length ? (
        <EmptyState
          icon={Users}
          title={status !== 'tous' || search ? 'Aucun lead ne correspond aux filtres' : 'Aucun lead pour le moment'}
          description="Les leads apparaîtront ici après les premières soumissions de formulaires"
        />
      ) : (
        <>
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Téléphone</TableHead>
                  <TableHead>Calendrier</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.map((lead) => (
                  <TableRow
                    key={lead.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => router.push(`/leads/${lead.id}`)}
                  >
                    <TableCell className="font-medium">
                      {lead.firstName} {lead.lastName}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{lead.email}</TableCell>
                    <TableCell className="text-muted-foreground">{lead.phone ?? '—'}</TableCell>
                    <TableCell className="text-muted-foreground">{lead.calendarName ?? '—'}</TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Select
                        value={lead.status}
                        onValueChange={(v) => updateStatus.mutate({ id: lead.id, status: v })}
                      >
                        <SelectTrigger className="h-7 w-32 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {LEAD_STATUSES.map((s) => (
                            <SelectItem key={s} value={s}>{STATUS_LABELS[s] ?? s}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {lead.score != null ? `${Math.round(lead.score)}%` : '—'}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {format(new Date(lead.createdAt), 'dd MMM yyyy', { locale: fr })}
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-muted-foreground hover:text-destructive"
                        onClick={() => setDeleteTarget(lead)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
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

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce lead ?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTarget && `${deleteTarget.firstName} ${deleteTarget.lastName} sera définitivement supprimé. Cette action est irréversible.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteTarget && deleteLead.mutate(deleteTarget.id)}
              disabled={deleteLead.isPending}
            >
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
