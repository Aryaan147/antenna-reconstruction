"""The horse-shoe paper: skeleton determined, slots not.

Table 1 gives a size for every slot symbol and a position for none, so the
correct reconstruction is the skeleton plus an explicit report of what could
not be placed.
"""
import pytest

from antenna_reconstruction.geometry.primitives import polygon_bounds
from antenna_reconstruction.templates import HorseShoePatchTemplate
from antenna_reconstruction.templates.base import Layer

TABLE = {
    "L_S": 34.0, "W": 28.0, "L_g": 13.0, "W_f": 2.9, "L_f": 14.0,
    "L_P": 16.0, "W_P": 24.0, "L_SII": 7.12, "W_R": 5.0, "W_RI": 9.0,
    "L_SIII": 2.0, "L_SIV": 1.5, "L_sII": 9.0, "D": 5.0,
}


@pytest.fixture
def result():
    return HorseShoePatchTemplate().build(TABLE)


def test_skeleton_is_built_on_four_layers(result):
    ids = {s.id: s for s in result.shapes}
    assert set(ids) == {"substrate", "patch", "feed", "ground"}
    assert ids["substrate"].layer is Layer.SUBSTRATE
    assert ids["patch"].layer is Layer.RADIATOR
    assert ids["feed"].layer is Layer.FEED
    assert ids["ground"].layer is Layer.GROUND


def test_patch_sits_on_the_feed(result):
    """Any other placement leaves the feed not touching the patch."""
    ids = {s.id: s for s in result.shapes}
    _, _, _, feed_top = polygon_bounds(ids["feed"].rings[0])
    _, patch_bottom, _, patch_top = polygon_bounds(ids["patch"].rings[0])
    assert feed_top == pytest.approx(TABLE["L_f"])
    assert patch_bottom == pytest.approx(TABLE["L_f"])
    assert patch_top - patch_bottom == pytest.approx(TABLE["L_P"])


def test_everything_is_centred_and_fits(result):
    for shape in result.shapes:
        x0, y0, x1, y1 = polygon_bounds(shape.rings[0])
        assert x0 >= -1e-9 and x1 <= TABLE["W"] + 1e-9
        assert y0 >= -1e-9 and y1 <= TABLE["L_S"] + 1e-9
    ids = {s.id: s for s in result.shapes}
    for name in ("patch", "feed"):
        x0, _, x1, _ = polygon_bounds(ids[name].rings[0])
        assert (x0 + x1) / 2 == pytest.approx(TABLE["W"] / 2)


def test_ground_is_partial_and_the_feed_clears_it(result):
    ids = {s.id: s for s in result.shapes}
    x0, y0, x1, y1 = polygon_bounds(ids["ground"].rings[0])
    assert (x1 - x0) == pytest.approx(TABLE["W"])      # full width
    assert (y1 - y0) == pytest.approx(TABLE["L_g"])    # partial height
    assert y1 < TABLE["L_f"]                           # feed reaches past it


def test_slots_are_reported_rather_than_placed(result):
    assert not any("slot" in s.id for s in result.shapes)
    reported = " ".join(result.underdetermined)
    for symbol in ("W_R", "W_RI", "D", "L_SIII", "L_SIV"):
        assert symbol in reported
    assert "crenellation count" in reported


def test_containment_relations_confirm(result):
    assert len(result.verification.confirmed) == 3
    assert not result.verification.refuted


def test_a_patch_too_wide_for_its_substrate_is_refused():
    result = HorseShoePatchTemplate().build(dict(TABLE, W_P=40.0))
    assert not result.shapes
    assert any("does not fit" in d for d in result.diagnostics)
    assert result.verification.refuted


def test_a_stack_taller_than_the_substrate_is_refused():
    result = HorseShoePatchTemplate().build(dict(TABLE, L_P=30.0))
    assert not result.shapes
    assert result.verification.refuted


def test_missing_required_symbols_build_nothing():
    result = HorseShoePatchTemplate().build({"L_S": 34.0, "W": 28.0})
    assert not result.shapes
    assert result.underdetermined == ["entire_structure"]
