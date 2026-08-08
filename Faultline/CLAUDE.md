# Faultline — Standing Technology Plan

AI behavior testing platform. "CI for AI behavior." It attacks AI applications before real users do.

This file is the **decided** technology plan. It is not a wish list and not a backlog. Every entry is
marked with the phase it belongs to. **Do not install anything until its phase actually arrives** —
the "avoid unnecessary dependencies" rule governs every phase, and a dependency added early is a cost
paid early for value not yet needed. Nothing here is to be re-litigated; if a decision needs to
change, raise it explicitly with the founder.

---

## Hard constraints that govern all code, in every phase

- **Gemini free tier only. Zero dollars, no exceptions.** ~15 RPM / 1,500 requests per day (Flash-Lite
  reaches 30 RPM). The daily cap resets at **midnight Pacific**, a hard boundary, not a rolling window.
  Gemini Pro left the free tier in April 2026, so Flash is the strongest judge available. Request
  frugality is a first-class design principle, not an optimization.
- **Never push broken code.** Every pushed commit must be green: tests pass, no errors, no
  half-finished work. Work on `main` (trunk-based); keep it local until it is green. Short-lived
  branches only for genuinely risky experiments.
- **User-facing vs. internal vocabulary split.** Violating it is a bug. User-facing: Rules / Rule Pack,
  Attack Run, Grade (A–F) with a one-line reason, Trust Page, Evidence Report, Test Suite, Attack
  Library. Internal only: policy spec, adversarial evaluation job, LLM-as-judge verdict, system card /
  compliance export, evaluation harness, adversarial corpus. The words *policy, governance, compliance,
  red-teaming, system card* never appear in the primary UI.
- **Error taxonomy — these are distinct and none of them ever scores a target down.** A target only
  fails when it actually breaks a rule.
  - `safety_blocked` — Gemini refused to process; neither pass nor fail
  - `deferred` — our own daily quota is exhausted; resumes at the midnight-Pacific reset
  - `unavailable` — HTTP 503, transient, retry with backoff
  - `errored` — retries exhausted; excluded from the grade denominator entirely
- **Secrets in environment variables only.** The repository is public. A leaked provider key is both a
  security and a cost incident.
- **Never use `-latest` model aliases.** An alias rolling to a new model would change grades without
  the target changing, breaking pinned-test-set comparability. Pin explicit versioned model IDs and
  treat the model ID as part of the test-set version.

---

## Phase: CLI slice (current)

Dependencies are **Pydantic and pytest only**. HTTP via the standard library. Rule packs in TOML
(`tomllib`, stdlib). Nothing else. This restriction is deliberate and holds for the whole slice.

---

## Phase: backend

Decided, install when the backend phase begins.

- **`google-genai`** — the current SDK. **Never the legacy `google-generativeai`.** Use Pydantic
  `response_schema` for structured JSON output, with `BLOCK_NONE` safety settings. Keep a
  `BLOCK_ONLY_HIGH` fallback and `finish_reason == "SAFETY"` handling in case `BLOCK_NONE` is ever
  rejected.
- **FastAPI** — the API surface.
- **SQLModel + async SQLAlchemy 2.0 + asyncpg + Alembic** — ORM, driver, migrations. Do not stack a
  second ORM on top of SQLModel.
- **pgvector** — vectors live in Postgres; no separate vector database.
- **Hand-rolled Postgres job queue using `FOR UPDATE SKIP LOCKED`.** Not Celery, not Redis, not arq.
  Graduate to **PgQueuer** only if concurrency genuinely demands `LISTEN`/`NOTIFY`.
- **tenacity** — backoff for 429 and 503.
- **slowapi** — inbound rate limiting.
- **structlog** — structured logging, built in from the start for the core flow.
- **cryptography (Fernet / MultiFernet)** — encrypting users' stored bot API keys at rest.

## Phase: frontend

Decided, install when the frontend phase begins.

- **Next.js App Router + React + TypeScript + Tailwind** — app, public Trust Pages, and punchbag.
- **shadcn/ui + Radix** — components and accessibility primitives.
- **`motion`** — import from `motion/react`.
- **lucide-react** — icons.
- **Recharts, or a hand-rolled SVG sparkline**, for Trust Page trends. No heavy chart libraries.
- **Sonner** — toasts.
- **`@vercel/og`** — Trust Page social images. No separate OG-image service.
- **shields.io endpoint-badge standard** — the README badge.
- **Visual Replay highlighting: plain `<mark>`.** The judge returns character offsets, so no diff
  library is needed. Add **`@sanity/diff-match-patch`** only if a safer-response diff is genuinely
  required. **Never the archived `google/diff-match-patch`.**

## Phase: testing and developer experience

Decided; adopt as each phase needs it.

- **pytest + pytest-asyncio**
- **respx and/or vcrpy / pytest-vcr** — record and replay Gemini HTTP so CI runs free and deterministic
- **ruff** (Python) and **Biome** (TS/JS), with a minimal `eslint-config-next` kept only for
  Next-specific accessibility rules
- **mypy or pyright**
- **pre-commit**
- **GitHub Actions CI** — free for our public repository

## Phase: tooling and skills

Install per phase, never up front.

- Anthropic official: `/plugin marketplace add anthropics/skills`, then
  `/plugin install example-skills@anthropic-agent-skills` — `frontend-design` (frontend phase),
  `webapp-testing` (UI verification phase), `web-artifacts-builder`, `mcp-builder`, `skill-creator`.
- Community: **`ibelick/ui-skills`** via `npx ui-skills add --all` (baseline-ui, fixing-accessibility,
  fixing-metadata, fixing-motion-performance) for the frontend phase. **`wshobson/agents`** via
  `/plugin marketplace add https://github.com/wshobson/agents` for `security-auditor`,
  `backend-architect`, `database-optimizer`, `test-automator`, `api-documenter` as those phases arrive.
  Optionally **`obra/superpowers`** for TDD discipline.
- Database schema work: the **`crystaldba/postgres-mcp`** MCP server. **Never the deprecated
  `@modelcontextprotocol/server-postgres`** — it carries a SQL-injection vulnerability.

---

## Free-tier constraints to design around

All decided. Design for these rather than pretending them away.

- **Render (backend).** The free service spins down after **15 minutes idle** with a **30–60s cold
  start**, so the Postgres queue does not drain while the service is asleep. A GitHub Actions cron
  heartbeat to a `/healthz` endpoint keeps it warm during active windows. **750 instance-hours per
  month means we cannot stay warm 24/7 all month** — accept periodic cold starts, and design jobs to
  be idempotent and resumable.
- **Neon (database).** Scales to zero after **5 minutes** idle, wakes in roughly **500ms**, with a
  **0.5 GB per-project storage cap**. Transcripts and embeddings must be pruned or compressed;
  retention is built in from day one, not retrofitted.
- **Vercel (frontend).** Hobby has a short function timeout — **treat it as 10s** — and is restricted
  to **non-commercial use**. Long Attack Runs therefore run on Render via the queue and **never inside
  a Vercel function**. Move to Vercel Pro before Faultline earns any revenue.

---

## Never add (bloat, or known-bad)

- Celery, Redis, or arq
- LangChain or any heavy agent framework
- `@modelcontextprotocol/server-postgres` (deprecated, SQL-injection vulnerability)
- `google-generativeai` (legacy SDK)
- Heavy chart libraries: ECharts, visx, Nivo
- A second ORM layered on top of SQLModel
- The archived `google/diff-match-patch`
- A separate OG-image service
