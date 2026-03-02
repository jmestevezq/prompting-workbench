import Editor, { type Monaco } from '@monaco-editor/react'
import { monacoLightTheme, MONACO_THEME_NAME } from '../lib/theme'

interface JsonEditorProps {
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  height?: string
  language?: string
  label?: string
}

export default function JsonEditor({
  value,
  onChange,
  readOnly = false,
  height = '300px',
  language = 'json',
  label,
}: JsonEditorProps) {
  const handleBeforeMount = (monaco: Monaco) => {
    monaco.editor.defineTheme(MONACO_THEME_NAME, monacoLightTheme)
  }

  return (
    <div className="rounded-lg border border-slate-200 overflow-hidden">
      {label && (
        <div className="bg-slate-50 px-3 py-1.5 border-b border-slate-200 text-xs font-medium text-slate-500">
          {label}
        </div>
      )}
      <Editor
        height={height}
        defaultLanguage={language}
        value={value}
        onChange={(val) => onChange?.(val ?? '')}
        beforeMount={handleBeforeMount}
        options={{
          readOnly,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          fontSize: 12,
          fontFamily: "'JetBrains Mono Variable', monospace",
          lineNumbers: 'on',
          wordWrap: 'on',
          automaticLayout: true,
          tabSize: 2,
          renderLineHighlight: 'line',
        }}
        theme={MONACO_THEME_NAME}
      />
    </div>
  )
}
