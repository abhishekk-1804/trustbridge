import * as React from 'react';
import { create } from 'zustand';
import { cn } from '@/utils';

interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
}

const useToastStore = create<ToastState>((set) => {
  return {
    toasts: [],
    addToast: (toast) => {
      const id = Math.random().toString(36).slice(2, 9);
      set((state) => ({
        toasts: [...state.toasts, { ...toast, id }],
      }));
      return id;
    },
    removeToast: (id) => set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
  };
});

export function useToast() {
  const { toasts, addToast, removeToast } = useToastStore();

  const toast = React.useCallback(
    (options: Omit<Toast, 'id'>) => addToast(options),
    [addToast]
  );

  return { toast, toasts, removeToast };
}

interface ToastProps {
  toast: Toast;
  onClose: () => void;
}

function ToastComponent({ toast, onClose }: ToastProps) {
  React.useEffect(() => {
    if (toast.duration !== 0) {
      const timer = setTimeout(onClose, toast.duration ?? 5000);
      return () => clearTimeout(timer);
    }
  }, [toast, onClose]);

  const variants = {
    success: 'border-emerald-500/30 bg-emerald-500/5 text-emerald-300',
    error: 'border-red-500/30 bg-red-500/5 text-red-300',
    warning: 'border-amber-500/30 bg-amber-500/5 text-amber-300',
    info: 'border-blue-500/30 bg-blue-500/5 text-blue-300',
  };

  return (
    <div
      className={cn(
        'fixed bottom-4 right-4 z-50 flex items-start gap-3 w-80 animate-slide-in',
        variants[toast.variant ?? 'info'],
        'border rounded-lg p-4 shadow-xl'
      )}
      role="alert"
    >
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm">{toast.title}</p>
        {toast.description && (
          <p className="mt-1 text-xs opacity-80">{toast.description}</p>
        )}
      </div>
      <button
        onClick={onClose}
        className="flex-shrink-0 p-1 opacity-50 hover:opacity-100 transition-opacity"
        aria-label="Dismiss"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

export function Toaster() {
  const { toasts, removeToast } = useToastStore();

  return (
    <div className="pointer-events-none">
      {toasts.map((toast) => (
        <ToastComponent
          key={toast.id}
          toast={toast}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );
}