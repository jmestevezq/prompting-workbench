interface MetricsCardProps {
  title: string
  metrics: Record<string, number | string>
}

export default function MetricsCard({ title, metrics }: MetricsCardProps) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-xs p-5">
      <h3 className="text-xs uppercase tracking-wider font-medium text-slate-500 mb-4">{title}</h3>
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(metrics).map(([key, value]) => (
          <div key={key}>
            <div className="text-[11px] text-slate-400 uppercase tracking-wider mb-0.5">{key.replace(/_/g, ' ')}</div>
            <div className="text-xl font-semibold text-slate-800 tabular-nums">
              {typeof value === 'number' ? (value < 1 && value > 0 ? `${(value * 100).toFixed(1)}%` : value.toFixed(2)) : value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
