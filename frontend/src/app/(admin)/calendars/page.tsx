'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Calendar, Copy, ExternalLink, Pencil } from 'lucide-react';
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

interface CalendarItem {
  id: number;
  name: string;
  slug: string;
  slot_duration?: number;
  slotDuration?: number;
  description?: string;
  status: string;
  lead_count?: number;
  booking_count?: number;
}

function CreateCalendarDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [form, setForm] = useState({ name: '', slot_duration: '30', description: '' });

  const { mutate, isPending } = useMutation({
    mutationFn: (data: object) => api.post<CalendarItem>('/api/calendars', data),
    onSuccess: (cal) => {
      queryClient.invalidateQueries({ queryKey: ['calendars'] });
      onClose();
      router.push(`/calendars/${cal.id}`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutate({ ...form, slot_duration: Number(form.slot_duration) });
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nouveau calendrier</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Nom</Label>
            <Input
              placeholder="Consultation découverte"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              required
            />
          </div>
          <div className="space-y-2">
            <Label>Durée du slot</Label>
            <Select
              value={form.slot_duration}
              onValueChange={(v) => setForm((p) => ({ ...p, slot_duration: v }))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="15">15 min</SelectItem>
                <SelectItem value="30">30 min</SelectItem>
                <SelectItem value="45">45 min</SelectItem>
                <SelectItem value="60">1h</SelectItem>
                <SelectItem value="90">1h30</SelectItem>
                <SelectItem value="120">2h</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Description (optionnel)</Label>
            <Textarea
              placeholder="Brève description de ce calendrier..."
              value={form.description}
              onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Création...' : 'Créer'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function CalendarsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<{ data: CalendarItem[] }>({
    queryKey: ['calendars'],
    queryFn: () => api.get('/api/calendars'),
  });

  const calendars = data?.data ?? (Array.isArray(data) ? (data as CalendarItem[]) : []);

  const toggleActive = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.patch(`/api/calendars/${id}`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['calendars'] }),
    onError: (err: Error) => toast.error(err.message),
  });

  function copyLink(slug: string) {
    navigator.clipboard.writeText(`${window.location.origin}/book/${slug}`);
    toast.success('Lien copié');
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Calendriers"
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" />
            Nouveau calendrier
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardContent>
                <Skeleton className="mb-2 h-5 w-32" />
                <Skeleton className="h-4 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : !calendars.length ? (
        <EmptyState
          icon={Calendar}
          title="Aucun calendrier"
          description="Créez votre premier calendrier pour commencer à recevoir des RDV qualifiés"
          action={{ label: 'Créer un calendrier', onClick: () => setCreateOpen(true) }}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {calendars.map((cal) => (
            <Card key={cal.id}>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-semibold truncate">{cal.name}</h3>
                  <Switch
                    checked={cal.status === 'active'}
                    onCheckedChange={(checked) =>
                      toggleActive.mutate({ id: cal.id, status: checked ? 'active' : 'inactive' })
                    }
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  /book/{cal.slug} · {cal.slotDuration ?? cal.slot_duration} min
                </p>
                {cal.description && (
                  <p className="line-clamp-2 text-sm text-muted-foreground">{cal.description}</p>
                )}
                <div className="flex items-center justify-between">
                  <div className="flex gap-1">
                    <Link href={`/calendars/${cal.id}`}>
                      <Button variant="ghost" size="icon-sm">
                        <Pencil className="size-3.5" />
                      </Button>
                    </Link>
                    <Button variant="ghost" size="icon-sm" onClick={() => copyLink(cal.slug)}>
                      <Copy className="size-3.5" />
                    </Button>
                    <a href={`/book/${cal.slug}`} target="_blank" rel="noopener noreferrer">
                      <Button variant="ghost" size="icon-sm">
                        <ExternalLink className="size-3.5" />
                      </Button>
                    </a>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateCalendarDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
