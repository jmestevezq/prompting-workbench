const statusStyles: Record<string, string> = {
  pass: 'bg-green-100 text-green-700',
  fail: 'bg-red-100 text-red-700',
  pending: 'bg-yellow-100 text-yellow-700',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  error: 'bg-red-100 text-red-700',
}

interface StatusBadgeProps {
  status: string
  className?: string
}

export default function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const style = statusStyles[status.toLowerCase()] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${style} ${className}`}>
      {status}
    </span>
  )
}
