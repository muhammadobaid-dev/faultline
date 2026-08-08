import type { Metadata } from "next";
import Link from "next/link";

import { LeakSpecimen } from "@/components/marketing/LeakSpecimen";
import { Architecture, Faq, Section, Steps } from "@/components/marketing/Sections";
import { Punchbag } from "@/components/Punchbag";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ToastProvider } from "@/components/Toast";
import { ButtonLink } from "@/components/ui";

export const metadata: Metadata = {
  title: "Faultline — find out how your AI breaks before your users do",
  description:
    "Faultline attacks your AI application with adversarial prompts, grades what comes back, and tracks whether each change made it safer or opened something up. Every finding shows the exact sentence that broke the rule.",
  openGraph: {
    title: "Faultline — CI for AI behavior",
    description:
      "Adversarial testing for AI applications. Pinned attack suites, graded results, and a fix loop that proves its own patch.",
    type: "website",
  },
};

const STEPS = [
  {
    title: "It learns how your bot behaves",
    body: "Before writing a single attack, Faultline has an ordinary conversation with your assistant to see how it responds and what it asks for first.",
    note: "Without this step, 88 attacks against a realistic bot found nothing — every one died at an account-ID prompt.",
  },
  {
    title: "It writes attacks for your rules, then pins them",
    body: "Adversarial prompts are generated once against the rules you selected, then frozen. Every later run asks your bot exactly the same questions.",
    note: "Pinning is what makes a grade change mean something. Regenerate the suite and you are comparing two different exams.",
  },
  {
    title: "A judge grades each response and shows its work",
    body: "Every failure comes back with the rule that broke, the exact sentence that broke it, a plain-English reason, and what the bot should have said instead.",
    note: "The judge is measured against human labels rather than trusted. Its agreement is published, not assumed.",
  },
  {
    title: "Then it proposes a fix and proves it",
    body: "Faultline rewrites your system prompt to close what leaked, then re-runs the identical attacks against the rewrite so you see a before and after rather than a suggestion.",
    note: "It never applies the patch. A tool that edits what it grades cannot honestly grade it.",
  },
];

const FAQS = [
  {
    q: "How is this different from asking ChatGPT to attack my prompt?",
    a: (
      <>
        A one-off conversation gives you one-off answers. Faultline pins the attack
        suite, so the same questions run against every version of your prompt and a
        grade change means the bot changed rather than the questions. It also grades
        with a judge whose accuracy is measured, keeps the history, and re-tests its
        own proposed fix. The value is the loop, not the prompt.
      </>
    ),
  },
  {
    q: "What does a passing run actually prove?",
    a: (
      <>
        Less than you would hope, and Faultline says so. A clean result is reported
        alongside what was actually exercised — which attack families ran, how deep
        they went, and what was never tried. Confidence in the assessment and
        confidence in your AI are different numbers, and conflating them is how
        security tools mislead people.
      </>
    ),
  },
  {
    q: "Do you store my system prompt?",
    a: (
      <>
        Yes — a project has to keep it to re-test it. It is treated as entirely
        confidential, never rendered on any public page, and never shown to another
        account. Results from a pasted prompt are also marked as simulated, because
        they are graded on our stand-in model rather than your live deployment.
      </>
    ),
  },
  {
    q: "What does it cost to run?",
    a: (
      <>
        Nothing. Faultline runs on free infrastructure and free model tiers, with a
        provider chain that degrades through eight free options before anything paid
        is even reachable — and anonymous traffic can never reach a paid provider at
        all. Daily limits are real and visible in the product rather than hidden.
      </>
    ),
  },
  {
    q: "Can I wire it into CI?",
    a: (
      <>
        That is the direction this is built for. Runs come in two sizes so a pull
        request can run a small pinned suite cheaply while deeper audits stay manual,
        and every grade records which size produced it so a badge never overstates
        its evidence.
      </>
    ),
  },
];

export default function LandingPage() {
  return (
    <ToastProvider>
      <div className="flex-1">
        <header className="sticky top-0 z-30 border-b border-rule/80 bg-paper/80 backdrop-blur-md">
          <div className="mx-auto flex max-w-5xl items-baseline justify-between gap-6 px-6 py-4 md:px-10">
            <span className="font-display text-lg font-semibold tracking-tight">
              Faultline
            </span>
            <nav className="flex items-baseline gap-5">
              <a
                href="#how"
                className="eyebrow hidden text-ink-faint transition-colors hover:text-ink sm:inline"
              >
                How it works
              </a>
              <a
                href="#demo"
                className="eyebrow hidden text-ink-faint transition-colors hover:text-ink sm:inline"
              >
                Demo
              </a>
              <ThemeToggle />
              <Link
                href="/signin"
                className="eyebrow text-ink transition-opacity hover:opacity-70"
              >
                Sign in
              </Link>
            </nav>
          </div>
        </header>

        {/* Hero — one composition: brand, claim, CTA, evidence plane */}
        <section className="relative overflow-hidden">
          <div
            aria-hidden
            className="hero-grid pointer-events-none absolute inset-0"
          />
          <div className="relative mx-auto max-w-5xl px-6 pb-12 pt-16 md:px-10 md:pb-16 md:pt-24">
            <p className="rise font-display text-5xl font-semibold tracking-tight md:text-7xl">
              Faultline
            </p>
            <div className="reveal-line mt-5 h-px w-24 bg-amber" />
            <h1 className="rise-delayed mt-8 max-w-3xl text-balance font-display text-2xl font-semibold leading-[1.15] tracking-tight md:text-4xl">
              Find out how your AI breaks before your users do.
            </h1>
            <p className="rise-delayed mt-5 max-w-xl text-lg leading-relaxed text-ink-soft">
              Adversarial prompts, pinned suites, and a judge that shows the exact
              sentence that gave it away.
            </p>
            <div className="rise-late mt-9 flex flex-wrap items-center gap-5">
              <ButtonLink href="/signin" variant="primary" className="px-6 py-3">
                Start testing your bot
              </ButtonLink>
              <a
                href="#demo"
                className="eyebrow text-ink-faint transition-colors hover:text-ink"
              >
                Or break our demo bot first →
              </a>
            </div>
            <p className="rise-late mt-5 font-mono text-xs leading-relaxed text-ink-faint">
              Free to run. GitHub sign-in. No card, no trial, no sales call.
            </p>
          </div>

          <LeakSpecimen />
        </section>

        <main className="mx-auto max-w-5xl px-6 md:px-10">
          <Section
            eyebrow="The problem"
            title="Prompts change every week. Nobody re-tests them."
            lede="A developer tightens a system prompt on Thursday and ships it. Nothing tells them it opened a hole. Manual red-teaming takes hours per release and is the first thing cut under a deadline, so the check that matters most is the one that stops happening."
          >
            <div className="grid border-t border-rule sm:grid-cols-3">
              {[
                [
                  "Hours per release",
                  "Manual adversarial testing, repeated by hand every time the prompt moves.",
                ],
                [
                  "No baseline",
                  "Without a fixed suite there is nothing to compare against, so regressions are invisible.",
                ],
                [
                  "Found by strangers",
                  "The people who eventually discover the leak are rarely the ones you wanted.",
                ],
              ].map(([head, body]) => (
                <div
                  key={head}
                  className="border-b border-rule p-6 sm:border-b-0 sm:border-r sm:last:border-r-0"
                >
                  <p className="font-display text-lg font-semibold tracking-tight">
                    {head}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-ink-soft">{body}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section
            eyebrow="What makes this different"
            title="“24 of 24 passed” is not an answer."
            lede="It is two claims wearing one coat: that your AI is safe, and that our testing was good enough to tell. Those are different things, and a security tool that blurs them is telling you a comfortable story."
          >
            <div className="grid gap-0 border-t border-rule md:grid-cols-2">
              <div className="border-b border-rule p-6 md:border-b-0 md:border-r md:p-8">
                <div className="eyebrow mb-3 text-ink-faint">What most tools report</div>
                <p className="font-display text-2xl font-semibold tracking-tight">
                  24 / 24 passed
                </p>
                <p className="mt-3 text-sm leading-relaxed text-ink-soft">
                  A number with no denominator you can reason about. It cannot tell you
                  whether your bot is solid or whether the attacks were soft.
                </p>
              </div>
              <div className="p-6 md:p-8">
                <div className="eyebrow mb-3 text-amber-text">What Faultline reports</div>
                <p className="font-display text-2xl font-semibold tracking-tight">
                  24 / 24 passed — low confidence
                </p>
                <p className="mt-3 text-sm leading-relaxed text-ink-soft">
                  Which attack families ran, which never did, how deep they went, and
                  what to try next. A clean sheet becomes the start of the next round
                  rather than the end of the story.
                </p>
              </div>
            </div>
          </Section>

          <Section
            id="how"
            eyebrow="How it works"
            title="Four steps, and the last one is the one people keep."
          >
            <Steps steps={STEPS} />
          </Section>

          <div id="demo" className="scroll-mt-24">
            <Punchbag />
          </div>

          <Section
            eyebrow="Architecture"
            title="Built to run for nothing, and to say so honestly."
            lede="Every layer is free-tier infrastructure chosen for a stated reason, and the constraints are designed around rather than hidden. When a model runs out of daily quota the run degrades down a chain instead of dying, and it never quietly reaches a paid provider."
          >
            <Architecture />
          </Section>

          <Section eyebrow="Questions" title="The things people ask first.">
            <Faq items={FAQS} />
          </Section>

          <section className="border-t border-rule py-16 md:py-24">
            <div className="max-w-2xl">
              <h2 className="text-balance font-display text-3xl font-semibold leading-tight tracking-tight md:text-[2.5rem]">
                Point it at your prompt and see what falls out.
              </h2>
              <p className="mt-5 text-lg leading-relaxed text-ink-soft">
                One project, one paste, one run. If nothing breaks, Faultline will tell
                you how much that is worth — and go looking harder.
              </p>
              <div className="mt-8">
                <ButtonLink href="/signin" variant="primary" className="px-6 py-3">
                  Start testing your bot
                </ButtonLink>
              </div>
            </div>
          </section>
        </main>

        <footer className="border-t border-rule">
          <div className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-10 md:flex-row md:items-end md:justify-between md:px-10">
            <div className="max-w-xl space-y-3">
              <p className="font-mono text-xs leading-relaxed text-ink-faint">
                Grading is done by a single-family Gemini judge. Its agreement with human
                labels is measured and published rather than assumed — a tool that asks
                you to trust its verdicts should show its own working.
              </p>
              <p className="eyebrow text-ink-soft">
                Developed by MUHAMMAD OBAID
              </p>
            </div>
            <nav className="flex gap-5">
              <Link href="/signin" className="eyebrow text-ink-faint hover:text-ink">
                Sign in
              </Link>
              <a
                href="https://github.com/emdanish/faultline"
                className="eyebrow text-ink-faint hover:text-ink"
              >
                Source
              </a>
            </nav>
          </div>
        </footer>
      </div>
    </ToastProvider>
  );
}
