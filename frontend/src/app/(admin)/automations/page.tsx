'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Zap, Plus } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { PageHeader } from '@/components/shared/page-header';
import { EmptyState } from '@/components/shared/empty-state';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';

interface Automation {
  id: string;
  name: string;
  trigger: string;
  isActive: boolean;
  calendarName?: string;
  stepsCount?: number;
}

const TRIGGER_LABELS: Record<string, string> = {
  avant_rdv: 'Avant le RDV',
  apres_rdv: 'Après le RDV',
  qualifie_sans_booking: 'Qualifié sans booking',
  coordonnees_sans_booking: 'Coordonnées sans booking',
};

export default function AutomationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<{ data: Automation[] } | Automation[]>({
    queryKey: ['automations'],
    queryFn: () => api.get('/api/automations'),
  });

  const automations: Automation[] = Array.isArray(data) ? data : (data?.data ?? []);

  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      api.patch(`/api/automations/${id}`, { is_active: !isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['automations'] }),
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Automations"
        actions={
          <div className="flex gap-2">
            <Link href="/automations/logs">
              <Button variant="outline" size="sm">Logs</Button>
            </Link>
            <Link href="/automations/new">
              <Button size="sm">
                <Plus className="size-4" />
                Nouvelle automation
              </Button>
            </Link>
          </div>
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : !automations.length ? (
        <EmptyState
          icon={Zap}
          title="Aucune automation"
          description="Créez votre première séquence de relance"
          action={{ label: 'Nouvelle automation', onClick: () => router.push('/automations/new') }}
        />
      ) : (
        <div className="space-y-3">
          {automations.map((auto) => (
            <Card
              key={auto.id}
              className="cursor-pointer hover:bg-muted/30 transition-colors"
              onClick={() => router.push(`/automations/${auto.id}`)}
            >
              <CardContent className="flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{auto.name}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {TRIGGER_LABELS[auto.trigger] ?? auto.trigger}
                    {auto.calendarName ? ` · ${auto.calendarName}` : ' · Tous les calendriers'}
                    {auto.stepsCount != null ? ` · ${auto.stepsCount} étapes` : ''}
                  </p>
                </div>
                <Switch
                  checked={auto.isActive}
                  onCheckedChange={() =>
                    toggleMutation.mutate({ id: auto.id, isActive: auto.isActive })
                  }
                  onClick={(e) => e.stopPropagation()}
                />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
