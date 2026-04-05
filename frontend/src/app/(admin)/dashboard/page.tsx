'use client';

import { useQuery } from '@tanstack/react-query';
import { CalendarDays, Users, TrendingUp, Clock } from 'lucide-react';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { PageHeader } from '@/components/shared/page-header';
import { StatusBadge } from '@/components/shared/status-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface DashboardData {
  bookingsToday: number;
  leadsThisWeek: number;
  qualificationRate: number;
  upcomingBookings: Array<{
    bookingId: string;
    leadId: string;
    leadName: string;
    calendarName: string;
    startsAt: string;
  }>;
}

function KpiCard({
  label,
  value,
  icon: Icon,
  suffix,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  suffix?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-1 text-3xl font-bold">
            {value}
            {suffix && <span className="ml-0.5 text-lg">{suffix}</span>}
          </p>
        </div>
        <div className="rounded-full bg-primary/10 p-3">
          <Icon className="size-5 text-primary" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { data, isLoading, error } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/api/dashboard'),
  });

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Dashboard" />
        <p className="text-sm text-destructive">Erreur lors du chargement du dashboard.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
      />

      {/* KPI Grid */}
      <div className="grid gap-4 sm:grid-cols-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardContent>
                <Skeleton className="mb-2 h-4 w-32" />
                <Skeleton className="h-9 w-16" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <KpiCard label="RDV aujourd'hui" value={data?.bookingsToday ?? 0} icon={CalendarDays} />
            <KpiCard label="Leads cette semaine" value={data?.leadsThisWeek ?? 0} icon={Users} />
            <KpiCard
              label="Taux de qualification"
              value={Math.round(data?.qualificationRate ?? 0)}
              icon={TrendingUp}
              suffix="%"
            />
          </>
        )}
      </div>

      {/* Upcoming bookings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Prochains RDV</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !data?.upcomingBookings?.length ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <Clock className="size-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Aucun RDV à venir</p>
              <Link href="/calendars">
                <Button size="sm" variant="outline">
                  Configurer un calendrier
                </Button>
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Lead</TableHead>
                  <TableHead>Calendrier</TableHead>
                  <TableHead>Date & heure</TableHead>
                  <TableHead>Statut</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.upcomingBookings.map((b) => (
                  <TableRow key={b.bookingId} className="cursor-pointer hover:bg-muted/50" onClick={() => router.push(`/leads/${b.leadId}`)}>
                    <TableCell className="font-medium">{b.leadName}</TableCell>
                    <TableCell className="text-muted-foreground">{b.calendarName}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {format(new Date(b.startsAt), 'dd MMM yyyy HH:mm', { locale: fr })}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status="confirmed" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
