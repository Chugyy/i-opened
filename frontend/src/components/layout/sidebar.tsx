'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Calendar,
  Users,
  Zap,
  CalendarCheck,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/app/(admin)/layout';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/calendars', label: 'Calendriers', icon: Calendar },
  { href: '/leads', label: 'Leads', icon: Users },
  { href: '/automations', label: 'Automations', icon: Zap },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { collapsed } = useSidebar();

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r border-border bg-sidebar transition-all duration-200',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Logo */}
      <div className={cn(
        'flex h-14 items-center gap-2 border-b border-border',
        collapsed ? 'justify-center px-2' : 'px-4'
      )}>
        <CalendarCheck className="size-5 shrink-0 text-primary" />
        {!collapsed && <span className="font-semibold text-sidebar-foreground">I-Opened</span>}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className={cn('space-y-0.5', collapsed ? 'px-1.5' : 'px-2')}>
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/');
            const linkContent = (
              <Link
                href={href}
                className={cn(
                  'flex items-center rounded-md text-sm font-medium transition-colors',
                  collapsed ? 'justify-center px-2 py-2' : 'gap-2.5 px-3 py-2',
                  active
                    ? 'bg-sidebar-accent text-sidebar-primary'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                )}
              >
                <Icon className="size-4 shrink-0" />
                {!collapsed && label}
              </Link>
            );

            if (collapsed) {
              return (
                <li key={href}>
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                    <TooltipContent side="right">{label}</TooltipContent>
                  </Tooltip>
                </li>
              );
            }

            return <li key={href}>{linkContent}</li>;
          })}
        </ul>
      </nav>
    </aside>
  );
}
