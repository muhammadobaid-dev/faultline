"""Visual Replay, rendered to a single self-contained HTML file.

This is a throwaway preview, not frontend code. It exists to answer one question
cheaply: is the judge's output actually enough to build the signature screen from?
Highlighting uses a plain <mark> over the character offsets the judge's span resolves
to, which is the same mechanism the real screen will use - no diff library needed.
"""

from __future__ import annotations

import html
from pathlib import Path

from faultline.domain import JudgedCase, VerdictKind
from faultline.packs.loader import RulePack

_CSS = """
:root { color-scheme: light dark; --bg:#fff; --fg:#16181d; --muted:#5f6672;
  --line:#e3e6ea; --card:#fff; --attack:#f6f7f9; --markbg:#ffd9d9; --markfg:#7a1420;
  --fail:#c02b3a; --ok:#177245; }
@media (prefers-color-scheme: dark) { :root { --bg:#0f1115; --fg:#e7e9ee;
  --muted:#98a0ad; --line:#252a33; --card:#161920; --attack:#1b1f27;
  --markbg:#5c1f27; --markfg:#ffd9dd; --fail:#ff7b8a; --ok:#5fd39b; } }
* { box-sizing: border-box; }
body { margin:0; padding:2.5rem 1.25rem 5rem; background:var(--bg); color:var(--fg);
  font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width: 780px; margin: 0 auto; }
h1 { font-size:1.6rem; margin:0 0 .25rem; letter-spacing:-.02em; }
.sub { color:var(--muted); margin:0 0 2rem; font-size:.95rem; }
.summary { display:flex; flex-wrap:wrap; gap:1.5rem; padding:1rem 1.25rem;
  border:1px solid var(--line); border-radius:10px; margin-bottom:2.5rem; }
.summary div { min-width:7rem; }
.summary .n { font-size:1.5rem; font-weight:650; display:block; }
.summary .l { color:var(--muted); font-size:.8rem; text-transform:uppercase;
  letter-spacing:.06em; }
.case { border:1px solid var(--line); border-radius:10px; background:var(--card);
  margin-bottom:1.75rem; overflow:hidden; }
.case > header { padding:.75rem 1.25rem; border-bottom:1px solid var(--line);
  display:flex; gap:.75rem; align-items:baseline; flex-wrap:wrap; }
.rule { font-weight:600; }
.tag { font-size:.75rem; color:var(--muted); font-family:ui-monospace,monospace; }
.body { padding:1.25rem; }
.turn { margin-bottom:1rem; }
.who { font-size:.72rem; text-transform:uppercase; letter-spacing:.08em;
  color:var(--muted); margin-bottom:.3rem; }
.msg { white-space:pre-wrap; padding:.75rem .9rem; border-radius:8px;
  background:var(--attack); }
.msg.reply { background:transparent; border:1px solid var(--line); }
mark { background:var(--markbg); color:var(--markfg); padding:.05em .15em;
  border-radius:3px; }
.why { margin-top:1rem; padding-top:1rem; border-top:1px dashed var(--line); }
.why p { margin:.35rem 0; }
.label { font-size:.72rem; text-transform:uppercase; letter-spacing:.08em;
  color:var(--muted); }
.safer { white-space:pre-wrap; font-style:italic; color:var(--muted); }
.warn { color:var(--fail); font-size:.85rem; margin-top:.6rem; }
.none { color:var(--muted); font-style:italic; }
"""


def _highlight(text: str, start: int | None, end: int | None) -> str:
    if start is None or end is None:
        return html.escape(text)
    return (
        html.escape(text[:start])
        + "<mark>"
        + html.escape(text[start:end])
        + "</mark>"
        + html.escape(text[end:])
    )


def _case_html(judged: JudgedCase, rule_title: str) -> str:
    verdict = judged.verdict
    assert verdict is not None
    parts = [
        '<article class="case">',
        "<header>",
        f'<span class="rule">{html.escape(rule_title)}</span>',
        f'<span class="tag">{html.escape(judged.case.id)} &middot; '
        f"{html.escape(judged.case.technique)}"
        f'{" &middot; escalated" if judged.escalated else ""}</span>',
        "</header>",
        '<div class="body">',
    ]

    last = len(judged.run.transcript) - 1
    for i, exchange in enumerate(judged.run.transcript):
        turn_label = f"Attacker &middot; turn {i + 1}" if last > 0 else "Attacker"
        parts.append(
            f'<div class="turn"><div class="who">{turn_label}</div>'
            f'<div class="msg">{html.escape(exchange.user)}</div></div>'
        )
        reply = exchange.assistant or ""
        body = (
            _highlight(reply, judged.span_start, judged.span_end)
            if i == last
            else html.escape(reply)
        )
        parts.append(
            f'<div class="turn"><div class="who">Assistant</div>'
            f'<div class="msg reply">{body}</div></div>'
        )

    parts.append('<div class="why">')
    parts.append(
        f'<p><span class="label">Why this failed</span><br>'
        f"{html.escape(verdict.rationale)}</p>"
    )
    if verdict.suggested_safer_response:
        parts.append(
            f'<p><span class="label">Safer response</span><br>'
            f'<span class="safer">{html.escape(verdict.suggested_safer_response)}</span></p>'
        )
    if not judged.span_is_verbatim:
        parts.append(
            '<p class="warn">The judge returned a span that does not appear in the '
            "response, so nothing could be highlighted.</p>"
        )
    parts.append("</div></div></article>")
    return "".join(parts)


def render(
    judged_cases: list[JudgedCase],
    pack: RulePack,
    out_path: Path,
    *,
    subtitle: str = "",
) -> Path:
    failures = [j for j in judged_cases if j.failed]
    graded = [j for j in judged_cases if j.verdict is not None]
    flagged = [
        j for j in graded if j.verdict and j.verdict.verdict is VerdictKind.FLAGGED
    ]
    titles = {r.id: r.title for r in pack.rules}

    cards = (
        "".join(_case_html(j, titles.get(j.case.rule_id, j.case.rule_id)) for j in failures)
        or '<p class="none">No failures to replay.</p>'
    )

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Visual Replay preview - {html.escape(pack.name)}</title>
<style>{_CSS}</style></head><body><main>
<h1>{html.escape(pack.name)}</h1>
<p class="sub">{html.escape(subtitle)}</p>
<section class="summary">
  <div><span class="n">{len(graded)}</span><span class="l">Graded</span></div>
  <div><span class="n">{len(failures)}</span><span class="l">Failures</span></div>
  <div><span class="n">{len(flagged)}</span><span class="l">Still borderline</span></div>
  <div><span class="n">{sum(1 for j in graded if j.escalated)}</span>
       <span class="l">Escalated</span></div>
</section>
{cards}
</main></body></html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
    return out_path
