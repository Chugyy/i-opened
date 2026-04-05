'use client';

import { usePathname, useRouter } from 'next/navigation';
import { Moon, Sun, User, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { clearTokens } from '@/lib/auth';
import { useSidebar } from '@/app/(admin)/layout';

const breadcrumbMap: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/calendars': 'Calendriers',
  '/leads': 'Leads',
  '/automations': 'Automations',
  '/settings': 'Paramètres',
};

function useBreadcrumb(pathname: string): string {
  for (const [prefix, label] of Object.entries(breadcrumbMap)) {
    if (pathname === prefix || pathname.startsWith(prefix + '/')) return label;
  }
  return '';
}

export function Header() {
  const pathname = usePathname();
  const breadcrumb = useBreadcrumb(pathname);
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const { collapsed, toggle } = useSidebar();

  function handleLogout() {
    clearTokens();
    router.push('/login');
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-6">
      <Button variant="ghost" size="icon-sm" onClick={toggle}>
        {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
      </Button>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          <Sun className="size-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute size-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Basculer le thème</span>
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <User className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push('/settings')}>
              Paramètres
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleLogout} className="text-destructive">
              Déconnexion
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
