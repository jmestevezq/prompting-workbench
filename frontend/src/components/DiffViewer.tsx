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
    <div className="grid grid-cols-2 gap-0 border border-gray-200 rounded overflow-hidden text-xs font-mono">
      <div className="border-r border-gray-200">
        <div className="bg-gray-100 px-3 py-1.5 font-medium text-gray-600 border-b border-gray-200">
          {leftTitle}
        </div>
        <div className="p-2 overflow-auto max-h-96">
          {Array.from({ length: maxLines }, (_, i) => {
            const line = leftLines[i] ?? ''
            const otherLine = rightLines[i] ?? ''
            const changed = line !== otherLine
            return (
              <div
                key={i}
                className={`px-1 ${changed ? 'bg-red-50 text-red-800' : ''}`}
              >
                {line || '\u00A0'}
              </div>
            )
          })}
        </div>
      </div>
      <div>
        <div className="bg-gray-100 px-3 py-1.5 font-medium text-gray-600 border-b border-gray-200">
          {rightTitle}
        </div>
        <div className="p-2 overflow-auto max-h-96">
          {Array.from({ length: maxLines }, (_, i) => {
            const line = rightLines[i] ?? ''
            const otherLine = leftLines[i] ?? ''
            const changed = line !== otherLine
            return (
              <div
                key={i}
                className={`px-1 ${changed ? 'bg-green-50 text-green-800' : ''}`}
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
