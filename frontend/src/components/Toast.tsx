import { useEffect, useState } from 'react'

interface ToastProps {
  message: string
  type?: 'success' | 'error' | 'info' | 'warning'
  duration?: number
  onClose: () => void
}

const TYPE_STYLES: Record<NonNullable<ToastProps['type']>, { bg: string; icon: string }> = {
  success: { bg: 'bg-emerald-600', icon: '✓' },
  error: { bg: 'bg-rose-600', icon: '✗' },
  info: { bg: 'bg-sky-600', icon: 'ℹ' },
  warning: { bg: 'bg-amber-600', icon: '⚠' },
}

export default function Toast({ message, type = 'success', duration = 2500, onClose }: ToastProps) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false)
      setTimeout(onClose, 200) // wait for fade-out
    }, duration)
    return () => clearTimeout(timer)
  }, [duration, onClose])

  const { bg, icon } = TYPE_STYLES[type]

  return (
    <div
      className={`flex items-center px-4 py-2 rounded-lg text-white text-sm shadow-lg transition-opacity duration-200 ${bg} ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <span className="mr-2 font-bold">{icon}</span>
      <span>{message}</span>
      <button
        onClick={() => { setVisible(false); setTimeout(onClose, 200) }}
        className="ml-3 text-white/70 hover:text-white"
        aria-label="Dismiss"
      >
        &times;
      </button>
    </div>
  )
}
