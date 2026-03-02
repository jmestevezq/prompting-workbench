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

function Spinner() {
  return (
    <svg
      className="animate-spin mr-1 h-3 w-3 inline-block"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  )
}

export default function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const style = statusStyles[status.toLowerCase()] ?? 'bg-slate-100 text-slate-600'
  const isRunning = status.toLowerCase() === 'running'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style} ${className}`}>
      {isRunning && <Spinner />}
      {status}
    </span>
  )
}
