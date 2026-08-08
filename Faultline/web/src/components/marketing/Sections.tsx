import type { ReactNode } from "react";

/** Shared furniture for the marketing page. */

export function Section({
  id,
  eyebrow,
  title,
  lede,
  children,
}: {
  id?: string;
  eyebrow?: string;
  title: string;
  lede?: string;
  children?: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 border-t border-rule pt-16 md:pt-24">
      {eyebrow && <div className="eyebrow mb-5 text-ink-faint">{eyebrow}</div>}
      <h2 className="max-w-3xl text-balance font-display text-3xl font-semibold leading-[1.1] tracking-tight md:text-[2.65rem]">
        {title}
      </h2>
      {lede && (
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-ink-soft">{lede}</p>
      )}
      {children && <div className="mt-10">{children}</div>}
    </section>
  );
}

export function Steps({
  steps,
}: {
  steps: { title: string; body: string; note?: string }[];
}) {
  return (
    <ol className="grid gap-0 border-t border-rule md:grid-cols-2">
      {steps.map((step, i) => (
        <li
          key={step.title}
          className="border-b border-rule p-6 md:odd:border-r md:p-8"
        >
          <div className="eyebrow mb-4 text-ink-faint">
            Step {String(i + 1).padStart(2, "0")}
          </div>
          <h3 className="font-display text-xl font-semibold tracking-tight">
            {step.title}
          </h3>
          <p className="mt-3 text-[0.9375rem] leading-relaxed text-ink-soft">
            {step.body}
          </p>
          {step.note && (
            <p className="mt-4 border-l-2 border-amber pl-3 font-mono text-xs leading-relaxed text-ink-faint">
              {step.note}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}

export function Faq({ items }: { items: { q: string; a: ReactNode }[] }) {
  return (
    <div className="divide-y divide-rule border-y border-rule">
      {items.map((item) => (
        <details key={item.q} className="group">
          <summary className="flex cursor-pointer list-none items-baseline justify-between gap-6 py-5 text-left">
            <span className="font-display text-lg font-semibold leading-snug tracking-tight">
              {item.q}
            </span>
            <span
              aria-hidden
              className="eyebrow shrink-0 text-ink-faint transition-transform group-open:rotate-45"
            >
              +
            </span>
          </summary>
          <div className="max-w-2xl pb-6 text-[0.9375rem] leading-relaxed text-ink-soft">
            {item.a}
          </div>
        </details>
      ))}
    </div>
  );
}

export function Architecture() {
  const rows = [
    ["Frontend", "Next.js on Vercel", "App router, server components, no client state library"],
    ["API + worker", "FastAPI on Render", "Runs outlive requests; the queue survives a restart"],
    ["Data", "Postgres on Neon", "Projects, pinned test sets, runs, grades — one database"],
    ["Queue", "FOR UPDATE SKIP LOCKED", "The run row is the source of truth, leases reclaim dead work"],
    ["Models", "Gemini, with failover", "Eight free rungs before anything paid is reachable"],
  ];
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] border-collapse text-left">
        <thead>
          <tr className="border-b border-rule">
            <th className="eyebrow py-3 pr-6 font-normal text-ink-faint">Layer</th>
            <th className="eyebrow py-3 pr-6 font-normal text-ink-faint">Runs on</th>
            <th className="eyebrow py-3 font-normal text-ink-faint">Why</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([layer, runs, why]) => (
            <tr key={layer} className="border-b border-rule last:border-0">
              <td className="py-3.5 pr-6 align-top text-sm font-medium">{layer}</td>
              <td className="py-3.5 pr-6 align-top font-mono text-xs text-ink-soft">
                {runs}
              </td>
              <td className="py-3.5 align-top text-sm leading-relaxed text-ink-soft">
                {why}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
