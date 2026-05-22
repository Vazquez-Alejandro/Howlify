import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";

type ToastType = "success" | "error" | "info";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface Toast {
  id: number;
  message: string;
  type: ToastType;
  action?: ToastAction;
}

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void;
  toastWithAction: (message: string, action: ToastAction, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be inside ToastProvider");
  return ctx;
}

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType = "info") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => removeToast(id), 4500);
  }, [removeToast]);

  const addToastWithAction = useCallback((message: string, action: ToastAction, type: ToastType = "info") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type, action }]);
    setTimeout(() => removeToast(id), 8000);
  }, [removeToast]);

  const colors: Record<ToastType, string> = {
    success: "border-green-500/50 bg-green-900/40 text-green-300",
    error: "border-red-500/50 bg-red-900/40 text-red-300",
    info: "border-gray-500/50 bg-gray-800/80 text-gray-300",
  };

  const icons: Record<ToastType, string> = {
    success: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    error: "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    info: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  };

  return (
    <ToastContext.Provider value={{ toast: addToast, toastWithAction: addToastWithAction }}>
      {children}
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 pointer-events-none">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              className={`pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl shadow-xl text-sm max-w-sm ${colors[t.type]}`}
            >
              <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icons[t.type]} />
              </svg>
              <div className="flex-1 min-w-0">
                <span className="block">{t.message}</span>
                {t.action && (
                  <button
                    onClick={() => { t.action!.onClick(); removeToast(t.id); }}
                    className="mt-1.5 text-xs font-semibold text-red-400 hover:text-red-300 transition-colors underline underline-offset-2"
                  >
                    {t.action.label}
                  </button>
                )}
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="ml-1 shrink-0 opacity-60 hover:opacity-100"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
