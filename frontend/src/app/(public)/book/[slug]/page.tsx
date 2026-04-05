'use client';

import { use, useState, useEffect } from 'react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, isBefore, startOfDay } from 'date-fns';
import { fr } from 'date-fns/locale';
import { CalendarCheck, ChevronLeft, ChevronRight, CheckCircle2, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PublicCalendar {
  calendarId: string;
  name: string;
  description?: string;
  slotDuration: number;
  questions: Question[];
}

interface Question {
  id: string;
  label: string;
  type: string;
  options?: string[];
  required: boolean;
}

interface Slot { startsAt: string; endsAt: string; }
interface QualifyResponse { leadId: string; qualified: boolean; }

// ─── Slots Panel ─────────────────────────────────────────────────────────────

function SlotsPanel({
  slug,
  calendar,
  leadId,
  unlocked,
  onConfirm,
}: {
  slug: string;
  calendar: PublicCalendar;
  leadId: string | null;
  unlocked: boolean;
  onConfirm: (slot: Slot) => void;
}) {
  const [selectedMonth, setSelectedMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);

  const today = startOfDay(new Date());
  const monthStart = startOfMonth(selectedMonth);
  const monthDays = eachDayOfInterval({ start: monthStart, end: endOfMonth(selectedMonth) });

  async function loadSlots(date: Date) {
    setSelectedDate(date);
    setSelectedSlot(null);
    setSlotsLoading(true);
    try {
      const dateStr = format(date, 'yyyy-MM-dd');
      const res = await fetch(
        `${API}/api/book/${slug}/slots?date=${dateStr}${leadId ? `&leadId=${leadId}` : ''}`
      );
      const data = await res.json();
      setSlots(Array.isArray(data) ? data : (data.slots ?? []));
    } catch {
      toast.error('Impossible de charger les créneaux');
    } finally {
      setSlotsLoading(false);
    }
  }

  return (
    <div className={cn('space-y-3 transition-all duration-300', !unlocked && 'pointer-events-none select-none blur-sm')}>
      {!unlocked && (
        <p className="text-center text-sm text-muted-foreground">
          Remplissez le formulaire pour débloquer les créneaux
        </p>
      )}

      {/* Month nav */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setSelectedMonth((m) => subMonths(m, 1))}
          className="rounded-md p-1 hover:bg-muted"
          disabled={isBefore(subMonths(selectedMonth, 1), today)}
        >
          <ChevronLeft className="size-4" />
        </button>
        <p className="text-sm font-medium capitalize">
          {format(selectedMonth, 'MMMM yyyy', { locale: fr })}
        </p>
        <button
          onClick={() => setSelectedMonth((m) => addMonths(m, 1))}
          className="rounded-md p-1 hover:bg-muted"
        >
          <ChevronRight className="size-4" />
        </button>
      </div>

      {/* Day grid */}
      <div className="grid grid-cols-7 gap-1 text-center">
        {['Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa', 'Di'].map((d) => (
          <div key={d} className="py-1 text-xs font-medium text-muted-foreground">{d}</div>
        ))}
        {Array.from({ length: (monthStart.getDay() + 6) % 7 }).map((_, i) => (
          <div key={`e-${i}`} />
        ))}
        {monthDays.map((day) => {
          const isPast = isBefore(day, today);
          const isSelected = selectedDate ? isSameDay(day, selectedDate) : false;
          return (
            <button
              key={day.toISOString()}
              disabled={isPast}
              onClick={() => loadSlots(day)}
              className={cn(
                'rounded-md py-1.5 text-sm transition-colors',
                isPast ? 'cursor-not-allowed opacity-30' : 'hover:bg-muted',
                isSelected ? 'bg-primary text-primary-foreground hover:bg-primary/90' : ''
              )}
            >
              {format(day, 'd')}
            </button>
          );
        })}
      </div>

      {/* Time slots */}
      {selectedDate && (
        <div className="space-y-2">
          <p className="text-sm font-medium">
            {format(selectedDate, 'dd MMMM yyyy', { locale: fr })}
          </p>
          {slotsLoading ? (
            <div className="grid grid-cols-3 gap-2">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9" />)}
            </div>
          ) : !slots.length ? (
            <p className="text-sm text-muted-foreground">Aucun créneau disponible.</p>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {slots.filter((s) => s.startsAt).map((slot) => (
                <button
                  key={slot.startsAt}
                  onClick={() => setSelectedSlot(slot)}
                  className={cn(
                    'rounded-md border px-3 py-2 text-sm transition-colors',
                    selectedSlot?.startsAt === slot.startsAt
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border hover:bg-muted'
                  )}
                >
                  {format(new Date(slot.startsAt), 'HH:mm')}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {selectedSlot && (
        <Button className="w-full" onClick={() => onConfirm(selectedSlot)}>
          Confirmer · {format(new Date(selectedSlot.startsAt), 'dd MMM à HH:mm', { locale: fr })}
        </Button>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function BookingPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);

  const [calendar, setCalendar] = useState<PublicCalendar | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [qualified, setQualified] = useState(false);
  const [rejected, setRejected] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [leadId, setLeadId] = useState<string | null>(null);
  const [bookingResult, setBookingResult] = useState<{ startsAt: string; endsAt: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [contact, setContact] = useState({ first_name: '', last_name: '', email: '', phone: '' });
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});

  useEffect(() => {
    fetch(`${API}/api/book/${slug}`, { cache: 'no-store' })
      .then(async (res) => {
        if (res.status === 404) { setError('Calendrier introuvable'); return; }
        if (res.status === 410 || !res.ok) { setError('Ce calendrier n\'est plus disponible'); return; }
        setCalendar(await res.json());
      })
      .catch(() => setError('Impossible de charger le calendrier'))
      .finally(() => setLoading(false));
  }, [slug]);

  async function handleSubmitForm(e: React.FormEvent) {
    e.preventDefault();
    if (!calendar) return;
    setSubmitting(true);

    const questionAnswers = calendar.questions.map((q) => ({
      questionId: q.id,
      value: answers[q.id] ?? '',
    }));

    try {
      const res = await fetch(`${API}/api/book/${slug}/qualify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...contact, answers: questionAnswers }),
      });
      if (!res.ok) { toast.error('Erreur lors de la soumission'); return; }
      const data: QualifyResponse = await res.json();
      setLeadId(data.leadId);
      if (!data.qualified) { setRejected(true); return; }
      setQualified(true);
    } catch {
      toast.error('Erreur réseau');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirm(slot: Slot) {
    if (!leadId) return;
    try {
      const res = await fetch(`${API}/api/book/${slug}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leadId, startsAt: slot.startsAt, endsAt: slot.endsAt }),
      });
      if (res.status === 409) { toast.error('Ce créneau vient d\'être pris.'); return; }
      if (!res.ok) { toast.error('Erreur lors de la confirmation'); return; }
      setBookingResult({ startsAt: slot.startsAt, endsAt: slot.endsAt });
      setConfirmed(true);
    } catch {
      toast.error('Erreur réseau');
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Skeleton className="h-96 w-full max-w-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-4 text-center">
        <CalendarCheck className="size-8 text-muted-foreground" />
        <p className="text-lg font-semibold">{error}</p>
      </div>
    );
  }

  if (rejected) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-4 text-center">
        <CalendarCheck className="mx-auto size-8 text-muted-foreground" />
        <h2 className="text-lg font-semibold">Aucun créneau disponible</h2>
        <p className="max-w-xs text-sm text-muted-foreground">
          Aucun créneau n'est disponible pour le moment. Nous vous recontacterons si un créneau se libère.
        </p>
      </div>
    );
  }

  if (confirmed && bookingResult) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-5 p-4 text-center">
        <div className="rounded-full bg-green-500/10 p-4">
          <CheckCircle2 className="size-10 text-green-500" />
        </div>
        <div className="max-w-sm space-y-1.5">
          <h1 className="text-xl font-semibold">RDV confirmé !</h1>
          <p className="text-muted-foreground">
            {format(new Date(bookingResult.startsAt), 'EEEE dd MMMM yyyy à HH:mm', { locale: fr })}
          </p>
          <p className="text-sm text-muted-foreground">
            Confirmation envoyée à <strong>{contact.email}</strong>
          </p>
        </div>
        <p className="text-xs text-muted-foreground">Powered by I-Opened</p>
      </div>
    );
  }

  // ─── Main: Single card with header + split ───────────────────────────────

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-4">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <CalendarCheck className="size-5 text-primary" />
        <span className="font-semibold">I-Opened</span>
      </div>

      {/* Single card — constrained */}
      <div className="w-full max-w-3xl max-h-[600px] rounded-xl border bg-card shadow-sm overflow-hidden flex flex-col">
        {/* Card header: title + description */}
        <div className="px-5 py-4 shrink-0">
          <h1 className="text-lg font-semibold">{calendar?.name}</h1>
          {calendar?.description && (
            <p className="mt-1 text-sm text-muted-foreground">{calendar.description}</p>
          )}
          <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="size-3" /> {calendar?.slotDuration} min
            </span>
          </div>
        </div>

        {/* Card body: split — each side scrolls independently */}
        <div className="grid md:grid-cols-2 min-h-0 flex-1 border-t">
          {/* Left: Form — independent scroll */}
          <div className="overflow-y-auto p-5 md:border-r">
            <form onSubmit={handleSubmitForm} className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Coordonnées</p>
              <div className="grid gap-3 grid-cols-2">
                <div className="space-y-1">
                  <Label className="text-sm">Prénom *</Label>
                  <Input
                    value={contact.first_name}
                    onChange={(e) => setContact((p) => ({ ...p, first_name: e.target.value }))}
                    required disabled={qualified}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-sm">Nom *</Label>
                  <Input
                    value={contact.last_name}
                    onChange={(e) => setContact((p) => ({ ...p, last_name: e.target.value }))}
                    required disabled={qualified}
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-sm">Email *</Label>
                <Input
                  type="email"
                  value={contact.email}
                  onChange={(e) => setContact((p) => ({ ...p, email: e.target.value }))}
                  required disabled={qualified}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-sm">Téléphone *</Label>
                <Input
                  type="tel" placeholder="+33 6 00 00 00 00"
                  value={contact.phone}
                  onChange={(e) => setContact((p) => ({ ...p, phone: e.target.value }))}
                  required disabled={qualified}
                />
              </div>

              {/* Questions — no border separator */}
              {calendar && calendar.questions.length > 0 && (
                <>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground pt-1">Questions</p>
                  {calendar.questions.map((q) => (
                    <div key={q.id} className="space-y-1">
                      <Label className="text-sm">
                        {q.label}{q.required && <span className="text-destructive"> *</span>}
                      </Label>
                      {q.type === 'text' && (
                        <Input
                          value={(answers[q.id] as string) ?? ''}
                          onChange={(e) => setAnswers((p) => ({ ...p, [q.id]: e.target.value }))}
                          required={q.required} disabled={qualified}
                        />
                      )}
                      {q.type === 'number' && (
                        <Input
                          type="number"
                          value={(answers[q.id] as string) ?? ''}
                          onChange={(e) => setAnswers((p) => ({ ...p, [q.id]: e.target.value }))}
                          required={q.required} disabled={qualified}
                        />
                      )}
                      {q.type === 'single_choice' && (
                        <div className="space-y-1">
                          {q.options?.map((opt) => (
                            <label key={opt} className="flex items-center gap-2 cursor-pointer text-sm">
                              <input
                                type="radio" name={`q_${q.id}`} value={opt}
                                checked={answers[q.id] === opt}
                                onChange={() => setAnswers((p) => ({ ...p, [q.id]: opt }))}
                                required={q.required} disabled={qualified}
                              />
                              {opt}
                            </label>
                          ))}
                        </div>
                      )}
                      {q.type === 'multiple_choice' && (
                        <div className="space-y-1">
                          {q.options?.map((opt) => (
                            <label key={opt} className="flex items-center gap-2 cursor-pointer text-sm">
                              <input
                                type="checkbox" value={opt}
                                checked={((answers[q.id] as string[]) ?? []).includes(opt)}
                                onChange={(e) => {
                                  const current = (answers[q.id] as string[]) ?? [];
                                  setAnswers((p) => ({
                                    ...p,
                                    [q.id]: e.target.checked
                                      ? [...current, opt]
                                      : current.filter((v) => v !== opt),
                                  }));
                                }}
                                disabled={qualified}
                              />
                              {opt}
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </>
              )}

              {!qualified && (
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? 'Vérification...' : 'Accéder aux créneaux'}
                </Button>
              )}

              {qualified && (
                <p className="text-center text-sm text-green-600 font-medium py-1">
                  ✓ Validé — choisissez un créneau →
                </p>
              )}
            </form>
          </div>

          {/* Right: Slots — independent scroll */}
          <div className="overflow-y-auto p-5">
            {calendar && (
              <SlotsPanel
                slug={slug}
                calendar={calendar}
                leadId={leadId}
                unlocked={qualified}
                onConfirm={handleConfirm}
              />
            )}
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">Powered by I-Opened</p>
    </div>
  );
}
