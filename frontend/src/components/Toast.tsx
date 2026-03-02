import { useEffect, useState } from 'react'

interface ToastProps {
  message: string
  type?: 'success' | 'error'
  duration?: number
  onClose: () => void
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

  const bg = type === 'success' ? 'bg-emerald-600' : 'bg-rose-600'

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 flex items-center px-4 py-2 rounded-lg text-white text-sm shadow-lg transition-opacity duration-200 ${bg} ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
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
