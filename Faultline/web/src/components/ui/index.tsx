import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

/**
 * The small set of primitives every screen is built from.
 *
 * Deliberately few. A tool about reliability should look like one instrument, not a
 * catalogue of components, and a short list is easier to keep consistent than a long
 * one. Everything here derives from the same tokens as Visual Replay.
 */

// -- type -------------------------------------------------------------------

export function Eyebrow({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`eyebrow text-ink-faint ${className}`}>{children}</div>;
}

export function PageTitle({ children }: { children: ReactNode }) {
  return (
    <h1 className="font-display text-3xl font-semibold md:text-4xl leading-[1.1] tracking-tight text-balance">
      {children}
    </h1>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="font-display text-xl font-semibold tracking-tight">{children}</h2>
  );
}

// -- surfaces ---------------------------------------------------------------

export function Card({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}) {
  return (
    <Tag className={`border border-rule bg-paper-raised ${className}`}>{children}</Tag>
  );
}

export function CardHeader({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-rule px-5 py-3">
      {children}
    </div>
  );
}

// -- actions ----------------------------------------------------------------

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 border px-4 py-2.5 text-sm " +
  "transition-[opacity,border-color] cursor-pointer disabled:opacity-40 " +
  "disabled:cursor-not-allowed";

const VARIANTS = {
  primary: "border-ink bg-ink text-paper hover:opacity-85",
  secondary: "border-rule text-ink hover:border-ink-faint",
  quiet: "border-transparent text-ink-soft hover:text-ink px-2",
} as const;

type Variant = keyof typeof VARIANTS;

export function Button({
  variant = "secondary",
  className = "",
  ...props
}: ComponentProps<"button"> & { variant?: Variant }) {
  return <button className={`${BUTTON_BASE} ${VARIANTS[variant]} ${className}`} {...props} />;
}

export function ButtonLink({
  variant = "secondary",
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant }) {
  return <Link className={`${BUTTON_BASE} ${VARIANTS[variant]} ${className}`} {...props} />;
}

// -- data display -----------------------------------------------------------

const GRADE_TONE: Record<string, string> = {
  A: "text-ok border-ok",
  B: "text-ok border-ok",
  C: "text-amber-text border-amber",
  D: "text-amber-text border-amber",
  F: "text-fail border-fail",
  "-": "text-ink-faint border-rule",
};

export function Grade({ letter, size = "md" }: { letter: string; size?: "sm" | "md" | "lg" }) {
  const dimensions = {
    sm: "h-7 w-7 text-sm",
    md: "h-11 w-11 text-xl",
    lg: "h-20 w-20 text-4xl",
  }[size];
  return (
    <span
      className={`inline-flex items-center justify-center border font-display ${dimensions} ${
        GRADE_TONE[letter] ?? GRADE_TONE["-"]
      }`}
      aria-label={letter === "-" ? "Not graded" : `Grade ${letter}`}
    >
      {letter}
    </span>
  );
}

const STATUS_TONE: Record<string, string> = {
  done: "bg-ok",
  running: "bg-amber",
  queued: "bg-ink-faint",
  failed: "bg-fail",
  deferred: "bg-amber",
  cancelled: "bg-ink-faint",
};

export function StatusDot({ status }: { status: string }) {
  const live = status === "running" || status === "queued";
  return (
    <span
      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
        STATUS_TONE[status] ?? "bg-ink-faint"
      } ${live ? "animate-pulse" : ""}`}
      aria-hidden
    />
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <dt className="eyebrow text-ink-faint mb-1.5">{label}</dt>
      <dd className="font-mono text-sm leading-snug">{value}</dd>
      {hint && <p className="mt-1 text-xs text-ink-faint leading-snug">{hint}</p>}
    </div>
  );
}

// -- states -----------------------------------------------------------------

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="border border-dashed border-rule px-6 py-12 text-center">
      <p className="font-display text-lg tracking-tight">{title}</p>
      <div className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-soft">
        {children}
      </div>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

export function Notice({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "warn";
  children: ReactNode;
}) {
  return (
    <p
      className={`border-l-2 py-1.5 pl-3 text-sm leading-relaxed ${
        tone === "warn" ? "border-amber text-ink" : "border-rule text-ink-soft"
      }`}
    >
      {children}
    </p>
  );
}

// -- time -------------------------------------------------------------------

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
