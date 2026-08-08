"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

/**
 * Hand-rolled rather than pulling in a toast library.
 *
 * The standing plan named Sonner, but this is ~90 lines, carries no dependency, and
 * matches the locked system exactly instead of being restyled into it. A tool about
 * reliability should not look flaky when a provider hiccups, and the two tones here
 * carry real meaning: a calm notice for a failover the user does not need to act on,
 * and a warmer one for something that stopped.
 */

export type ToastTone = "notice" | "attention";

export type Toast = {
  id: number;
  tone: ToastTone;
  title: string;
  detail?: string;
  /** Technical context - provider names, model ids. Set in mono, kept quiet. */
  meta?: string;
  action?: { label: string; onClick: () => void };
};

type ToastInput = Omit<Toast, "id">;

const ToastContext = createContext<{ push: (t: ToastInput) => void } | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}

const DISMISS_AFTER = { notice: 4500, attention: 0 } as const;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((input: ToastInput) => {
    const id = nextId.current++;
    setToasts((current) => [...current.slice(-2), { ...input, id }]);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        // polite, not assertive: a failover is information, not an interruption
        aria-live="polite"
        className="fixed bottom-0 right-0 z-50 flex flex-col items-end gap-2 p-4 sm:p-6 pointer-events-none"
      >
        {toasts.map((toast) => (
          <ToastCard key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastCard({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: (id: number) => void;
}) {
  const attention = toast.tone === "attention";

  useEffect(() => {
    const after = DISMISS_AFTER[toast.tone];
    if (!after) return;
    const timer = setTimeout(() => onDismiss(toast.id), after);
    return () => clearTimeout(timer);
  }, [toast.id, toast.tone, onDismiss]);

  return (
    <div
      role={attention ? "alert" : "status"}
      className={`toast-in pointer-events-auto w-[min(22rem,calc(100vw-2rem))] border bg-paper-raised px-4 py-3 ${
        attention ? "border-l-2 border-l-amber border-rule" : "border-rule"
      }`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span
          className={`eyebrow ${attention ? "text-amber-text" : "text-ink-faint"}`}
        >
          {attention ? "Attention" : "Notice"}
        </span>
        <button
          type="button"
          onClick={() => onDismiss(toast.id)}
          aria-label="Dismiss"
          className="eyebrow text-ink-faint hover:text-ink cursor-pointer"
        >
          Close
        </button>
      </div>

      <p className="mt-1.5 text-sm leading-snug">{toast.title}</p>
      {toast.detail && (
        <p className="mt-1 text-sm leading-snug text-ink-soft">{toast.detail}</p>
      )}
      {toast.meta && (
        <p className="mt-1.5 font-mono text-[0.6875rem] leading-snug text-ink-faint break-all">
          {toast.meta}
        </p>
      )}
      {toast.action && (
        <button
          type="button"
          onClick={() => {
            toast.action?.onClick();
            onDismiss(toast.id);
          }}
          className="eyebrow mt-3 text-amber-text underline underline-offset-4 hover:no-underline cursor-pointer"
        >
          {toast.action.label}
        </button>
      )}
    </div>
  );
}
