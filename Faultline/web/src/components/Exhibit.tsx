import type { Failure } from "@/lib/types";
import { MarkedResponse } from "./MarkedResponse";

type Props = {
  failure: Failure;
  index: number;
};

/**
 * One failure, laid out as an evidence exhibit: the transcript on the left, the
 * judge's findings in the margin. The marked sentence is the only amber on the
 * page, so it is where the eye goes first.
 */
export function Exhibit({ failure, index }: Props) {
  const lastTurn = failure.turns.length - 1;

  return (
    <article className="border-t border-rule pt-8 md:pt-12">
      <header className="mb-6 md:mb-8">
        <div className="eyebrow text-ink-faint flex flex-wrap items-baseline gap-x-3 gap-y-1">
          {/* Deliberately not amber. The marked sentence is the only amber on
              the page; giving the label the accent too dilutes it. */}
          <span className="text-ink-soft">
            Exhibit {String(index + 1).padStart(2, "0")}
          </span>
          <span aria-hidden>·</span>
          <span>{failure.ruleId}</span>
          <span aria-hidden>·</span>
          <span>{failure.technique.replace(/_/g, " ")}</span>
          {failure.escalated && (
            <>
              <span aria-hidden>·</span>
              <span>escalated</span>
            </>
          )}
        </div>
        <h2 className="font-display text-2xl md:text-[2rem] leading-[1.15] mt-2 max-w-2xl text-balance">
          {failure.ruleTitle}
        </h2>
      </header>

      <div className="grid gap-8 md:gap-12 md:grid-cols-[minmax(0,1fr)_15rem] lg:grid-cols-[minmax(0,1fr)_17rem]">
        <div className="space-y-6">
          {failure.turns.map((turn, i) => (
            <div key={i} className="space-y-6">
              <div>
                <div className="eyebrow text-ink-faint mb-2">
                  Attack{failure.turns.length > 1 ? ` · turn ${i + 1}` : ""}
                </div>
                <p className="transcript text-ink-soft text-[0.9375rem] leading-relaxed border-l border-rule pl-4">
                  {turn.user}
                </p>
              </div>
              <div>
                <div className="eyebrow text-ink-faint mb-2">Response</div>
                <div className="text-[1.0625rem] leading-[1.75] bg-paper-raised border border-rule rounded-sm px-5 py-4">
                  {i === lastTurn ? (
                    <MarkedResponse
                      text={turn.assistant}
                      spanStart={failure.spanStart}
                      spanEnd={failure.spanEnd}
                    />
                  ) : (
                    <p className="transcript">{turn.assistant}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <aside className="space-y-6 md:border-l md:border-rule md:pl-6 lg:pl-8">
          <div>
            <div className="eyebrow text-ink-faint mb-2">Why this failed</div>
            <p className="text-[0.9375rem] leading-relaxed">{failure.rationale}</p>
          </div>

          {failure.saferResponse && (
            <div>
              <div className="eyebrow text-ink-faint mb-2">Safer response</div>
              <p className="text-[0.9375rem] leading-relaxed text-ink-soft italic">
                {failure.saferResponse}
              </p>
            </div>
          )}

          <div>
            <div className="eyebrow text-ink-faint mb-2">Graded by</div>
            {/* Two blocks rather than a <br>, so this is not announced as one
                run-on string. */}
            <p className="font-mono text-xs text-ink-soft leading-relaxed">
              <span className="block">{failure.judgedBy}</span>
              <span className="block">{failure.confidence} confidence</span>
            </p>
          </div>

          {!failure.spanIsVerbatim && (
            <p className="font-mono text-xs text-amber-text leading-relaxed">
              The judge returned a span that does not appear in the response, so
              nothing could be marked.
            </p>
          )}
        </aside>
      </div>
    </article>
  );
}
