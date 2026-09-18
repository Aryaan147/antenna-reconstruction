import pytest

from antenna_reconstruction.binding.verifier import (
    CheckOutcome, Relation, rounding_tolerance, verify,
)

HEX = {"W": 20.0, "FW": 1.2, "G1": 0.3, "W1": 9.1, "S1": 6.5, "H1": 1.0, "S2": 5.3}


def _feed_centered() -> Relation:
    return Relation(
        name="feed_is_centered", target="W1", requires=["W", "FW", "G1"],
        description="ground inner edge to substrate edge",
        predict=lambda v: v["W"] / 2 - v["FW"] / 2 - v["G1"],
    )


def test_tolerance_follows_stated_precision():
    # "5.3" asserts far less than "4.76" does.
    assert rounding_tolerance(5.3) == pytest.approx(0.05)
    assert rounding_tolerance(4.76) == pytest.approx(0.005)
    assert rounding_tolerance(20.0) == pytest.approx(0.05)


def test_correct_binding_is_confirmed():
    report = verify(HEX, [_feed_centered()])
    assert report.results[0].outcome is CheckOutcome.CONFIRMED
    assert report.ok


def test_wrong_binding_is_refuted():
    # Mis-bind G1 as if it were the feed width: the arithmetic no longer closes.
    bad = Relation(
        name="wrong", target="W1", requires=["W", "FW", "G1"],
        description="deliberately wrong binding",
        predict=lambda v: v["W"] / 2 - v["G1"] / 2 - v["FW"],
    )
    report = verify(HEX, [bad])
    assert report.results[0].outcome is CheckOutcome.REFUTED
    assert not report.ok


def test_missing_symbols_are_skipped_not_passed():
    report = verify({"W": 20.0}, [_feed_centered()])
    assert report.results[0].outcome is CheckOutcome.SKIPPED
    assert "FW" in report.results[0].missing
    # Skipping is not evidence of correctness.
    assert not report.ok


def test_no_relations_is_unverified_not_verified():
    report = verify(HEX, [])
    assert not report.refuted
    assert not report.ok  # nothing confirmed => unverified


def test_relation_that_raises_is_refuted_not_ignored():
    boom = Relation(
        name="boom", target="W1", requires=["W"],
        description="raises", predict=lambda v: 1 / 0,
    )
    report = verify(HEX, [boom])
    assert report.results[0].outcome is CheckOutcome.REFUTED
