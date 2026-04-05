'use client';

import { use, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Trash2, Plus, GripVertical, X, Pencil } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { PageHeader } from '@/components/shared/page-header';
import { EmptyState } from '@/components/shared/empty-state';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

const DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

// ─── General Tab ─────────────────────────────────────────────────────────────

function GeneralTab({ calendarId }: { calendarId: string }) {
  const queryClient = useQueryClient();
  const { data: cal, isLoading } = useQuery<{
    id: number; name: string; slug: string; slotDuration: number;
    description?: string; status: string;
  }>({
    queryKey: ['calendar', calendarId],
    queryFn: () => api.get(`/api/calendars/${calendarId}`),
  });

  const [form, setForm] = useState({ name: '', slug: '', slotDuration: '30', description: '' });
  const [initialized, setInitialized] = useState(false);

  // Sync form once when data arrives
  if (cal && !initialized) {
    setForm({
      name: cal.name, slug: cal.slug,
      slotDuration: String(cal.slotDuration),
      description: cal.description ?? '',
    });
    setInitialized(true);
  }

  const { mutate, isPending } = useMutation({
    mutationFn: () => api.patch(`/api/calendars/${calendarId}`, {
      name: form.name, slug: form.slug,
      slotDuration: Number(form.slotDuration),
      description: form.description,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', calendarId] });
      queryClient.invalidateQueries({ queryKey: ['calendars'] });
      toast.success('Calendrier mis à jour');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!cal) return null;

  const isDirty = form.name !== cal.name
    || form.slug !== cal.slug
    || form.slotDuration !== String(cal.slotDuration)
    || form.description !== (cal.description ?? '');

  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label className="text-xs">Nom</Label>
            <Input
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Slug (URL publique)</Label>
            <Input
              value={form.slug}
              onChange={(e) => setForm((p) => ({ ...p, slug: e.target.value }))}
            />
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label className="text-xs">Durée du slot</Label>
            <Select
              value={form.slotDuration}
              onValueChange={(v) => setForm((p) => ({ ...p, slotDuration: v }))}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {['15', '30', '45', '60', '90', '120'].map((v) => (
                  <SelectItem key={v} value={v}>{v} min</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Description</Label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
              rows={1}
            />
          </div>
        </div>
        {isDirty && (
          <Button size="sm" onClick={() => mutate()} disabled={isPending}>
            {isPending ? 'Sauvegarde...' : 'Sauvegarder'}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Availabilities Tab ───────────────────────────────────────────────────────

interface Availability {
  dayOfWeek: number;
  startTime: string;
  endTime: string;
  isActive: boolean;
  lunchStart?: string;
  lunchEnd?: string;
}

function AvailabilitiesTab({ calendarId }: { calendarId: string }) {
  const queryClient = useQueryClient();
  const { data: rawData, isLoading } = useQuery<{ data: Availability[] }>({
    queryKey: ['availabilities', calendarId],
    queryFn: () => api.get(`/api/calendars/${calendarId}/availabilities`),
  });
  const data = rawData?.data;

  const defaultAvail: Availability[] = Array.from({ length: 7 }, (_, i) => ({
    dayOfWeek: i, startTime: '09:00', endTime: '18:00', isActive: i < 5,
  }));

  const [avail, setAvail] = useState<Availability[]>(defaultAvail);
  const [serverAvail, setServerAvail] = useState<string>('');

  if (data && !serverAvail) {
    const resolved = Array.from({ length: 7 }, (_, i) =>
      data.find((a) => a.dayOfWeek === i) ?? defaultAvail[i]
    );
    setAvail(resolved);
    setServerAvail(JSON.stringify(resolved));
  }

  const availDirty = serverAvail && JSON.stringify(avail) !== serverAvail;

  const { mutate, isPending } = useMutation({
    mutationFn: () => api.put(`/api/calendars/${calendarId}/availabilities`, avail),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['availabilities', calendarId] });
      setServerAvail(JSON.stringify(avail));
      toast.success('Disponibilités mises à jour');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function update(idx: number, field: keyof Availability, value: string | boolean) {
    setAvail((prev) => prev.map((a, i) => i === idx ? { ...a, [field]: value } : a));
  }

  if (isLoading) return <Skeleton className="h-48 w-full" />;

  return (
    <Card>
      <CardContent className="space-y-2">
        {DAYS.map((day, i) => (
          <div key={i} className="flex flex-wrap items-center gap-3 rounded-md border px-3 py-2">
            <div className="flex items-center gap-2 w-28">
              <Switch
                checked={avail[i]?.isActive ?? false}
                onCheckedChange={(checked) => update(i, 'isActive', checked)}
              />
              <span className="text-sm font-medium">{day}</span>
            </div>
            {avail[i]?.isActive && (
              <>
                <div className="flex items-center gap-1">
                  <Input
                    type="time"
                    value={avail[i]?.startTime ?? '09:00'}
                    onChange={(e) => update(i, 'startTime', e.target.value)}
                    className="w-28"
                  />
                  <span className="text-xs text-muted-foreground">—</span>
                  <Input
                    type="time"
                    value={avail[i]?.endTime ?? '18:00'}
                    onChange={(e) => update(i, 'endTime', e.target.value)}
                    className="w-28"
                  />
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span>Pause:</span>
                  <Input
                    type="time"
                    value={avail[i]?.lunchStart ?? ''}
                    onChange={(e) => update(i, 'lunchStart', e.target.value)}
                    className="w-24"
                    placeholder="12:00"
                  />
                  <span>—</span>
                  <Input
                    type="time"
                    value={avail[i]?.lunchEnd ?? ''}
                    onChange={(e) => update(i, 'lunchEnd', e.target.value)}
                    className="w-24"
                    placeholder="13:00"
                  />
                </div>
              </>
            )}
          </div>
        ))}
        {availDirty && (
          <Button size="sm" onClick={() => mutate()} disabled={isPending}>
            {isPending ? 'Sauvegarde...' : 'Sauvegarder'}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Questions Tab ────────────────────────────────────────────────────────────

interface Question {
  id: string;
  label: string;
  type: string;
  options?: string[];
  required: boolean;
  position: number;
}

const typeLabel: Record<string, string> = {
  text: 'Texte', number: 'Nombre',
  single_choice: 'Choix unique', multiple_choice: 'Choix multiple',
};

function QuestionDialog({
  open,
  onClose,
  calendarId,
  question,
}: {
  open: boolean;
  onClose: () => void;
  calendarId: string;
  question?: Question;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!question;
  const [form, setForm] = useState({
    label: question?.label ?? '',
    type: question?.type ?? 'text',
    options: question?.options?.length ? question.options : [''],
    is_required: question?.required ?? true,
  });

  const mutation = useMutation({
    mutationFn: (data: object) =>
      isEdit
        ? api.patch(`/api/calendars/${calendarId}/questions/${question!.id}`, data)
        : api.post(`/api/calendars/${calendarId}/questions`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions', calendarId] });
      onClose();
      toast.success(isEdit ? 'Question modifiée' : 'Question ajoutée');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const opts = form.options.map((s) => s.trim()).filter(Boolean);
    mutation.mutate({
      label: form.label,
      type: form.type,
      options: opts.length ? opts : undefined,
      required: form.is_required,
      ...(!isEdit && { position: 999 }),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Modifier la question' : 'Ajouter une question'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Libellé</Label>
            <Input
              value={form.label}
              onChange={(e) => setForm((p) => ({ ...p, label: e.target.value }))}
              placeholder="Quel est votre budget mensuel ?"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Type</Label>
            <Select value={form.type} onValueChange={(v) => setForm((p) => ({ ...p, type: v }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="text">Texte libre</SelectItem>
                <SelectItem value="number">Nombre</SelectItem>
                <SelectItem value="single_choice">Choix unique</SelectItem>
                <SelectItem value="multiple_choice">Choix multiple</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {(form.type === 'single_choice' || form.type === 'multiple_choice') && (
            <div className="space-y-1.5">
              <Label className="text-xs">Options</Label>
              <div className="space-y-1.5">
                {form.options.map((opt, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      value={opt}
                      onChange={(e) => setForm((p) => {
                        const next = [...p.options];
                        next[i] = e.target.value;
                        return { ...p, options: next };
                      })}
                      placeholder={`Option ${i + 1}`}
                    />
                    {form.options.length > 1 && (
                      <Button
                        type="button" variant="ghost" size="icon-sm"
                        onClick={() => setForm((p) => ({ ...p, options: p.options.filter((_, j) => j !== i) }))}
                      >
                        <X className="size-3.5 text-muted-foreground" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  type="button" variant="outline" size="sm"
                  onClick={() => setForm((p) => ({ ...p, options: [...p.options, ''] }))}
                >
                  <Plus className="size-3.5" /> Option
                </Button>
              </div>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Switch
              id="q_required"
              checked={form.is_required}
              onCheckedChange={(checked) => setForm((p) => ({ ...p, is_required: checked }))}
            />
            <Label htmlFor="q_required" className="text-xs">Obligatoire</Label>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>Annuler</Button>
            <Button type="submit" size="sm" disabled={mutation.isPending}>
              {isEdit ? 'Enregistrer' : 'Ajouter'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function QuestionsTab({ calendarId }: { calendarId: string }) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editQuestion, setEditQuestion] = useState<Question | undefined>();

  const { data: rawQuestions, isLoading } = useQuery<{ data: Question[] }>({
    queryKey: ['questions', calendarId],
    queryFn: () => api.get(`/api/calendars/${calendarId}/questions`),
  });
  const questions = rawQuestions?.data ?? [];

  const deleteMutation = useMutation({
    mutationFn: (qid: string) => api.delete(`/api/calendars/${calendarId}/questions/${qid}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions', calendarId] });
      toast.success('Question supprimée');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function openAdd() { setEditQuestion(undefined); setDialogOpen(true); }
  function openEdit(q: Question) { setEditQuestion(q); setDialogOpen(true); }

  if (isLoading) return <Skeleton className="h-32 w-full" />;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm">Questions de qualification</CardTitle>
        <Button size="sm" variant="outline" onClick={openAdd}>
          <Plus className="size-3.5" /> Ajouter
        </Button>
      </CardHeader>
      <CardContent className="space-y-1.5">
      {!questions.length ? (
        <EmptyState title="Aucune question" description="Les prospects iront directement aux créneaux" />
      ) : (
        <>
          {questions.map((q) => (
            <div key={q.id} className="flex items-center gap-2 rounded-md border px-3 py-2">
              <GripVertical className="size-3.5 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{q.label}</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <Badge variant="secondary" className="text-[10px]">{typeLabel[q.type] ?? q.type}</Badge>
                  <Badge variant={q.required ? 'default' : 'outline'} className="text-[10px]">
                    {q.required ? 'Obligatoire' : 'Optionnel'}
                  </Badge>
                  {q.options?.map((opt, i) => (
                    <Badge key={i} variant="outline" className="text-[10px] font-normal">{opt}</Badge>
                  ))}
                </div>
              </div>
              <Button variant="ghost" size="icon-sm" onClick={() => openEdit(q)}>
                <Pencil className="size-3.5" />
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="ghost" size="icon-sm">
                    <Trash2 className="size-3.5 text-destructive" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Supprimer la question ?</AlertDialogTitle>
                    <AlertDialogDescription>Les règles associées seront aussi supprimées.</AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Annuler</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => deleteMutation.mutate(q.id)}
                      className="bg-destructive text-white hover:bg-destructive/90"
                    >
                      Supprimer
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          ))}
        </>
      )}
      </CardContent>

      <QuestionDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        calendarId={calendarId}
        question={editQuestion}
      />
    </Card>
  );
}

// ─── Rules Tab ────────────────────────────────────────────────────────────────

interface Rule {
  id: string;
  questionId: string;
  questionLabel?: string;
  questionType?: string;
  disqualifyValues?: string[];
  minLength?: number;
  containsKeywords?: string[];
  minValue?: number;
}

function ruleDescription(r: Rule): string {
  const label = r.questionLabel ?? `Question #${r.questionId}`;
  if (r.disqualifyValues?.length) return `"${label}" = [${r.disqualifyValues.join(', ')}]`;
  if (r.minLength) return `"${label}" < ${r.minLength} caractères`;
  if (r.containsKeywords?.length) return `"${label}" contient [${r.containsKeywords.join(', ')}]`;
  if (r.minValue !== undefined && r.minValue !== null) return `"${label}" < ${r.minValue}`;
  return `Règle sur "${label}"`;
}

interface RuleFormData {
  questionId: string;
  disqualifyValues: string[];
  minLength: string;
  containsKeywords: string;
  minValue: string;
}

const emptyRuleForm: RuleFormData = {
  questionId: '', disqualifyValues: [], minLength: '', containsKeywords: '', minValue: '',
};

function ruleToForm(r: Rule): RuleFormData {
  return {
    questionId: r.questionId,
    disqualifyValues: r.disqualifyValues ?? [],
    minLength: r.minLength ? String(r.minLength) : '',
    containsKeywords: r.containsKeywords?.join(', ') ?? '',
    minValue: r.minValue !== undefined && r.minValue !== null ? String(r.minValue) : '',
  };
}

function RuleDialog({
  open,
  onClose,
  calendarId,
  questions,
  rule,
}: {
  open: boolean;
  onClose: () => void;
  calendarId: string;
  questions: Question[];
  rule?: Rule;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!rule;
  const [form, setForm] = useState<RuleFormData>(rule ? ruleToForm(rule) : emptyRuleForm);
  const selectedQuestion = questions.find((q) => q.id === form.questionId);

  const mutation = useMutation({
    mutationFn: (data: object) =>
      isEdit
        ? api.patch(`/api/calendars/${calendarId}/rules/${rule!.id}`, data)
        : api.post(`/api/calendars/${calendarId}/rules`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', calendarId] });
      onClose();
      toast.success(isEdit ? 'Règle modifiée' : 'Règle ajoutée');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function toggleDisqualifyValue(option: string) {
    setForm((p) => ({
      ...p,
      disqualifyValues: p.disqualifyValues.includes(option)
        ? p.disqualifyValues.filter((v) => v !== option)
        : [...p.disqualifyValues, option],
    }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedQuestion) return;
    const payload: Record<string, unknown> = isEdit ? {} : { questionId: form.questionId };

    if (selectedQuestion.type === 'single_choice' || selectedQuestion.type === 'multiple_choice') {
      if (!form.disqualifyValues.length) { toast.error('Sélectionnez au moins une option'); return; }
      payload.disqualifyValues = form.disqualifyValues;
    } else if (selectedQuestion.type === 'text') {
      const ml = form.minLength ? parseInt(form.minLength, 10) : null;
      const kw = form.containsKeywords.split(',').map((s) => s.trim()).filter(Boolean);
      if (!ml && !kw.length) { toast.error('Renseignez au moins un critère'); return; }
      if (ml) payload.minLength = ml;
      if (kw.length) payload.containsKeywords = kw;
    } else if (selectedQuestion.type === 'number') {
      const mv = form.minValue ? parseFloat(form.minValue) : null;
      if (mv === null || isNaN(mv)) { toast.error('Renseignez une valeur minimum'); return; }
      payload.minValue = mv;
    }
    mutation.mutate(payload);
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Modifier la règle' : 'Ajouter une règle'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Question</Label>
            <Select
              value={form.questionId}
              onValueChange={(v) => setForm({ ...emptyRuleForm, questionId: v })}
              disabled={isEdit}
            >
              <SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger>
              <SelectContent>
                {questions.map((q) => (
                  <SelectItem key={q.id} value={String(q.id)}>{q.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedQuestion && (selectedQuestion.type === 'single_choice' || selectedQuestion.type === 'multiple_choice') && (
            <div className="space-y-1.5">
              <Label className="text-xs">Options disqualifiantes</Label>
              <div className="space-y-1">
                {(selectedQuestion.options ?? []).map((opt) => (
                  <label key={opt} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={form.disqualifyValues.includes(opt)}
                      onChange={() => toggleDisqualifyValue(opt)}
                      className="size-3.5"
                    />
                    {opt}
                  </label>
                ))}
              </div>
            </div>
          )}

          {selectedQuestion?.type === 'text' && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Longueur min (caractères)</Label>
                <Input
                  type="number" min={1}
                  value={form.minLength}
                  onChange={(e) => setForm((p) => ({ ...p, minLength: e.target.value }))}
                  placeholder="ex: 10"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Mots-clés disqualifiants</Label>
                <Input
                  value={form.containsKeywords}
                  onChange={(e) => setForm((p) => ({ ...p, containsKeywords: e.target.value }))}
                  placeholder="spam, test, non"
                />
              </div>
            </div>
          )}

          {selectedQuestion?.type === 'number' && (
            <div className="space-y-1.5">
              <Label className="text-xs">Valeur minimum</Label>
              <Input
                type="number"
                value={form.minValue}
                onChange={(e) => setForm((p) => ({ ...p, minValue: e.target.value }))}
                placeholder="ex: 1000"
                required
              />
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>Annuler</Button>
            <Button type="submit" size="sm" disabled={mutation.isPending || !form.questionId}>
              {isEdit ? 'Enregistrer' : 'Ajouter'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RulesTab({ calendarId }: { calendarId: string }) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editRule, setEditRule] = useState<Rule | undefined>();

  const { data: rawQ } = useQuery<{ data: Question[] }>({
    queryKey: ['questions', calendarId],
    queryFn: () => api.get(`/api/calendars/${calendarId}/questions`),
  });
  const questions = rawQ?.data ?? [];

  const { data: rawRules, isLoading } = useQuery<{ data: Rule[] }>({
    queryKey: ['rules', calendarId],
    queryFn: () => api.get(`/api/calendars/${calendarId}/rules`),
  });
  const rules = rawRules?.data ?? [];

  const deleteMutation = useMutation({
    mutationFn: (rid: string) => api.delete(`/api/calendars/${calendarId}/rules/${rid}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', calendarId] });
      toast.success('Règle supprimée');
    },
  });

  function openAdd() { setEditRule(undefined); setDialogOpen(true); }
  function openEdit(r: Rule) { setEditRule(r); setDialogOpen(true); }

  if (isLoading) return <Skeleton className="h-32 w-full" />;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm">Règles de disqualification</CardTitle>
        <Button size="sm" variant="outline" onClick={openAdd}>
          <Plus className="size-3.5" /> Ajouter
        </Button>
      </CardHeader>
      <CardContent className="space-y-1.5">
        <p className="rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          Si une règle est déclenchée, le prospect est disqualifié. Sans règle, tous sont qualifiés.
        </p>

        {!rules.length ? (
          <EmptyState title="Aucune règle" description="Tous les prospects seront qualifiés par défaut" />
        ) : (
          <>
            {rules.map((r) => (
              <div key={r.id} className="flex items-center gap-2 rounded-md border px-3 py-2">
                <p className="flex-1 text-sm min-w-0 truncate">
                  {ruleDescription(r)}
                </p>
                <Badge variant="destructive" className="text-[10px] shrink-0">disqualifié</Badge>
                <Button variant="ghost" size="icon-sm" onClick={() => openEdit(r)}>
                  <Pencil className="size-3.5" />
                </Button>
                <Button variant="ghost" size="icon-sm" onClick={() => deleteMutation.mutate(r.id)}>
                  <Trash2 className="size-3.5 text-destructive" />
                </Button>
              </div>
            ))}
          </>
        )}
      </CardContent>

      <RuleDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        calendarId={calendarId}
        questions={questions}
        rule={editRule}
      />
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CalendarEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const calendarId = id;
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: cal } = useQuery<{ id: number; name: string; slug: string; status: string }>({
    queryKey: ['calendar', calendarId],
    queryFn: () => api.get(`/api/calendars/${calendarId}`),
  });

  const isActive = cal?.status === 'active';

  const toggleActive = useMutation({
    mutationFn: (active: boolean) =>
      api.patch(`/api/calendars/${calendarId}`, { status: active ? 'active' : 'inactive' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', calendarId] });
      queryClient.invalidateQueries({ queryKey: ['calendars'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/api/calendars/${calendarId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendars'] });
      toast.success('Calendrier supprimé');
      router.push('/calendars');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title={cal?.name ?? 'Chargement...'}
        actions={
          <div className="flex items-center gap-2">
            {cal && (
              <Switch
                checked={isActive}
                onCheckedChange={(checked) => toggleActive.mutate(checked)}
              />
            )}
            {cal && (
              <a href={`/book/${cal.slug}`} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="icon-sm">
                  <ExternalLink className="size-3.5" />
                </Button>
              </a>
            )}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="ghost" size="icon-sm">
                  <Trash2 className="size-3.5 text-destructive" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Supprimer ce calendrier ?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Tous les leads, RDV et questions associés seront supprimés.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Annuler</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => deleteMutation.mutate()}
                    className="bg-destructive text-white hover:bg-destructive/90"
                  >
                    Supprimer
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        }
      />

      <Tabs defaultValue="general">
        <TabsList>
          <TabsTrigger value="general">Général</TabsTrigger>
          <TabsTrigger value="availabilities">Disponibilités</TabsTrigger>
          <TabsTrigger value="questions">Questions</TabsTrigger>
          <TabsTrigger value="rules">Règles</TabsTrigger>
        </TabsList>
        <TabsContent value="general" className="mt-3">
          <GeneralTab calendarId={calendarId} />
        </TabsContent>
        <TabsContent value="availabilities" className="mt-3">
          <AvailabilitiesTab calendarId={calendarId} />
        </TabsContent>
        <TabsContent value="questions" className="mt-3">
          <QuestionsTab calendarId={calendarId} />
        </TabsContent>
        <TabsContent value="rules" className="mt-3">
          <RulesTab calendarId={calendarId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
