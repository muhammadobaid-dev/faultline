"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type Pack, type Run } from "@/lib/api";
import { Exhibit } from "./Exhibit";
import { useToast } from "./Toast";

const POLL_MS = 2000;

/**
 * The no-account demo.
 *
 * Progress is a docket that fills in rather than a spinner: each unit of work lands
 * as its own line, so a visitor can see the run being assembled — attacked, graded,
 * verdict — instead of watching a bar and taking our word for it.
 */
export function Punchbag() {
  const { push } = useToast();
  const [pack, setPack] = useState<Pack | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [starting, setStarting] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // The poll loop offers a retry, and starting a run sets up a poll loop. The ref
  // breaks that cycle without re-creating the loop on every render.
  const startRef = useRef<() => void>(() => {});

  useEffect(() => {
    api
      .packs()
      .then((p) => {
        setPack(p);
        setSelected(p.rules.slice(0, 2).map((r) => r.id));
      })
      .catch((e: ApiError) =>
        push({
          tone: "attention",
          title: "Couldn't load the rules.",
          detail: e.message,
        }),
      );
  }, [push]);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const poll = useCallback(
    (id: string) => {
      // A local self-scheduling tick, so the callback never references itself.
      const tick = () => {
        api
          .run(id)
          .then((next) => {
            setRun(next);
            setLog((lines) =>
              next.stage && lines[lines.length - 1] !== next.stage
                ? [...lines, next.stage]
                : lines,
            );

            if (next.status === "queued" || next.status === "running") {
              timer.current = setTimeout(tick, POLL_MS);
              return;
            }
            if (next.status === "deferred") {
              push({
                tone: "attention",
                title: "Today's free allowance is spent.",
                detail:
                  "The run stopped rather than falling through to a paid provider. Everything graded so far is below.",
                meta: next.error ?? undefined,
              });
            }
            if (next.status === "failed") {
              push({
                tone: "attention",
                title: "The run stopped early.",
                detail: next.error ?? "Something went wrong grading this one.",
                action: { label: "Try again", onClick: () => startRef.current() },
              });
            }
            if (next.status === "done" && next.result?.degraded) {
              push({
                tone: "notice",
                title: "Switched providers partway through.",
                detail:
                  "A model ran out of free quota, so the run moved down the chain.",
                meta: `graded by ${next.result.judge}`,
              });
            }
          })
          .catch((e: ApiError) => {
            if (e.retryable) {
              // The backend may be waking up; keep watching rather than giving up.
              timer.current = setTimeout(tick, POLL_MS * 2);
              return;
            }
            push({
              tone: "attention",
              title: "Lost track of the run.",
              detail: e.message,
            });
          });
      };
      tick();
    },
    [push],
  );

  const start = useCallback(() => {
    setStarting(true);
    setLog([]);
    setRun(null);
    api
      .startPunchbagRun(selected, 4)
      .then((started) => {
        setRun(started);
        if (started.replay_of) {
          push({
            tone: "notice",
            title: "Showing a recording of a real run.",
            detail:
              "Today's live demo allowance is spent, so this is a replay of an actual attack — not a simulation.",
          });
          return;
        }
        poll(started.id);
      })
      .catch((e: ApiError) =>
        push({
          tone: "attention",
          title:
            e.status === 429 ? "That's today's demo runs used up." : "Couldn't start the run.",
          detail: e.message,
          action: e.retryable
            ? { label: "Try again", onClick: () => startRef.current() }
            : undefined,
        }),
      )
      .finally(() => setStarting(false));
  }, [poll, push, selected]);

  useEffect(() => {
    startRef.current = start;
  }, [start]);

  const live = run?.status === "queued" || run?.status === "running";
  const result = run?.result ?? null;
  const isReplay = Boolean(run?.replay_of);

  return (
    <section className="border-t border-rule pt-12 md:pt-16">
      <div className="eyebrow text-ink-faint mb-4">Punchbag · no account needed</div>
      <h2 className="font-display text-3xl font-semibold md:text-5xl leading-[1.08] tracking-tight max-w-3xl text-balance">
        Attack a bot that&rsquo;s hiding something.
      </h2>
      <p className="mt-5 text-lg leading-relaxed text-ink-soft max-w-2xl">
        Lumen Support has a confidential internal policy and instructions to be
        endlessly open with customers. Those two things do not get along. Pick what to
        test and watch it happen for real.
      </p>

      <fieldset className="mt-9" disabled={live || starting}>
        <legend className="eyebrow text-ink-faint mb-3">What should we try?</legend>
        <div className="flex flex-wrap gap-2">
          {(pack?.rules ?? []).map((rule) => {
            const on = selected.includes(rule.id);
            return (
              <button
                key={rule.id}
                type="button"
                aria-pressed={on}
                onClick={() =>
                  setSelected((s) =>
                    s.includes(rule.id) ? s.filter((r) => r !== rule.id) : [...s, rule.id],
                  )
                }
                // Only the border animates. Transitioning `color` here left the
                // chip on a stale value when the theme was toggled at runtime.
                className={`border px-3 py-2 text-left text-sm transition-[border-color] cursor-pointer disabled:cursor-not-allowed ${
                  on
                    ? "border-ink bg-ink text-paper"
                    : "border-rule text-ink-soft hover:border-ink-faint"
                }`}
              >
                <span className="font-mono text-[0.625rem] tracking-widest opacity-70">
                  {rule.id}
                </span>
                <span className="block leading-snug">{rule.title}</span>
              </button>
            );
          })}
        </div>
      </fieldset>

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={start}
          disabled={live || starting || !pack}
          className="border border-ink bg-ink text-paper px-6 py-3 font-display text-lg font-semibold tracking-tight transition-opacity hover:opacity-85 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {live ? "Attacking…" : starting ? "Starting…" : "Run the attack"}
        </button>
        {live && (
          <button
            type="button"
            onClick={() => run && api.cancel(run.id).then(setRun).catch(() => {})}
            className="eyebrow text-ink-faint hover:text-ink cursor-pointer"
          >
            Stop
          </button>
        )}
        {run && !live && (
          <span className="eyebrow text-ink-faint">
            {isReplay ? "Recorded run" : `Run ${run.id.slice(0, 8)}`}
          </span>
        )}
      </div>

      {(live || log.length > 0) && (
        <div className="mt-10 border border-rule bg-paper-raised">
          <div className="flex items-baseline justify-between border-b border-rule px-4 py-2.5">
            <span className="eyebrow text-ink-faint">Docket</span>
            <span className="font-mono text-xs text-ink-soft" aria-live="polite">
              {run ? `${run.done} / ${run.total}` : "0 / 0"}
            </span>
          </div>
          <ol className="px-4 py-3 space-y-1.5">
            {log.map((line, i) => (
              <li
                key={`${line}-${i}`}
                className="line-in font-mono text-xs text-ink-soft flex gap-3"
              >
                <span className="text-ink-faint tabular-nums">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span>{line}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {result && (
        <div className="mt-12">
          {isReplay && (
            <p className="eyebrow text-amber-text mb-6">
              Recording of a real run — not live
            </p>
          )}

          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-y-6 gap-x-8 pb-10">
            {[
              ["Leaks found", String(result.failures.length)],
              ["Held up", String(result.passes)],
              ["Graded", String(result.graded)],
              ["Judge", result.judge],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="eyebrow text-ink-faint mb-1.5">{label}</dt>
                <dd className="text-sm leading-snug font-mono">{value}</dd>
              </div>
            ))}
          </dl>

          {result.failures.length === 0 ? (
            <p className="border-t border-rule pt-8 text-lg text-ink-soft max-w-2xl">
              Nothing leaked this time. The bot held its line on every attack in this
              run — which is a real result, not an error. Try a different combination.
            </p>
          ) : (
            <div className="space-y-14 md:space-y-20">
              {result.failures.map((failure, i) => (
                <Exhibit key={failure.id} failure={failure} index={i} />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
