"""Characterization + invariant tests for the C4 v2 frozen-probe instrument.

The pilot fingerprints lock the exact probes and prompts the reported pilot
numbers came from. If a refactor changes either, the pilot CSV no longer
describes the code and these tests fail.
"""
from __future__ import annotations

import hashlib

import pytest

from src.evaluation.attribution_frozen import (
    HIDDEN,
    FrozenProbe,
    check_probe,
    frequency_baseline,
    grade,
    lexical_pick,
    names_in_answer,
    render_main,
    render_swap,
    swap_partner,
    turn_taking_baseline,
    visible_counts,
)

PILOT_CONSTRUCTION_MD5 = "7f3daf6e8f890a441b82833a91e7c0cd"
PILOT_PROMPTS_MD5 = "f38c08684f93c78a5f6379c3fa05b9b8"
PILOT_JOBS = 3682
SWAP_BUDGETS = (1.0, 0.25, 0.1)


def toy_probe(target="m2", speakers=("A", "B", "A", "B"), roster=("B", "A")) -> FrozenProbe:
    uids = tuple(f"m{i}" for i in range(len(speakers)))
    gold = speakers[uids.index(target)]
    return FrozenProbe(probe_id=f"q:{target}", qid="q", target_uid=target, context_uids=uids,
                       speakers=speakers, gold_author=gold, roster=roster)


TOY_STORE = {"m0": "alpha one", "m1": "beta two", "m2": "alpha three", "m3": "beta four", "m4": "alpha five"}


# --------------------------------------------------------------------------
# pilot fingerprints (slow)
# --------------------------------------------------------------------------

@pytest.mark.slow
def test_pilot_construction_signature_is_unchanged(pilot):
    probes = pilot["probes"]
    sig = "|".join(f"{p.probe_id}:{','.join(p.roster)}" for p in probes)
    assert len(probes) == 542
    assert hashlib.md5(sig.encode()).hexdigest() == PILOT_CONSTRUCTION_MD5


@pytest.mark.slow
def test_pilot_prompts_are_byte_identical(pilot):
    digest, count = hashlib.md5(), 0
    for probe in pilot["probes"]:
        partner = swap_partner(probe)
        for budget, store in pilot["stores"].items():
            digest.update(render_main(probe, store, budget).prompt().encode())
            count += 1
            if partner and budget in SWAP_BUDGETS:
                digest.update(render_swap(probe, store, budget, partner).prompt().encode())
                count += 1
    assert count == PILOT_JOBS
    assert digest.hexdigest() == PILOT_PROMPTS_MD5


@pytest.mark.slow
def test_every_pilot_render_satisfies_invariants(pilot):
    for probe in pilot["probes"]:
        partner = swap_partner(probe)
        for budget in (1.0, 0.1):
            store = pilot["stores"][budget]
            assert check_probe(render_main(probe, store, budget)) == []
            if partner:
                assert check_probe(render_swap(probe, store, budget, partner)) == []


# --------------------------------------------------------------------------
# rendering invariants
# --------------------------------------------------------------------------

def test_target_label_is_hidden_and_others_visible():
    rendered = render_main(toy_probe(), TOY_STORE, 1.0)
    assert rendered.labels == ("A", "B", HIDDEN, "B")
    assert rendered.target_text == "alpha three"


def test_roster_equals_visible_speakers():
    rendered = render_main(toy_probe(), TOY_STORE, 1.0)
    assert set(visible_counts(rendered.labels)) == set(rendered.probe.roster)
    assert check_probe(rendered) == []


def test_check_probe_flags_a_leaked_target_label():
    good = render_main(toy_probe(), TOY_STORE, 1.0)
    leaked = type(good)(good.probe, good.budget, good.condition, good.gold,
                        ("A", "B", "A", "B"), good.texts)
    assert "target label visible" in check_probe(leaked)


def test_swap_preserves_presence_and_counts_and_moves_gold():
    # target m2 (A); visible A: m0, m4 and B: m1, m3 -> equal counts, B is a valid partner
    probe = toy_probe(target="m2", speakers=("A", "B", "A", "B", "A"), roster=("B", "A"))
    partner = swap_partner(probe)
    assert partner == "B"
    main = render_main(probe, TOY_STORE, 1.0)
    swapped = render_swap(probe, TOY_STORE, 1.0, partner)
    assert visible_counts(swapped.labels) == visible_counts(main.labels)
    assert swapped.texts == main.texts
    assert swapped.gold == "B"
    assert swapped.labels == ("B", "A", HIDDEN, "A", "B")


def test_default_toy_probe_has_no_equal_count_partner():
    # target m2 (A) in A,B,A,B -> visible A:1, B:2, so no count-matched swap exists
    assert swap_partner(toy_probe()) is None


def test_swap_partner_requires_equal_label_counts():
    probe = toy_probe(target="m3", speakers=("A", "A", "B", "B"), roster=("A", "B"))
    # A has 2 visible labels, B has 1 (its other message is the target) -> no partner
    assert swap_partner(probe) is None


# --------------------------------------------------------------------------
# grading and baselines
# --------------------------------------------------------------------------

def test_names_match_whole_tokens_only():
    assert names_in_answer("User_13", ["User_1", "User_13"]) == {"User_13"}
    assert names_in_answer("I think User_1 said it.", ["User_1", "User_13"]) == {"User_1"}
    assert names_in_answer("user_1", ["User_1"]) == {"User_1"}


def test_grade_rejects_substring_collisions_and_multi_name_answers():
    probe = toy_probe(roster=("User_1", "User_13"), speakers=("User_1", "User_13", "User_1", "User_13"))
    rendered = render_main(probe, TOY_STORE, 1.0)
    assert grade(rendered, "User_1") == (True, True, "User_1")
    assert grade(rendered, "User_13") == (False, True, "User_13")
    assert grade(rendered, "User_1 or User_13") == (False, False, "")
    assert grade(rendered, "") == (False, False, "")


def test_frequency_baseline_picks_most_labelled_speaker():
    probe = toy_probe(target="m0", speakers=("A", "A", "B", "A"), roster=("A", "B"))
    rendered = render_main(probe, TOY_STORE, 1.0)
    assert frequency_baseline(rendered) == 1.0  # A has 2 visible labels vs B's 1


def test_frequency_baseline_splits_ties():
    rendered = render_main(toy_probe(), TOY_STORE, 1.0)  # A:1, B:2 visible -> B leads
    assert frequency_baseline(rendered) == 0.0
    # target m0 (A); visible A: m1, B: m2 -> a genuine 1:1 tie
    tie = render_main(toy_probe(target="m0", speakers=("A", "A", "B"), roster=("A", "B")), TOY_STORE, 1.0)
    assert frequency_baseline(tie) == 0.5


def test_turn_taking_baseline_excludes_the_neighbouring_speakers():
    # m1 (B) before and m3 (C) after the target -> the guess is A, the only other speaker
    probe = toy_probe(target="m2", speakers=("A", "B", "A", "C", "A"), roster=("A", "B", "C"))
    assert turn_taking_baseline(render_main(probe, TOY_STORE, 1.0)) == 1.0
    # target at the start: only the next turn (B) is a neighbour -> uniform over A, C
    first = toy_probe(target="m0", speakers=("A", "B", "C", "A"), roster=("A", "B", "C"))
    assert turn_taking_baseline(render_main(first, TOY_STORE, 1.0)) == 0.5


TOY_IDF = {"alpha": 2.0, "beta": 2.0, "one": 1.0, "two": 1.0, "three": 1.0, "four": 1.0}


def test_lexical_pick_prefers_the_speaker_with_shared_content():
    rendered = render_main(toy_probe(roster=("B", "A")), TOY_STORE, 1.0)    # target m2 "alpha three"
    assert lexical_pick(rendered, TOY_IDF) == "A"                          # A said "alpha one"


def test_lexical_pick_breaks_ties_by_roster_order():
    rendered = render_main(toy_probe(roster=("B", "A")), {**TOY_STORE, "m2": "gamma"}, 1.0)
    assert lexical_pick(rendered, TOY_IDF) == "B"                          # no overlap: first name


def test_turn_taking_baseline_scores_the_swapped_label_on_the_swap_arm():
    probe = toy_probe(target="m2", speakers=("A", "B", "A", "C", "A", "B"), roster=("A", "B", "C"))
    partner = swap_partner(probe)                      # A and B both have 2 visible labels
    swapped = render_swap(probe, {**TOY_STORE, "m5": "beta six"}, 1.0, partner)
    # labels become B, A, ?, C, B, A: neighbours A and C, so the guess is B = the swapped gold
    assert (partner, swapped.gold, swapped.labels[1]) == ("B", "B", "A")
    assert turn_taking_baseline(swapped) == 1.0
