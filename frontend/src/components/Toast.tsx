import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastProps {
  message: string;
  type?: ToastType;
  duration?: number;
  onClose?: () => void;
}

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertCircle,
  info: Info,
};

const colorMap = {
  success: 'bg-[#dcfce7] border-[#bbf7d0] text-[#166534]',
  error: 'bg-[#fee2e2] border-[#fecaca] text-[#991b1b]',
  warning: 'bg-[#fefce8] border-[#fef08a] text-[#854d0e]',
  info: 'bg-[#e8f0fe] border-[#bfdbfe] text-[#1e40af]',
};

const iconColorMap = {
  success: 'text-[#22c55e]',
  error: 'text-[#ef4444]',
  warning: 'text-[#f59e0b]',
  info: 'text-[#165DFF]',
};

export function Toast({ message, type = 'info', duration = 3000, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      onClose?.();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const Icon = iconMap[type];

  return (
    <div
      className={`
        fixed top-4 right-4 z-50 
        flex items-center gap-3 px-4 py-2.5 
        bg-white border rounded-lg 
        shadow-md
        transform transition-all duration-200
        ${isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        ${colorMap[type]}
      `}
    >
      <Icon className={`w-4 h-4 ${iconColorMap[type]}`} />
      <span className="text-sm font-medium">{message}</span>
      <button
        onClick={() => {
          setIsVisible(false);
          onClose?.();
        }}
        className="ml-2 p-1 hover:bg-black/5 rounded-lg transition-all duration-200"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

// Toast Manager for multiple toasts
interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface ToastManagerProps {
  toasts: ToastItem[];
  removeToast: (id: string) => void;
}

export function ToastManager({ toasts, removeToast }: ToastManagerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          duration={toast.duration}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );
}
