'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

const TRIGGERS = [
  { value: 'booking_confirme', label: 'Booking confirmé' },
  { value: 'avant_rdv', label: 'Avant le RDV' },
  { value: 'apres_rdv', label: 'Après le RDV' },
  { value: 'qualifie_sans_booking', label: 'Qualifié sans booking' },
  { value: 'coordonnees_sans_booking', label: 'Coordonnées sans booking' },
];

interface Automation { id: string }

export default function NewAutomationPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: '', trigger: 'avant_rdv', is_active: true, calendar_id: '' });

  const { data: calendarsData } = useQuery<{ data?: { id: number; name: string }[] } | { id: number; name: string }[]>({
    queryKey: ['calendars-list'],
    queryFn: () => api.get('/api/calendars'),
  });

  const calendars = Array.isArray(calendarsData) ? calendarsData : (calendarsData?.data ?? []);

  const createMutation = useMutation({
    mutationFn: (data: object) => api.post<Automation>('/api/automations', data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['automations'] });
      toast.success('Automation créée');
      router.push(`/automations/${res.id}`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    createMutation.mutate({
      name: form.name,
      trigger: form.trigger,
      is_active: form.is_active,
      ...(form.calendar_id ? { calendar_id: form.calendar_id } : {}),
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/automations">
          <Button variant="ghost" size="icon-sm"><ArrowLeft className="size-4" /></Button>
        </Link>
        <h1 className="text-2xl font-semibold">Nouvelle automation</h1>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Configuration</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Nom</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                  placeholder="Relance avant RDV"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Trigger</Label>
                <Select value={form.trigger} onValueChange={(v) => setForm((p) => ({ ...p, trigger: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TRIGGERS.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Calendrier (optionnel)</Label>
                <Select value={form.calendar_id || 'all'} onValueChange={(v) => setForm((p) => ({ ...p, calendar_id: v === 'all' ? '' : v }))}>
                  <SelectTrigger><SelectValue placeholder="Tous les calendriers" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous les calendriers</SelectItem>
                    {calendars.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_active"
                checked={form.is_active}
                onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))}
                className="size-4"
              />
              <Label htmlFor="is_active">Automation active dès la création</Label>
            </div>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Création...' : 'Créer et ajouter des étapes'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
