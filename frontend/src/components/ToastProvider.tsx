import { createContext, useCallback, useContext, useState } from 'react'
import Toast from './Toast'

interface ToastItem {
  id: string
  message: string
  type: 'success' | 'error' | 'info' | 'warning'
  duration: number
}

interface ToastContextValue {
  addToast: (message: string, type?: ToastItem['type'], duration?: number) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const DEFAULT_DURATION: Record<ToastItem['type'], number> = {
  success: 3000,
  info: 3000,
  error: 5000,
  warning: 5000,
}

const MAX_TOASTS = 4

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback((message: string, type: ToastItem['type'] = 'success', duration?: number) => {
    const id = Math.random().toString(36).slice(2)
    const resolvedDuration = duration ?? DEFAULT_DURATION[type]
    setToasts((prev) => {
      const next = [...prev, { id, message, type, duration: resolvedDuration }]
      // Remove oldest if over max
      return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next
    })
  }, [])

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end pointer-events-none">
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto">
            <Toast
              message={t.message}
              type={t.type}
              duration={t.duration}
              onClose={() => removeToast(t.id)}
            />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
