interface MetricsCardProps {
  title: string
  metrics: Record<string, number | string>
}

export default function MetricsCard({ title, metrics }: MetricsCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-medium text-gray-600 mb-3">{title}</h3>
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(metrics).map(([key, value]) => (
          <div key={key}>
            <div className="text-xs text-gray-500 uppercase tracking-wider">{key.replace(/_/g, ' ')}</div>
            <div className="text-lg font-semibold text-gray-800">
              {typeof value === 'number' ? (value < 1 && value > 0 ? `${(value * 100).toFixed(1)}%` : value.toFixed(2)) : value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
