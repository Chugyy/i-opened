'use client';

import { use, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, Trash2, Pencil, Check, X } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { StatusBadge } from '@/components/shared/status-badge';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

interface Automation {
  id: string;
  name: string;
  trigger: string;
  calendarId?: string;
  isActive: boolean;
}

interface Step {
  id: string;
  channel: string;
  delayValue: number;
  delayUnit: string;
  content: string;
  position: number;
}

const TRIGGERS = [
  { value: 'booking_confirme', label: 'Booking confirmé' },
  { value: 'avant_rdv', label: 'Avant le RDV' },
  { value: 'apres_rdv', label: 'Après le RDV' },
  { value: 'qualifie_sans_booking', label: 'Qualifié sans booking' },
  { value: 'coordonnees_sans_booking', label: 'Coordonnées sans booking' },
];

const VARIABLES = ['{prenom}', '{nom}', '{email}', '{telephone}', '{date_rdv}', '{calendrier}'];

export default function AutomationEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const isNew = id === 'new';
  const autoId = isNew ? null : id;
  const router = useRouter();
  const queryClient = useQueryClient();

  const [form, setForm] = useState({ name: '', trigger: 'avant_rdv', is_active: true, calendar_id: '' });
  const [addingStep, setAddingStep] = useState(false);
  const [newStep, setNewStep] = useState({ channel: 'email', delay_value: '0', delay_unit: 'minutes', content: '' });
  const [editingStepId, setEditingStepId] = useState<string | null>(null);
  const [editStep, setEditStep] = useState({ channel: '', delay_value: '', delay_unit: '', content: '' });

  const { data: auto, isLoading } = useQuery<Automation>({
    queryKey: ['automation', autoId],
    queryFn: () => api.get(`/api/automations/${autoId}`),
    enabled: !isNew,
  });

  const { data: stepsData, isLoading: stepsLoading } = useQuery<{ data: Step[] } | Step[]>({
    queryKey: ['steps', autoId],
    queryFn: () => api.get(`/api/automations/${autoId}/steps`),
    enabled: !isNew,
  });

  const steps: Step[] = Array.isArray(stepsData) ? stepsData : (stepsData?.data ?? []);

  const { data: calendarsRaw } = useQuery<unknown>({
    queryKey: ['calendars-list'],
    queryFn: () => api.get('/api/calendars'),
  });
  const calendars: { id: string; name: string }[] = Array.isArray(calendarsRaw)
    ? calendarsRaw
    : Array.isArray((calendarsRaw as Record<string, unknown>)?.data)
      ? (calendarsRaw as Record<string, unknown>).data as { id: string; name: string }[]
      : [];

  const saveAutoMutation = useMutation({
    mutationFn: (data: object) =>
      isNew
        ? api.post('/api/automations', data)
        : api.patch(`/api/automations/${autoId}`, data),
    onSuccess: (res: unknown) => {
      queryClient.invalidateQueries({ queryKey: ['automations'] });
      toast.success(isNew ? 'Automation créée' : 'Automation sauvegardée');
      if (isNew) router.push(`/automations/${(res as Automation).id}`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const addStepMutation = useMutation({
    mutationFn: (data: object) => api.post(`/api/automations/${autoId}/steps`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['steps', autoId] });
      setAddingStep(false);
      setNewStep({ channel: 'email', delay_value: '1', delay_unit: 'hours', content: '' });
      toast.success('Étape ajoutée');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteStepMutation = useMutation({
    mutationFn: (sid: string) => api.delete(`/api/automations/${autoId}/steps/${sid}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['steps', autoId] });
      toast.success('Étape supprimée');
    },
  });

  const updateStepMutation = useMutation({
    mutationFn: ({ sid, data }: { sid: string; data: object }) => api.patch(`/api/automations/${autoId}/steps/${sid}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['steps', autoId] });
      setEditingStepId(null);
      toast.success('Étape modifiée');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteAutoMutation = useMutation({
    mutationFn: () => api.delete(`/api/automations/${autoId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automations'] });
      toast.success('Automation supprimée');
      router.push('/automations');
    },
  });

  const currentForm = form.name ? form : {
    name: auto?.name ?? '', trigger: auto?.trigger ?? 'avant_rdv', is_active: auto?.isActive ?? true, calendar_id: form.calendar_id,
  };

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    saveAutoMutation.mutate(currentForm);
  }

  function appendVar(v: string) {
    setNewStep((p) => ({ ...p, content: p.content + v }));
  }

  if (!isNew && isLoading) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/automations">
          <Button variant="ghost" size="icon-sm"><ArrowLeft className="size-4" /></Button>
        </Link>
        <h1 className="text-xl font-semibold">
          {isNew ? 'Nouvelle automation' : (auto?.name ?? 'Automation')}
        </h1>
        {/* Toggle dans la card config — pas besoin de badge ici */}
      </div>

      {/* Configuration — compact form */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Configuration</CardTitle>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Switch
                id="auto_active"
                checked={currentForm.is_active}
                onCheckedChange={(checked) => setForm((p) => ({ ...p, is_active: checked }))}
              />
              <Label htmlFor="auto_active" className="text-xs text-muted-foreground">Actif</Label>
            </div>
            {!isNew && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="ghost" size="icon-sm">
                    <Trash2 className="size-3.5 text-destructive" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Supprimer cette automation ?</AlertDialogTitle>
                    <AlertDialogDescription>Action irréversible.</AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Annuler</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => deleteAutoMutation.mutate()}
                      className="bg-destructive text-white hover:bg-destructive/90"
                    >
                      Supprimer
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Nom</Label>
                <Input
                  value={currentForm.name}
                  onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                  placeholder="Relance avant RDV"
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Trigger</Label>
                <Select value={currentForm.trigger} onValueChange={(v) => setForm((p) => ({ ...p, trigger: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TRIGGERS.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Calendrier</Label>
                <Select
                  value={form.calendar_id || 'all'}
                  onValueChange={(v) => setForm((p) => ({ ...p, calendar_id: v === 'all' ? '' : v }))}
                >
                  <SelectTrigger><SelectValue placeholder="Tous" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous les calendriers</SelectItem>
                    {calendars.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {(isNew || form.name) && (
              <Button size="sm" type="submit" disabled={saveAutoMutation.isPending}>
                {saveAutoMutation.isPending ? 'Sauvegarde...' : 'Sauvegarder'}
              </Button>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Steps */}
      {!isNew && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm">Étapes</CardTitle>
            <Button size="sm" variant="outline" onClick={() => setAddingStep(true)}>
              <Plus className="size-3.5" /> Ajouter
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {stepsLoading ? (
              <Skeleton className="h-20" />
            ) : !steps.length ? (
              <p className="text-sm text-muted-foreground text-center py-3">
                Aucune étape — ajoutez votre première action
              </p>
            ) : (
              steps.map((step, idx) => (
                <div key={step.id} className="rounded-md border px-3 py-2 space-y-2">
                  {editingStepId === step.id ? (
                    /* Edit mode */
                    <div className="space-y-2">
                      <div className="grid gap-2 sm:grid-cols-3">
                        <Select value={editStep.channel} onValueChange={(v) => setEditStep((p) => ({ ...p, channel: v }))}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="email">Email</SelectItem>
                            <SelectItem value="whatsapp">WhatsApp</SelectItem>
                          </SelectContent>
                        </Select>
                        <Input type="number" min="0" value={editStep.delay_value} onChange={(e) => setEditStep((p) => ({ ...p, delay_value: e.target.value }))} />
                        <Select value={editStep.delay_unit} onValueChange={(v) => setEditStep((p) => ({ ...p, delay_unit: v }))}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="minutes">Minutes</SelectItem>
                            <SelectItem value="hours">Heures</SelectItem>
                            <SelectItem value="days">Jours</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <Textarea value={editStep.content} onChange={(e) => setEditStep((p) => ({ ...p, content: e.target.value }))} rows={2} />
                      <div className="flex gap-1.5">
                        <Button size="sm" onClick={() => updateStepMutation.mutate({ sid: step.id, data: { channel: editStep.channel, delayValue: Number(editStep.delay_value), delayUnit: editStep.delay_unit, content: editStep.content } })}>
                          <Check className="size-3.5" /> Enregistrer
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setEditingStepId(null)}>
                          <X className="size-3.5" /> Annuler
                        </Button>
                      </div>
                    </div>
                  ) : (
                    /* View mode */
                    <div className="flex items-start gap-2">
                      <div className="flex-1 space-y-0.5">
                        <div className="flex items-center gap-2 text-xs">
                          <span className="font-medium text-muted-foreground">#{idx + 1}</span>
                          <span className="capitalize">{step.channel}</span>
                          <span className="text-muted-foreground">
                            · {step.delayValue === 0 ? 'Instant' : `${step.delayValue} ${step.delayUnit === 'minutes' ? 'min' : step.delayUnit === 'hours' ? 'h' : 'j'}`}
                          </span>
                        </div>
                        <p className="text-sm line-clamp-2">{step.content}</p>
                      </div>
                      <Button variant="ghost" size="icon-sm" onClick={() => { setEditingStepId(step.id); setEditStep({ channel: step.channel, delay_value: String(step.delayValue), delay_unit: step.delayUnit, content: step.content }); }}>
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => deleteStepMutation.mutate(step.id)}>
                        <Trash2 className="size-3.5 text-destructive" />
                      </Button>
                    </div>
                  )}
                </div>
              ))
            )}

            {addingStep && (
              <div className="rounded-md border border-primary/30 bg-muted/20 p-3 space-y-2.5">
                <p className="text-xs font-medium">Nouvelle étape</p>
                <div className="grid gap-2 sm:grid-cols-3">
                  <div className="space-y-1">
                    <Label className="text-xs">Canal</Label>
                    <Select value={newStep.channel} onValueChange={(v) => setNewStep((p) => ({ ...p, channel: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="email">Email</SelectItem>
                        <SelectItem value="whatsapp">WhatsApp</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Délai</Label>
                    <Input
                      type="number"
                      min="0"
                      value={newStep.delay_value}
                      onChange={(e) => setNewStep((p) => ({ ...p, delay_value: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Unité</Label>
                    <Select value={newStep.delay_unit} onValueChange={(v) => setNewStep((p) => ({ ...p, delay_unit: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="minutes">Minutes</SelectItem>
                        <SelectItem value="hours">Heures</SelectItem>
                        <SelectItem value="days">Jours</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Message</Label>
                  <Textarea
                    value={newStep.content}
                    onChange={(e) => setNewStep((p) => ({ ...p, content: e.target.value }))}
                    rows={3}
                    placeholder="Bonjour {prenom}, votre RDV est prévu le {date_rdv}..."
                  />
                  <div className="flex flex-wrap gap-1">
                    {VARIABLES.map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() => appendVar(v)}
                        className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono hover:bg-primary/20"
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => addStepMutation.mutate({
                      channel: newStep.channel,
                      delay_value: Number(newStep.delay_value),
                      delay_unit: newStep.delay_unit,
                      content: newStep.content,
                    })}
                    disabled={addStepMutation.isPending || !newStep.content}
                  >
                    Ajouter
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setAddingStep(false)}>Annuler</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
