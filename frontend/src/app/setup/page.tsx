'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { CalendarCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { setTokens } from '@/lib/auth';
import api, { ApiError } from '@/lib/api';

interface TokenResponse {
  accessToken: string;
  refreshToken: string;
}

export default function SetupPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirm) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }

    setLoading(true);
    try {
      const data = await api.post<TokenResponse>('/api/auth/setup', {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
      });
      setTokens(data.accessToken, data.refreshToken);
      router.push('/dashboard');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          router.push('/login');
          return;
        }
        setError(err.message || 'Erreur lors de la création du compte');
      } else {
        setError('Impossible de se connecter au serveur');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-2">
            <CalendarCheck className="size-7 text-primary" />
            <span className="text-2xl font-bold">I-Opened</span>
          </div>
          <p className="text-sm text-muted-foreground">Créez votre compte administrateur</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Configuration initiale</CardTitle>
            <CardDescription>Ce compte sera le seul administrateur de la plateforme</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="full_name">Nom complet</Label>
                <Input
                  id="full_name"
                  placeholder="Jean Dupont"
                  value={form.full_name}
                  onChange={(e) => update('full_name', e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@exemple.com"
                  value={form.email}
                  onChange={(e) => update('email', e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Mot de passe</Label>
                <Input
                  id="password"
                  type="password"
                  value={form.password}
                  onChange={(e) => update('password', e.target.value)}
                  required
                  minLength={8}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm">Confirmer le mot de passe</Label>
                <Input
                  id="confirm"
                  type="password"
                  value={form.confirm}
                  onChange={(e) => update('confirm', e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Création...' : 'Créer le compte'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
