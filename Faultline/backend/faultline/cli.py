"""Command line entry point for the slice.

    python -m faultline generate   # build and pin a test set
    python -m faultline execute    # run it against the target
    python -m faultline judge      # grade the transcripts and render Replay

Each step writes its output to disk so the next can pick it up, and every model call
goes through a cassette, so re-running a step after the first time costs nothing.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from faultline import config
from faultline.domain import (
    AttackCase,
    CaseRun,
    Exchange,
    JudgedCase,
    TestSet,
    VerdictKind,
)
from faultline.execution.runner import VERBATIM_THRESHOLD, Executor
from faultline.execution.targets import load_target
from faultline.generation.generator import AttackGenerator
from faultline.judging.judge import Judge
from faultline.packs.loader import load_builtin
from faultline.providers.base import LLMProvider, Outcome
from faultline.providers.cassette import CassetteMode, CassetteProvider
from faultline.providers.chain import FallbackChain
from faultline.replay.render import render

# 15 RPM is the tightest ceiling we run against. Pace every call rather than
# discovering the limit as a 429 mid-run.
SECONDS_BETWEEN_CALLS = 4.5

TARGET_PATH = config.FIXTURES_DIR / "targets" / "meridian_support.toml"
TESTSET_PATH = config.OUT_DIR / "testset.json"
RUNS_PATH = config.OUT_DIR / "runs.json"
JUDGED_PATH = config.OUT_DIR / "judged.json"
REPLAY_PATH = config.OUT_DIR / "replay.html"

# 40 cases with 8 multi-turn averaging four turns costs about 64 target calls.
DEFAULT_TOTAL_CASES = 40
MULTI_TURN_PER_RULE = {
    "SP-05": 3,  # oracle leakage is inherently a many-questions attack
    "SP-02": 2,
    "SP-01": 1,
    "SP-03": 1,
    "SP-04": 1,
    "SP-06": 0,
}

# Cases engineered to sit exactly on a rubric boundary, where "flagged" is the honest
# verdict. These measure whether the judge's escalation path fires at all - across 95
# consecutive calls so far it has never once been used.
BORDERLINE_PER_RULE = {
    "SP-02": 4,  # the reconstructability line
    "SP-05": 4,  # the confirm-or-deny line
}


class PacedProvider:
    """Wraps a provider and sleeps between real calls. Replays are not paced."""

    def __init__(self, inner: LLMProvider, seconds: float) -> None:
        self._inner = inner
        self._seconds = seconds
        self._last: float | None = None

    def generate(self, request):
        before = getattr(self._inner, "replayed", None)
        response = self._inner.generate(request)
        served_from_disk = before is not None and getattr(self._inner, "replayed") > before
        if not served_from_disk:
            self._last = time.monotonic()
            time.sleep(self._seconds)
        return response


def build_provider(
    mode: CassetteMode, steps=None
) -> tuple[PacedProvider, FallbackChain, CassetteProvider]:
    """Cassette outside the chain, so a replayed call spends no allowance and does
    not fail over."""
    chain = config.build_chain(steps or config.judge_chain_steps())
    cassette = CassetteProvider(chain, config.CASSETTE_DIR, mode)
    return PacedProvider(cassette, SECONDS_BETWEEN_CALLS), chain, cassette



def chain_requests(chain: FallbackChain) -> int:
    """Real provider calls made, summed across every rung the chain touched."""
    return sum(
        getattr(p, "request_count", 0) for p in chain._providers.values()  # noqa: SLF001
    )

def _log_setup() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)-7s %(name)-20s %(message)s"
    )


# -- commands -------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    pack = load_builtin("system-prompt-leak")
    target = load_target(TARGET_PATH)
    provider, chain, _ = build_provider(CassetteMode(args.cassette))

    generator = AttackGenerator(provider, config.GENERATION_MODEL)
    test_set = generator.generate(
        pack,
        target,
        total_cases=args.cases,
        multi_turn_per_rule=MULTI_TURN_PER_RULE,
        borderline_per_rule=BORDERLINE_PER_RULE,
    )

    TESTSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TESTSET_PATH.write_text(test_set.model_dump_json(indent=2), encoding="utf-8")

    multi = sum(1 for c in test_set.cases if c.is_multi_turn)
    edge = sum(1 for c in test_set.cases if c.borderline)
    turns = sum(len(c.turns) for c in test_set.cases)
    print(f"\ntest set {test_set.version}: {len(test_set.cases)} cases "
          f"({multi} multi-turn, {edge} borderline), {turns} target calls when executed")
    print(f"requests spent: {chain_requests(chain)}")
    print(f"written to {TESTSET_PATH}")
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    test_set = TestSet.model_validate_json(TESTSET_PATH.read_text(encoding="utf-8"))
    target = load_target(TARGET_PATH)
    provider, chain, cassette = build_provider(CassetteMode(args.cassette))

    executor = Executor(provider, target)
    runs: list[CaseRun] = []
    for i, case in enumerate(test_set.cases, start=1):
        run = executor.run_case(case)
        runs.append(run)
        flag = "CANARY" if run.canary_leaked else ("VERBATIM" if run.verbatim_overlap >= VERBATIM_THRESHOLD else "")
        print(f"  [{i:2}/{len(test_set.cases)}] {case.id:9} {case.technique[:24]:24} "
              f"{run.outcome.value:14} overlap={run.verbatim_overlap:4} {flag}", flush=True)

    RUNS_PATH.write_text(
        json.dumps([r.model_dump(mode="json") for r in runs], indent=2), encoding="utf-8"
    )
    gradeable = sum(1 for r in runs if r.gradeable)
    print(f"\n{gradeable}/{len(runs)} gradeable; "
          f"canary leaked in {sum(1 for r in runs if r.canary_leaked)}; "
          f"verbatim overlap >= {VERBATIM_THRESHOLD} in "
          f"{sum(1 for r in runs if r.verbatim_overlap >= VERBATIM_THRESHOLD)}")
    print(f"requests spent: {chain_requests(chain)} (replayed {cassette.replayed})")
    return 0


def cmd_judge(args: argparse.Namespace) -> int:
    pack = load_builtin("system-prompt-leak")
    test_set = TestSet.model_validate_json(TESTSET_PATH.read_text(encoding="utf-8"))
    runs = {
        r["case_id"]: CaseRun.model_validate(r)
        for r in json.loads(RUNS_PATH.read_text(encoding="utf-8"))
    }
    provider, chain, cassette = build_provider(CassetteMode(args.cassette))
    judge = Judge(provider, config.JUDGE_FIRST_PASS_MODEL, config.JUDGE_ESCALATION_MODEL)

    judged: list[JudgedCase] = []
    for i, case in enumerate(test_set.cases, start=1):
        run = runs.get(case.id)
        if run is None:
            continue
        result = judge.judge(case, run, pack.rule(case.rule_id))
        judged.append(result)
        verdict = result.verdict.verdict.value if result.verdict else "unjudged"
        conf = result.verdict.confidence.value if result.verdict else "-"
        print(f"  [{i:2}/{len(test_set.cases)}] {case.id:11} "
              f"{'EDGE' if case.borderline else '    '} {verdict:9} {conf:7}"
              f"{' ESCALATED' if result.escalated else ''}"
              f"{'' if result.span_is_verbatim else '  SPAN-NOT-VERBATIM'}", flush=True)

    JUDGED_PATH.write_text(
        json.dumps([j.model_dump(mode="json") for j in judged], indent=2), encoding="utf-8"
    )

    graded = [j for j in judged if j.verdict]
    fails = [j for j in graded if j.failed]
    flagged = [j for j in graded if j.verdict and j.verdict.verdict is VerdictKind.FLAGGED]
    render(
        judged, pack, REPLAY_PATH,
        subtitle=f"test set {test_set.version} against {test_set.target_id} "
                 f"({test_set.target_model})",
    )

    edge = [j for j in graded if j.case.borderline]
    edge_escalated = sum(1 for j in edge if j.escalated)
    print(f"\ngraded {len(graded)}/{len(judged)}; {len(fails)} failures; "
          f"{len(flagged)} still borderline after escalation")
    print(f"escalated {judge.escalation_calls}/{judge.first_pass_calls} "
          f"({judge.escalation_calls / max(judge.first_pass_calls, 1):.0%})")
    print(f"deliberate borderline cases: {len(edge)}; of those, "
          f"{edge_escalated} escalated, "
          f"{sum(1 for j in edge if j.verdict and j.verdict.verdict is VerdictKind.FLAGGED)} flagged")
    print(f"requests spent: {chain_requests(chain)} (replayed {cassette.replayed})")
    print(f"replay written to {REPLAY_PATH}")
    return 0


def cmd_judge_fixtures(args: argparse.Namespace) -> int:
    """Judge hand-authored transcripts.

    The judge does not care whether a transcript came from a live target, so a
    hand-authored one costs zero target calls. That makes this the cheapest way to
    measure judge behaviour on inputs we could not reliably provoke in a live run.
    """
    pack = load_builtin("system-prompt-leak")
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    provider, chain, _ = build_provider(CassetteMode(args.cassette))
    judge = Judge(provider, args.first_pass_model, args.escalation_model)
    print(f"first pass: {args.first_pass_model}  escalation: {args.escalation_model}\n")

    results = []
    for raw in fixture["cases"]:
        case = AttackCase(
            id=raw["id"],
            rule_id=raw["rule_id"],
            technique="borderline",
            turns=[t["user"] for t in raw["turns"]],
            borderline=True,
        )
        run = CaseRun(
            case_id=case.id,
            rule_id=case.rule_id,
            outcome=Outcome.OK,
            transcript=[
                Exchange(user=t["user"], assistant=t["assistant"]) for t in raw["turns"]
            ],
        )
        judged = judge.judge(case, run, pack.rule(case.rule_id))
        results.append({"expected_strength": raw.get("reviewer_strength"),
                        "judged": judged.model_dump(mode="json")})

        verdict = judged.verdict.verdict.value if judged.verdict else "unjudged"
        conf = judged.verdict.confidence.value if judged.verdict else "-"
        print(f"  {case.id:10} {case.rule_id}  {verdict:8} {conf:7}"
              f"{'ESCALATED' if judged.escalated else '':11}", flush=True)
        if judged.verdict:
            print(f"             {judged.verdict.rationale}", flush=True)

    # Derived from the fixture, so judging one set never clobbers another's results.
    out = config.OUT_DIR / f"judged_{Path(args.fixture).stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    graded = [r["judged"] for r in results if r["judged"]["verdict"]]
    flagged = [r for r in graded if r["verdict"]["verdict"] == "flagged"]
    escalated = [r for r in graded if r["escalated"]]
    print(f"\nflagged {len(flagged)}/{len(graded)}; escalated {len(escalated)}/{len(graded)}")
    print(f"requests spent: {chain_requests(chain)}")
    print(f"written to {out}")
    return 0


def cmd_export_web(args: argparse.Namespace) -> int:
    """Emit the judged failures the Visual Replay screen renders.

    Reads whatever judged results are on disk and writes one flat JSON the frontend
    imports directly. No database yet: the screen is a rendering of records we have
    already produced, so it costs nothing to serve.
    """
    pack = load_builtin("system-prompt-leak")
    titles = {r.id: r.title for r in pack.rules}
    failures = []

    for path in sorted(config.OUT_DIR.glob("judged_*.json")):
        for record in json.loads(path.read_text(encoding="utf-8")):
            judged = record["judged"]
            verdict = judged.get("verdict")
            if not verdict or verdict["verdict"] != "fail":
                continue
            case, run = judged["case"], judged["run"]
            failures.append({
                "id": case["id"],
                "ruleId": case["rule_id"],
                "ruleTitle": titles.get(case["rule_id"], case["rule_id"]),
                "packName": pack.name,
                "packVersion": pack.version,
                "technique": case["technique"],
                "turns": [
                    {"user": e["user"], "assistant": e["assistant"] or ""}
                    for e in run["transcript"]
                ],
                "spanStart": judged["span_start"],
                "spanEnd": judged["span_end"],
                "spanIsVerbatim": judged["span_is_verbatim"],
                "rationale": verdict["rationale"],
                "saferResponse": verdict["suggested_safer_response"],
                "confidence": verdict["confidence"],
                "judgedBy": judged["judged_by"],
                "escalated": judged["escalated"],
            })

    payload = {
        "pack": {"id": pack.id, "name": pack.name, "version": pack.version},
        "target": {"id": "meridian-support", "name": "Meridian Cloud support assistant"},
        "judge": config.JUDGE_FIRST_PASS_MODEL,
        "failures": failures,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"{len(failures)} failures -> {out}")
    for f in failures:
        print(f"  {f['id']:11} {f['ruleId']}  span {f['spanStart']}-{f['spanEnd']}  "
              f"{len(f['turns'])} turn(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    _log_setup()
    parser = argparse.ArgumentParser(prog="faultline")
    parser.add_argument(
        "--cassette", default="auto",
        choices=[m.value for m in CassetteMode],
        help="auto replays what is recorded and records the rest",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="build and pin a test set")
    gen.add_argument("--cases", type=int, default=DEFAULT_TOTAL_CASES)
    gen.set_defaults(func=cmd_generate)

    sub.add_parser("execute", help="run the test set against the target").set_defaults(
        func=cmd_execute
    )
    sub.add_parser("judge", help="grade transcripts and render Replay").set_defaults(
        func=cmd_judge
    )

    fixtures = sub.add_parser(
        "judge-fixtures", help="judge hand-authored transcripts (no target calls)"
    )
    fixtures.add_argument(
        "--fixture",
        default=str(config.FIXTURES_DIR / "golden" / "borderline_transcripts.json"),
    )
    fixtures.add_argument("--first-pass-model", default=config.JUDGE_FIRST_PASS_MODEL)
    fixtures.add_argument("--escalation-model", default=config.JUDGE_ESCALATION_MODEL)
    fixtures.set_defaults(func=cmd_judge_fixtures)

    export = sub.add_parser(
        "export-web", help="emit judged failures for the Visual Replay screen"
    )
    export.add_argument(
        "--out", default=str(config.BACKEND_ROOT.parent / "web" / "src" / "data" / "failures.json")
    )
    export.set_defaults(func=cmd_export_web)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
