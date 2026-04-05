'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { PageHeader } from '@/components/shared/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';

interface UserProfile {
  id: number;
  full_name: string;
  email: string;
  notifications_enabled?: boolean;
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [notif, setNotif] = useState(true);

  const { data: user, isLoading } = useQuery<UserProfile>({
    queryKey: ['me'],
    queryFn: () => api.get('/api/auth/me'),
    select: (data) => {
      if (!name) setName(data.full_name);
      if (data.notifications_enabled !== undefined) setNotif(data.notifications_enabled);
      return data;
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: object) => api.patch('/api/auth/me', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] });
      toast.success('Profil mis à jour');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Paramètres" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Paramètres" />

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profil</CardTitle>
          <CardDescription>Vos informations personnelles</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Nom complet</Label>
            <Input
              value={name || user?.full_name || ''}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Email</Label>
            <Input value={user?.email ?? ''} disabled className="opacity-60" />
            <p className="text-xs text-muted-foreground">L'email ne peut pas être modifié</p>
          </div>
          {name !== (user?.full_name ?? '') && (
            <Button
              onClick={() => updateMutation.mutate({ full_name: name })}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? 'Sauvegarde...' : 'Sauvegarder le profil'}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Notifications</CardTitle>
          <CardDescription>Préférences d'email</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Email à chaque nouveau booking</p>
              <p className="text-xs text-muted-foreground">Recevez un email dès qu'un RDV est confirmé</p>
            </div>
            <Switch checked={notif} onCheckedChange={setNotif} />
          </div>
          {notif !== (user?.notifications_enabled ?? true) && (
            <Button
              onClick={() => updateMutation.mutate({ notifications_enabled: notif })}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? 'Sauvegarde...' : 'Sauvegarder les préférences'}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Integrations */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Intégrations</CardTitle>
          <CardDescription>Statut des services connectés</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { name: 'Google Calendar', status: 'Non connecté' },
            { name: 'Email (SMTP)', status: 'Configuré via config/email.json' },
            { name: 'WhatsApp (Unipile)', status: 'Configuré via config/whatsapp.json' },
          ].map((int) => (
            <div key={int.name} className="flex items-center justify-between py-1">
              <span className="text-sm font-medium">{int.name}</span>
              <span className="text-xs text-muted-foreground">{int.status}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
