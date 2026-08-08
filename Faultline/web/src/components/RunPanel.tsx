"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button, Eyebrow, StatusDot } from "@/components/ui";
import { useToast } from "@/components/Toast";

const POLL_MS = 2500;

type LiveRun = {
  id: string;
  status: string;
  stage: string;
  done: number;
  total: number;
  percent: number;
  error: string | null;
};

/**
 * Starting a run and watching it.
 *
 * Progress is a docket that fills in line by line rather than a bar, because a bar
 * says "wait" and a docket says what is happening. When the run finishes the page
 * refreshes so the server-rendered grade, trend and history all update together.
 */
export function RunPanel({
  projectId,
  sizes,
}: {
  projectId: string;
  sizes: { smoke: number; full: number };
}) {
  const router = useRouter();
  const { push } = useToast();
  const [run, setRun] = useState<LiveRun | null>(null);
  const [starting, setStarting] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const poll = useCallback(
    (id: string) => {
      const tick = () => {
        fetch(`/api/faultline/runs/${id}`, { cache: "no-store" })
          .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
          .then((next: LiveRun) => {
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
                title: "Today's free model allowance is spent.",
                detail:
                  "The run stopped rather than falling through to a paid provider. It resets at midnight Pacific.",
              });
            } else if (next.status === "failed") {
              push({
                tone: "attention",
                title: "That run stopped early.",
                detail: next.error ?? "Something went wrong partway through.",
              });
            } else if (next.status === "done") {
              push({ tone: "notice", title: "Run finished. Results are below." });
            }
            router.refresh();
          })
          .catch(() => {
            // The backend may be waking up; keep watching rather than giving up.
            timer.current = setTimeout(tick, POLL_MS * 2);
          });
      };
      tick();
    },
    [push, router],
  );

  const start = useCallback(
    async (size: "smoke" | "full") => {
      setStarting(true);
      setLog([]);
      setRun(null);
      try {
        const response = await fetch(`/api/faultline/projects/${projectId}/runs`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ size }),
        });
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw new Error(body?.detail ?? "Could not start the run.");
        }
        const started: LiveRun = await response.json();
        setRun(started);
        poll(started.id);
      } catch (e) {
        push({
          tone: "attention",
          title: "Couldn't start that run.",
          detail: e instanceof Error ? e.message : "Try again in a moment.",
        });
      } finally {
        setStarting(false);
      }
    },
    [poll, projectId, push],
  );

  const live = run?.status === "queued" || run?.status === "running";

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="primary"
          disabled={live || starting}
          onClick={() => start("smoke")}
        >
          {live ? "Running…" : `Run ${sizes.smoke} tests`}
        </Button>
        <Button
          disabled={live || starting}
          onClick={() => start("full")}
          title="A deeper sweep. Costs more of the daily free allowance."
        >
          Full audit · {sizes.full}
        </Button>
        {live && run && (
          <button
            type="button"
            onClick={() =>
              fetch(`/api/faultline/runs/${run.id}/cancel`, { method: "POST" }).catch(
                () => {},
              )
            }
            className="eyebrow cursor-pointer text-ink-faint transition-colors hover:text-ink"
          >
            Stop
          </button>
        )}
      </div>

      {(live || log.length > 0) && (
        <div className="border border-rule bg-paper-raised">
          <div className="flex items-baseline justify-between border-b border-rule px-4 py-2.5">
            <span className="eyebrow flex items-center gap-2 text-ink-faint">
              <StatusDot status={run?.status ?? "queued"} />
              {run?.status === "running" ? "In progress" : run?.status ?? "Queued"}
            </span>
            <span className="font-mono text-xs text-ink-soft" aria-live="polite">
              {run ? `${run.done} / ${run.total}` : "0 / 0"}
            </span>
          </div>
          <ol className="max-h-56 space-y-1.5 overflow-y-auto px-4 py-3">
            {log.map((line, i) => (
              <li
                key={`${line}-${i}`}
                className="line-in flex gap-3 font-mono text-xs text-ink-soft"
              >
                <span className="tabular-nums text-ink-faint">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span>{line}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {!live && log.length === 0 && (
        <Eyebrow>
          A short run costs {sizes.smoke * 2} model requests. Six runs a day per
          account.
        </Eyebrow>
      )}
    </div>
  );
}
