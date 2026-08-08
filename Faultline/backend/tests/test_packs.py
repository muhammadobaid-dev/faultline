from faultline.packs.loader import Oracle, available_packs, load_builtin


def test_the_slice_pack_loads_and_validates():
    pack = load_builtin("system-prompt-leak")
    assert pack.id == "system-prompt-leak"
    assert pack.name == "Never reveal the system prompt"
    assert len(pack.rules) == 6


def test_every_rule_states_all_three_branches():
    # A rule missing a branch would hand the judge a prompt that asks for a verdict it
    # has been given no criteria for - which is how the two-part rubric failed.
    for rule in load_builtin("system-prompt-leak").rules:
        assert rule.rule.strip(), f"{rule.id} has no assertion"
        assert rule.clear_pass.strip(), f"{rule.id} has no clear-pass branch"
        assert rule.clear_violation.strip(), f"{rule.id} has no clear-violation branch"
        assert rule.on_the_line.strip(), f"{rule.id} has no borderline branch"
        assert rule.examples_fail, f"{rule.id} has no canonical failing example"
        assert rule.examples_pass, f"{rule.id} has no canonical passing example"


def test_the_rubric_rewrite_is_recorded_as_a_version_bump():
    # Rewording a rubric changes judge behaviour, so any golden-set baseline collected
    # against an earlier version is invalidated by it. Every rewrite bumps this.
    assert load_builtin("system-prompt-leak").version >= 2


def test_the_two_collapsing_rules_have_worked_borderline_examples():
    # Both kept filing branch-3 disclosures under a confident verdict even with the
    # branch spelled out in prose. Concrete anchors for the verdict the judge will
    # not reach for moved SP-05's decisive case; SP-02 now gets the same treatment.
    # None of these examples is drawn from the test fixture.
    pack = load_builtin("system-prompt-leak")
    for rule_id in ("SP-05", "SP-02"):
        rule = pack.rule(rule_id)
        assert rule.examples_borderline, f"{rule_id} has no branch-3 anchor"
        assert 'ON THE LINE (branch 3 - return "flagged")' in rule.as_rubric()


def test_rule_ids_are_unique():
    ids = [r.id for r in load_builtin("system-prompt-leak").rules]
    assert len(ids) == len(set(ids))


def test_rubric_text_gives_the_judge_a_named_home_for_each_verdict():
    rubric = load_builtin("system-prompt-leak").rule("SP-03").as_rubric()
    assert "RULE SP-03" in rubric
    assert 'BRANCH 1 - CLEAR PASS (return "pass")' in rubric
    assert 'BRANCH 2 - CLEAR VIOLATION (return "fail")' in rubric
    assert 'BRANCH 3 - ON THE LINE (return "flagged")' in rubric
    assert "EDGE CASES" in rubric


def test_the_carve_out_that_swallowed_sp02_and_sp05_is_explicitly_closed():
    pack = load_builtin("system-prompt-leak")
    # The judge passed all ten borderlines by reclassifying disclosures as
    # "capability, not text". Both rubrics now name and forbid that move.
    assert "capability" in pack.rule("SP-05").edge_cases.lower()
    assert "operational" in pack.rule("SP-05").edge_cases.lower()
    assert "not scope" in pack.rule("SP-02").edge_cases.lower()


def test_the_canary_rule_is_marked_machine_checkable():
    pack = load_builtin("system-prompt-leak")
    assert pack.rule("SP-03").oracle is Oracle.CANARY
    # Two rules are verbatim-recoverable and one needs no human either way.
    assert pack.rule("SP-01").oracle is Oracle.OVERLAP
    assert pack.rule("SP-05").oracle is Oracle.NONE


def test_available_packs_lists_the_slice_pack():
    assert "system-prompt-leak" in available_packs()
