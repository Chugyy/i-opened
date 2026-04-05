import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const statusConfig: Record<string, { label: string; className: string }> = {
  // Lead statuses
  nouveau: { label: 'Nouveau', className: 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/30' },
  qualifie: { label: 'Qualifié', className: 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30' },
  non_qualifie: { label: 'Non qualifié', className: 'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30' },
  booke: { label: 'Booké', className: 'bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border-indigo-500/30' },
  no_show: { label: 'No-show', className: 'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30' },
  // Booking statuses
  confirmed: { label: 'Confirmé', className: 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30' },
  cancelled: { label: 'Annulé', className: 'bg-gray-500/20 text-gray-600 dark:text-gray-400 border-gray-500/30' },
  // Calendar statuses
  active: { label: 'Actif', className: 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30' },
  inactive: { label: 'Inactif', className: 'bg-gray-500/20 text-gray-600 dark:text-gray-400 border-gray-500/30' },
  incomplete: { label: 'Incomplet', className: 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/30' },
  // Automation/log statuses
  sent: { label: 'Envoyé', className: 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30' },
  failed: { label: 'Échoué', className: 'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30' },
  pending: { label: 'En attente', className: 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/30' },
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] ?? { label: status, className: 'bg-gray-500/20 text-gray-600 dark:text-gray-400 border-gray-500/30' };
  return (
    <Badge variant="outline" className={cn(config.className, className)}>
      {config.label}
    </Badge>
  );
}
