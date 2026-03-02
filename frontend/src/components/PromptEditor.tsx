import Editor, { type Monaco } from '@monaco-editor/react'
import { monacoLightTheme, MONACO_THEME_NAME } from '../lib/theme'

interface PromptEditorProps {
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  height?: string
  language?: string
  label?: string
}

export default function PromptEditor({
  value,
  onChange,
  readOnly = false,
  height = '300px',
  language = 'markdown',
  label,
}: PromptEditorProps) {
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
          fontSize: 13,
          fontFamily: "'JetBrains Mono Variable', monospace",
          lineNumbers: 'off',
          wordWrap: 'on',
          automaticLayout: true,
          padding: { top: 8 },
          renderLineHighlight: 'none',
          quickSuggestions: false,
          suggestOnTriggerCharacters: false,
          wordBasedSuggestions: 'off',
          parameterHints: { enabled: false },
        }}
        theme={MONACO_THEME_NAME}
      />
    </div>
  )
}
