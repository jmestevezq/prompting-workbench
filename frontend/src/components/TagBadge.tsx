interface TagBadgeProps {
  tag: string
  label?: string // 'P' | 'N' | undefined
}

export default function TagBadge({ tag, label }: TagBadgeProps) {
  return (
    <span className="inline-flex items-center gap-0">
      <span className={`text-xs rounded px-1.5 py-0.5 bg-indigo-50 text-indigo-600 ${label ? 'rounded-r-none' : ''}`}>
        {tag}
      </span>
      {label === 'P' && (
        <span className="text-xs font-semibold rounded-r px-1 py-0.5 bg-emerald-100 text-emerald-700">
          P
        </span>
      )}
      {label === 'N' && (
        <span className="text-xs font-semibold rounded-r px-1 py-0.5 bg-rose-100 text-rose-700">
          N
        </span>
      )}
    </span>
  )
}
