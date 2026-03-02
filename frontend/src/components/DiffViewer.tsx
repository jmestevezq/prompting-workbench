interface DiffViewerProps {
  left: string
  right: string
  leftTitle?: string
  rightTitle?: string
}

export default function DiffViewer({
  left,
  right,
  leftTitle = 'Before',
  rightTitle = 'After',
}: DiffViewerProps) {
  const leftLines = left.split('\n')
  const rightLines = right.split('\n')
  const maxLines = Math.max(leftLines.length, rightLines.length)

  return (
    <div className="grid grid-cols-2 gap-0 border border-slate-200 rounded-lg overflow-hidden text-xs font-mono shadow-xs">
      <div className="border-r border-slate-200">
        <div className="bg-slate-50 px-3 py-2 font-medium text-slate-500 border-b border-slate-200 text-[11px] uppercase tracking-wider">
          {leftTitle}
        </div>
        <div className="p-2 overflow-auto max-h-96 bg-white">
          {Array.from({ length: maxLines }, (_, i) => {
            const line = leftLines[i] ?? ''
            const otherLine = rightLines[i] ?? ''
            const changed = line !== otherLine
            return (
              <div
                key={i}
                className={`px-1 leading-5 ${changed ? 'bg-rose-50 text-rose-800' : 'text-slate-700'}`}
              >
                {line || '\u00A0'}
              </div>
            )
          })}
        </div>
      </div>
      <div>
        <div className="bg-slate-50 px-3 py-2 font-medium text-slate-500 border-b border-slate-200 text-[11px] uppercase tracking-wider">
          {rightTitle}
        </div>
        <div className="p-2 overflow-auto max-h-96 bg-white">
          {Array.from({ length: maxLines }, (_, i) => {
            const line = rightLines[i] ?? ''
            const otherLine = leftLines[i] ?? ''
            const changed = line !== otherLine
            return (
              <div
                key={i}
                className={`px-1 leading-5 ${changed ? 'bg-emerald-50 text-emerald-800' : 'text-slate-700'}`}
              >
                {line || '\u00A0'}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
