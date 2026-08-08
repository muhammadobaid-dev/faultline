"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Button, Card, Eyebrow, SectionTitle, StatusDot } from "@/components/ui";
import { useToast } from "@/components/Toast";

const POLL_MS = 2500;

type PatchResult = {
  kind: "patch";
  verdict: string;
  improved: boolean;
  closed: number;
  beforeFailures: number;
  afterFailures: number;
  graded: number;
  summary: string;
  changes: { what: string; why: string }[];
  patchedPrompt: string;
  originalPrompt: string;
  stillFailing: { id: string; ruleId: string; rationale: string }[];
  newlyFailing: { id: string; ruleId: string; rationale: string }[];
};

type PatchRun = {
  id: string;
  status: string;
  stage: string;
  done: number;
  total: number;
  result: PatchResult | null;
  error: string | null;
};

/**
 * Propose a fix and prove it.
 *
 * The value is not the suggestion - anyone can ask a model to harden a prompt. It is
 * that the patched prompt is re-tested against the *same pinned attacks*, so what the
 * developer reads is a before-and-after on identical questions rather than a claim.
 */
export function PatchPanel({
  projectId,
  failureCount,
}: {
  projectId: string;
  failureCount: number;
}) {
  const { push } = useToast();
  const [run, setRun] = useState<PatchRun | null>(null);
  const [starting, setStarting] = useState(false);
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const poll = useCallback(
    (id: string) => {
      const tick = () => {
        fetch(`/api/faultline/runs/${id}`, { cache: "no-store" })
          .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
          .then((next: PatchRun) => {
            setRun(next);
            if (next.status === "queued" || next.status === "running") {
              timer.current = setTimeout(tick, POLL_MS);
              return;
            }
            if (next.status === "done") {
              push({ tone: "notice", title: "Patch tested against the same attacks." });
            } else {
              push({
                tone: "attention",
                title: "Couldn't finish testing the patch.",
                detail: next.error ?? "Try again shortly.",
              });
            }
          })
          .catch(() => {
            timer.current = setTimeout(tick, POLL_MS * 2);
          });
      };
      tick();
    },
    [push],
  );

  const start = useCallback(async () => {
    setStarting(true);
    try {
      const response = await fetch(`/api/faultline/projects/${projectId}/patch`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Could not start.");
      }
      const started: PatchRun = await response.json();
      setRun(started);
      poll(started.id);
    } catch (e) {
      push({
        tone: "attention",
        title: "Couldn't propose a fix.",
        detail: e instanceof Error ? e.message : "Try again in a moment.",
      });
    } finally {
      setStarting(false);
    }
  }, [poll, projectId, push]);

  const live = run?.status === "queued" || run?.status === "running";
  const result = run?.result ?? null;

  if (failureCount === 0) return null;

  return (
    <section className="space-y-5">
      <SectionTitle>Fix it</SectionTitle>
      <p className="max-w-2xl text-base leading-relaxed text-ink-soft">
        Faultline can rewrite your system prompt to close these leaks, then re-run the
        exact same attacks against the rewrite. You get a before-and-after on identical
        questions — not a suggestion you have to go and verify yourself.
      </p>

      {!result && (
        <div className="flex flex-wrap items-center gap-4">
          <Button variant="primary" onClick={start} disabled={live || starting}>
            {live ? "Testing the patch…" : starting ? "Starting…" : "Propose a fix"}
          </Button>
          {live && run && (
            <span className="eyebrow flex items-center gap-2 text-ink-faint">
              <StatusDot status={run.status} />
              {run.stage} · {run.done}/{run.total}
            </span>
          )}
          {!live && !starting && (
            <span className="text-xs text-ink-faint">
              Costs one run from today&rsquo;s allowance.
            </span>
          )}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <Card className="px-5 py-5">
            <div className="flex flex-wrap items-baseline justify-between gap-4">
              <p
                className={`font-display text-xl tracking-tight ${
                  result.improved ? "text-ok" : "text-amber-text"
                }`}
              >
                {result.verdict}
              </p>
              <span className="eyebrow text-ink-faint">
                same {result.graded} attacks, re-run
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink-soft">
              {result.summary}
            </p>

            <dl className="mt-5 grid grid-cols-3 gap-6 border-t border-rule pt-5">
              <div>
                <dt className="eyebrow mb-1 text-ink-faint">Before</dt>
                <dd className="font-mono text-lg">{result.beforeFailures}</dd>
              </div>
              <div>
                <dt className="eyebrow mb-1 text-ink-faint">After</dt>
                <dd className={`font-mono text-lg ${result.improved ? "text-ok" : ""}`}>
                  {result.afterFailures}
                </dd>
              </div>
              <div>
                <dt className="eyebrow mb-1 text-ink-faint">Closed</dt>
                <dd className="font-mono text-lg">{result.closed}</dd>
              </div>
            </dl>
          </Card>

          {result.changes.length > 0 && (
            <div className="space-y-3">
              <Eyebrow>What changed</Eyebrow>
              <ul className="space-y-3">
                {result.changes.map((change, i) => (
                  <li key={i} className="border-l-2 border-amber pl-4">
                    <p className="text-sm leading-relaxed">{change.what}</p>
                    <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                      {change.why}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.newlyFailing.length > 0 && (
            <div className="space-y-2">
              <Eyebrow className="text-amber-text">
                The patch opened something new
              </Eyebrow>
              <ul className="space-y-1.5">
                {result.newlyFailing.map((f) => (
                  <li key={f.id} className="text-sm leading-relaxed text-ink-soft">
                    <span className="font-mono text-xs">{f.ruleId}</span> — {f.rationale}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-3">
            <div className="flex items-baseline justify-between gap-4">
              <Eyebrow>The patched prompt</Eyebrow>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard?.writeText(result.patchedPrompt);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="eyebrow cursor-pointer text-ink-faint transition-colors hover:text-ink"
              >
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap border border-rule bg-paper-raised px-4 py-3 font-mono text-xs leading-relaxed">
              {result.patchedPrompt}
            </pre>
            <p className="text-xs leading-relaxed text-ink-faint">
              Faultline never edits your project. Read it, diff it, and paste it in
              yourself if you agree — a tool that rewrites the thing it grades
              can&rsquo;t honestly grade it.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
