import { Card, Eyebrow, SectionTitle } from "@/components/ui";

export type Coverage = {
  headline: string;
  confidence: "low" | "moderate" | "high";
  caveat: string | null;
  nextStep: string | null;
  familiesCovered: number;
  familiesKnown: number;
  exercised: Record<string, number>;
  untested: string[];
  tier: number;
  tierLabel: string;
};

const FAMILY_LABELS: Record<string, string> = {
  direct: "Asking outright",
  authority: "Claiming authority",
  roleplay: "Fiction and roleplay",
  override: "Instruction override",
  encoding: "Encoding and translation",
  format: "Format tricks",
  hypothetical: "Hypothetical framing",
  false_premise: "False premises",
  incremental: "Incremental probing",
  social: "Social pressure",
};

const CONFIDENCE_TONE = {
  low: "text-amber-text border-amber",
  moderate: "text-ink border-rule",
  high: "text-ok border-ok",
} as const;

/**
 * What the run actually covered, and what that is worth.
 *
 * This exists because "24 of 24 passed" is the moment a security tool is most
 * likely to mislead. The grade is a claim about the assistant; this is a claim about
 * the assessment, and keeping them visibly separate is the whole point.
 */
export function CoveragePanel({ coverage }: { coverage: Coverage }) {
  const covered = Object.entries(coverage.exercised).filter(([, n]) => n > 0);

  return (
    <section className="space-y-5">
      <SectionTitle>How much this is worth</SectionTitle>

      <Card className="px-5 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <p className="max-w-xl font-display text-xl leading-snug tracking-tight">
            {coverage.headline}
          </p>
          <span
            className={`eyebrow shrink-0 border px-2.5 py-1 ${
              CONFIDENCE_TONE[coverage.confidence]
            }`}
          >
            {coverage.confidence} confidence
          </span>
        </div>

        {coverage.caveat && (
          <p className="mt-4 border-l-2 border-amber pl-3 text-sm leading-relaxed">
            {coverage.caveat}
          </p>
        )}

        <dl className="mt-5 grid grid-cols-2 gap-6 border-t border-rule pt-5 sm:grid-cols-3">
          <div>
            <dt className="eyebrow mb-1 text-ink-faint">Attack families</dt>
            <dd className="font-mono text-sm">
              {coverage.familiesCovered} of {coverage.familiesKnown}
            </dd>
          </div>
          <div>
            <dt className="eyebrow mb-1 text-ink-faint">Difficulty</dt>
            <dd className="font-mono text-sm">{coverage.tierLabel}</dd>
          </div>
          <div>
            <dt className="eyebrow mb-1 text-ink-faint">Assessment of</dt>
            <dd className="font-mono text-sm">the testing, not the bot</dd>
          </div>
        </dl>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <Eyebrow className="mb-3">What ran</Eyebrow>
          {covered.length === 0 ? (
            <p className="text-sm text-ink-soft">Nothing completed.</p>
          ) : (
            <ul className="space-y-1.5">
              {covered
                .sort((a, b) => b[1] - a[1])
                .map(([family, count]) => (
                  <li
                    key={family}
                    className="flex items-baseline justify-between gap-4 border-b border-rule pb-1.5 text-sm"
                  >
                    <span>{FAMILY_LABELS[family] ?? family}</span>
                    <span className="font-mono text-xs text-ink-faint">
                      {count} attack{count === 1 ? "" : "s"}
                    </span>
                  </li>
                ))}
            </ul>
          )}
        </div>

        <div>
          <Eyebrow className="mb-3">What never ran</Eyebrow>
          {coverage.untested.length === 0 ? (
            <p className="text-sm leading-relaxed text-ink-soft">
              Every family Faultline knows about was exercised. That is the ceiling of
              what this tool can currently claim — not the ceiling of what exists.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {coverage.untested.map((family) => (
                <li
                  key={family}
                  className="flex items-baseline justify-between gap-4 border-b border-rule pb-1.5 text-sm text-ink-soft"
                >
                  <span>{family}</span>
                  <span className="font-mono text-xs text-ink-faint">untested</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {coverage.nextStep && (
        <Card className="px-5 py-4">
          <Eyebrow className="mb-2">Do this next</Eyebrow>
          <p className="text-sm leading-relaxed">{coverage.nextStep}</p>
        </Card>
      )}
    </section>
  );
}
