const statusStyles: Record<string, string> = {
  pass: 'bg-emerald-50 text-emerald-700',
  fail: 'bg-rose-50 text-rose-700',
  pending: 'bg-amber-50 text-amber-700',
  running: 'bg-indigo-50 text-indigo-700',
  completed: 'bg-emerald-50 text-emerald-700',
  failed: 'bg-rose-50 text-rose-700',
  error: 'bg-rose-50 text-rose-700',
}

interface StatusBadgeProps {
  status: string
  className?: string
}

export default function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const style = statusStyles[status.toLowerCase()] ?? 'bg-slate-100 text-slate-600'
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${style} ${className}`}>
      {status}
    </span>
  )
}
