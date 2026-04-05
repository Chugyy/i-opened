'use client';

import { use, useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { ArrowLeft, Mail, Phone, Calendar, Star, Clock } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { StatusBadge } from '@/components/shared/status-badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
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
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

interface LeadDetail {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  status: string;
  score?: number;
  calendarId?: string;
  calendarName?: string;
  createdAt: string;
  answers?: Array<{ questionId: string; questionLabel?: string; value: string }>;
  bookings?: Array<{ id: string; startsAt: string; endsAt: string; status: string }>;
  automationLogs?: Array<{ id: string; automationName: string; channel: string; status: string; scheduledAt: string; errorMessage?: string }>;
}

function InfoRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <Icon className="size-3.5 shrink-0 text-muted-foreground" />
      <span className="text-muted-foreground min-w-20">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

const LEAD_STATUSES = ['nouveau', 'qualifie', 'non_qualifie', 'booke', 'no_show'];
const STATUS_LABELS: Record<string, string> = {
  nouveau: 'Nouveau', qualifie: 'Qualifié', non_qualifie: 'Non qualifié', booke: 'Booké', no_show: 'No-show',
};

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  const { data: lead, isLoading } = useQuery<LeadDetail>({
    queryKey: ['lead', id],
    queryFn: () => api.get(`/api/leads/${id}`),
  });

  useEffect(() => {
    if (lead) setSelectedStatus(lead.status);
  }, [lead]);

  const updateStatus = useMutation({
    mutationFn: (status: string) => api.patch(`/api/leads/${id}/status`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', id] });
      toast.success('Statut mis à jour');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteLead = useMutation({
    mutationFn: () => api.delete(`/api/leads/${id}`),
    onSuccess: () => {
      toast.success('Lead supprimé');
      router.push('/leads');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-36" />
          <Skeleton className="h-36" />
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="space-y-4">
        <Link href="/leads"><Button variant="ghost" size="sm"><ArrowLeft className="size-4" /> Retour</Button></Link>
        <p className="text-muted-foreground">Lead introuvable.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/leads">
            <Button variant="ghost" size="icon-sm"><ArrowLeft className="size-4" /></Button>
          </Link>
          <h1 className="text-xl font-semibold">{lead.firstName} {lead.lastName}</h1>
          <Select value={selectedStatus} onValueChange={(v) => { setSelectedStatus(v); updateStatus.mutate(v); }}>
            <SelectTrigger className="h-8 w-36 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LEAD_STATUSES.map((s) => (
                <SelectItem key={s} value={s}>{STATUS_LABELS[s] ?? s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" size="sm">Supprimer</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Supprimer ce lead ?</AlertDialogTitle>
              <AlertDialogDescription>
                {lead.firstName} {lead.lastName} sera définitivement supprimé. Cette action est irréversible.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Annuler</AlertDialogCancel>
              <AlertDialogAction
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={() => deleteLead.mutate()}
                disabled={deleteLead.isPending}
              >
                Supprimer
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Info + Answers */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-sm">Informations</CardTitle></CardHeader>
          <CardContent className="space-y-2.5">
            <InfoRow icon={Mail} label="Email" value={lead.email} />
            <InfoRow icon={Phone} label="Téléphone" value={lead.phone ?? '—'} />
            <InfoRow icon={Calendar} label="Calendrier" value={lead.calendarName ?? '—'} />
            <InfoRow icon={Star} label="Score" value={lead.score != null ? `${Math.round(lead.score)}%` : '—'} />
            <InfoRow icon={Clock} label="Créé le" value={format(new Date(lead.createdAt), 'dd MMM yyyy HH:mm', { locale: fr })} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Réponses qualification</CardTitle></CardHeader>
          <CardContent>
            {!lead.answers?.length ? (
              <p className="text-sm text-muted-foreground">Aucune réponse</p>
            ) : (
              <div className="space-y-2">
                {lead.answers.map((a, i) => (
                  <div key={i}>
                    <p className="text-xs text-muted-foreground">{a.questionLabel ?? a.questionId}</p>
                    <p className="text-sm font-medium">{a.value}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bookings + Automation logs side by side on larger screens */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-sm">Rendez-vous</CardTitle></CardHeader>
          <CardContent>
            {!lead.bookings?.length ? (
              <p className="text-sm text-muted-foreground">Aucun RDV</p>
            ) : (
              <div className="space-y-2">
                {lead.bookings.map((b) => (
                  <div key={b.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                    <span className="text-sm">
                      {format(new Date(b.startsAt), 'dd MMM yyyy · HH:mm', { locale: fr })}
                    </span>
                    <StatusBadge status={b.status} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Automations</CardTitle></CardHeader>
          <CardContent>
            {!lead.automationLogs?.length ? (
              <p className="text-sm text-muted-foreground">Aucune automation envoyée</p>
            ) : (
              <div className="space-y-2">
                {lead.automationLogs.map((log) => (
                  <div key={log.id} className="rounded-md border px-3 py-2 space-y-0.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{log.automationName}</span>
                        <span className="text-xs text-muted-foreground capitalize">{log.channel}</span>
                      </div>
                      <StatusBadge status={log.status} />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {format(new Date(log.scheduledAt), 'dd MMM yyyy HH:mm', { locale: fr })}
                    </p>
                    {log.errorMessage && (
                      <p className="text-xs text-destructive">{log.errorMessage}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
