import Editor from '@monaco-editor/react'

interface JsonEditorProps {
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  height?: string
}

export default function JsonEditor({
  value,
  onChange,
  readOnly = false,
  height = '300px',
}: JsonEditorProps) {
  return (
    <Editor
      height={height}
      defaultLanguage="json"
      value={value}
      onChange={(val) => onChange?.(val ?? '')}
      options={{
        readOnly,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 12,
        lineNumbers: 'on',
        wordWrap: 'on',
        automaticLayout: true,
        tabSize: 2,
      }}
      theme="vs-dark"
    />
  )
}
