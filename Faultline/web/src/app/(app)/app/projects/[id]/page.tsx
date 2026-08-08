import Link from "next/link";
import { notFound } from "next/navigation";

import { RunPanel } from "@/components/RunPanel";
import { TrendChart } from "@/components/TrendChart";
import {
  Card,
  CardHeader,
  EmptyState,
  Eyebrow,
  Grade,
  PageTitle,
  Notice,
  SectionTitle,
  Stat,
  StatusDot,
  relativeTime,
} from "@/components/ui";
import { backend, BackendError } from "@/lib/server-api";

export const dynamic = "force-dynamic";

const STATUS_COPY: Record<string, string> = {
  done: "Completed",
  running: "Running",
  queued: "Queued",
  failed: "Stopped early",
  deferred: "Waiting on quota",
  cancelled: "Stopped by you",
};

function direction(letters: string[]): { text: string; tone: "neutral" | "warn" } | null {
  if (letters.length < 2) return null;
  const order = ["A", "B", "C", "D", "F"];
  const [previous, latest] = [letters[letters.length - 2], letters[letters.length - 1]];
  const from = order.indexOf(previous);
  const to = order.indexOf(latest);
  if (from < 0 || to < 0 || from === to) return null;
  return to > from
    ? { text: `Down from ${previous} to ${latest} since the last run.`, tone: "warn" }
    : { text: `Up from ${previous} to ${latest} since the last run.`, tone: "neutral" };
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let detail;
  try {
    detail = await backend.project(id);
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound();
    throw e;
  }

  const { project, runs, grades, trend, sizes } = detail;
  const grade = grades[0];
  const move = direction(trend.map((t) => t.letter));
  const completed = runs.filter((r) => r.status === "done");
  const latestRun = completed[0];

  return (
    <div className="space-y-12">
      <div>
        <Link href="/app" className="eyebrow text-ink-faint transition-colors hover:text-ink">
          ← Projects
        </Link>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-6">
          <div>
            <PageTitle>{project.name}</PageTitle>
            <p className="eyebrow mt-3 text-ink-faint">
              {project.ruleIds.length} rules · {project.targetModel} ·{" "}
              {completed.length} completed run{completed.length === 1 ? "" : "s"}
            </p>
          </div>
          <div className="flex items-center gap-5">
            <Grade letter={grade?.letter ?? "-"} size="lg" />
            <div className="max-w-[16rem]">
              <Eyebrow className="mb-1.5">Current grade</Eyebrow>
              <p className="text-sm leading-relaxed text-ink-soft">
                {grade
                  ? grade.failures === 0
                    ? `No rule broken across ${grade.graded} tests.`
                    : `Broke a rule in ${grade.failures} of ${grade.graded} tests.`
                  : "Run the suite to get a grade."}
              </p>
            </div>
          </div>
        </div>
      </div>

      {move && <Notice tone={move.tone}>{move.text}</Notice>}

      {project.isSimulated && (
        <Notice>
          This grade comes from your prompt running on Faultline&rsquo;s model, not
          your live deployment. Use it to find weaknesses, not to make a public claim.
        </Notice>
      )}

      <section className="space-y-5">
        <SectionTitle>Run the suite</SectionTitle>
        <RunPanel projectId={project.id} sizes={sizes} />
      </section>

      {trend.length >= 2 && (
        <section className="space-y-5">
          <SectionTitle>Safety over time</SectionTitle>
          <Card className="px-5 py-5">
            <TrendChart points={trend} />
          </Card>
        </section>
      )}

      <section className="space-y-5">
        <SectionTitle>Run history</SectionTitle>
        {runs.length === 0 ? (
          <EmptyState title="No runs yet.">
            The first run writes the attacks and pins them, so every later run asks
            your bot exactly the same questions. That is what makes a grade change
            mean something.
          </EmptyState>
        ) : (
          <Card>
            <CardHeader>
              <Eyebrow>Newest first</Eyebrow>
              <Eyebrow>{runs.length} total</Eyebrow>
            </CardHeader>
            <ul className="divide-y divide-rule">
              {runs.map((run) => (
                <li key={run.id}>
                  <Link
                    href={`/app/runs/${run.id}`}
                    className="flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3.5 transition-colors hover:bg-paper"
                  >
                    <span className="eyebrow flex min-w-[9rem] items-center gap-2 text-ink-soft">
                      <StatusDot status={run.status} />
                      {STATUS_COPY[run.status] ?? run.status}
                    </span>
                    <span className="font-mono text-xs text-ink-faint">
                      {relativeTime(run.createdAt)}
                    </span>
                    <span className="text-sm text-ink-soft">
                      {run.status === "done"
                        ? `${run.failureCount} leak${run.failureCount === 1 ? "" : "s"}`
                        : run.error
                          ? run.error
                          : `${run.done}/${run.total}`}
                    </span>
                    <span className="eyebrow ml-auto text-ink-faint">
                      {run.size}
                      {run.testSetVersion ? ` · ${run.testSetVersion.slice(0, 7)}` : ""}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </section>

      {latestRun && (
        <section className="space-y-4">
          <SectionTitle>Latest findings</SectionTitle>
          <Stat
            label="From"
            value={
              <Link href={`/app/runs/${latestRun.id}`} className="underline underline-offset-4">
                the run {relativeTime(latestRun.createdAt)}
              </Link>
            }
            hint={`${latestRun.failureCount} leak${
              latestRun.failureCount === 1 ? "" : "s"
            } found. Open it to see the exact sentence that broke each rule.`}
          />
        </section>
      )}
    </div>
  );
}
