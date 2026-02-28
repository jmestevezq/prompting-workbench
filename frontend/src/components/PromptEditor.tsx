import Editor from '@monaco-editor/react'

interface PromptEditorProps {
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  height?: string
  language?: string
}

export default function PromptEditor({
  value,
  onChange,
  readOnly = false,
  height = '300px',
  language = 'markdown',
}: PromptEditorProps) {
  return (
    <Editor
      height={height}
      defaultLanguage={language}
      value={value}
      onChange={(val) => onChange?.(val ?? '')}
      options={{
        readOnly,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 13,
        lineNumbers: 'off',
        wordWrap: 'on',
        automaticLayout: true,
        padding: { top: 8 },
      }}
      theme="vs-dark"
    />
  )
}
