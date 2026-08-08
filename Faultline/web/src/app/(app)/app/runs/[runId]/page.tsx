import Link from "next/link";
import { notFound } from "next/navigation";

import { CoveragePanel } from "@/components/CoveragePanel";
import { Exhibit } from "@/components/Exhibit";
import { PatchPanel } from "@/components/PatchPanel";
import {
  Card,
  EmptyState,
  Eyebrow,
  Grade,
  Notice,
  PageTitle,
  SectionTitle,
  Stat,
} from "@/components/ui";
import { backend, BackendError } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export default async function RunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;

  let run;
  try {
    run = await backend.run(runId);
  } catch (e) {
    if (e instanceof BackendError && e.status === 404) notFound();
    throw e;
  }

  const result = run.result;
  const grade = result?.grades?.[0];
  const failures = result?.failures ?? [];

  return (
    <div className="space-y-12">
      <div>
        <Link
          href="/app"
          className="eyebrow text-ink-faint transition-colors hover:text-ink"
        >
          ← Projects
        </Link>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-6">
          <div>
            <Eyebrow className="mb-3">Run {run.id.slice(0, 8)}</Eyebrow>
            <PageTitle>
              {failures.length === 0
                ? "Nothing got through — but read on."
                : `${failures.length} way${failures.length === 1 ? "" : "s"} in.`}
            </PageTitle>
          </div>
          {grade && (
            <div className="flex items-center gap-5">
              <Grade letter={grade.letter} size="lg" />
              <p className="max-w-[16rem] text-sm leading-relaxed text-ink-soft">
                {grade.reason}
              </p>
            </div>
          )}
        </div>
      </div>

      {run.status === "deferred" && (
        <Notice tone="warn">
          This run stopped because the day&rsquo;s free model allowance ran out. It
          did not fall through to a paid provider. Everything graded before that point
          is below.
        </Notice>
      )}

      {run.status === "failed" && (
        <Notice tone="warn">{run.error ?? "This run stopped early."}</Notice>
      )}

      {result?.degraded && (
        <Notice>
          A model hit its daily cap partway through, so the run moved down the
          provider chain and finished on a different one.
        </Notice>
      )}

      {result && (
        <dl className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
          <Stat label="Leaks found" value={String(failures.length)} />
          <Stat label="Held up" value={String(result.passes)} />
          <Stat label="Graded" value={String(result.graded)} />
          <Stat
            label="Judge"
            value={result.judge}
            hint={
              result.testSetVersion
                ? `Test set ${result.testSetVersion.slice(0, 7)}`
                : undefined
            }
          />
        </dl>
      )}

      {result?.incomplete ? (
        <Notice>
          {result.incomplete} case
          {result.incomplete === 1 ? "" : "s"} could not be completed and{" "}
          {result.incomplete === 1 ? "was" : "were"} left out of the grade entirely —
          a provider problem is never counted against your bot.
        </Notice>
      ) : null}

      {result?.coverage && <CoveragePanel coverage={result.coverage} />}

      <section className="space-y-6">
        <SectionTitle>Visual Replay</SectionTitle>
        {failures.length === 0 ? (
          <EmptyState title="Nothing to replay.">
            Your bot held its line on every attack in this run. That is a real result,
            not an empty screen — the same suite will run again next time you change
            the prompt, so you will know if that stops being true.
          </EmptyState>
        ) : (
          <div className="space-y-14 md:space-y-20">
            {failures.map((failure, i) => (
              <Exhibit key={failure.id} failure={failure} index={i} />
            ))}
          </div>
        )}
      </section>

      {run.project_id && failures.length > 0 && (
        <PatchPanel projectId={run.project_id} failureCount={failures.length} />
      )}

      {result?.isSimulated && (
        <Card className="px-5 py-4">
          <Eyebrow className="mb-2">About this result</Eyebrow>
          <p className="text-sm leading-relaxed text-ink-soft">
            Your prompt was run on Faultline&rsquo;s model to stand in for your bot.
            A weaker or differently-tuned stand-in can fail attacks your real
            deployment would resist, so treat this as a pointer to a weakness rather
            than a measurement of production.
          </p>
        </Card>
      )}
    </div>
  );
}
