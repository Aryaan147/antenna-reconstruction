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
def skeleton():
    """Determined geometry only: no figure-derived detail."""
    return HorseShoePatchTemplate(use_figure_outline=False).build(TABLE)


@pytest.fixture
def traced():
    """Slots cut using outlines traced from Fig. 1."""
    return HorseShoePatchTemplate(use_figure_outline=True).build(TABLE)


def test_skeleton_is_built_on_four_layers(skeleton):
    ids = {s.id: s for s in skeleton.shapes}
    assert set(ids) == {"substrate", "patch", "feed", "ground"}
    assert ids["substrate"].layer is Layer.SUBSTRATE
    assert ids["patch"].layer is Layer.RADIATOR
    assert ids["feed"].layer is Layer.FEED
    assert ids["ground"].layer is Layer.GROUND


def test_patch_sits_on_the_feed(skeleton):
    """Any other placement leaves the feed not touching the patch."""
    ids = {s.id: s for s in skeleton.shapes}
    _, _, _, feed_top = polygon_bounds(ids["feed"].rings[0])
    _, patch_bottom, _, patch_top = polygon_bounds(ids["patch"].rings[0])
    assert feed_top == pytest.approx(TABLE["L_f"])
    assert patch_bottom == pytest.approx(TABLE["L_f"])
    assert patch_top - patch_bottom == pytest.approx(TABLE["L_P"])


def test_everything_is_centred_and_fits(skeleton):
    for shape in skeleton.shapes:
        x0, y0, x1, y1 = polygon_bounds(shape.rings[0])
        assert x0 >= -1e-9 and x1 <= TABLE["W"] + 1e-9
        assert y0 >= -1e-9 and y1 <= TABLE["L_S"] + 1e-9
    ids = {s.id: s for s in skeleton.shapes}
    for name in ("patch", "feed"):
        x0, _, x1, _ = polygon_bounds(ids[name].rings[0])
        assert (x0 + x1) / 2 == pytest.approx(TABLE["W"] / 2)


def test_ground_is_partial_and_the_feed_clears_it(skeleton):
    ids = {s.id: s for s in skeleton.shapes}
    x0, y0, x1, y1 = polygon_bounds(ids["ground"].rings[0])
    assert (x1 - x0) == pytest.approx(TABLE["W"])      # full width
    assert (y1 - y0) == pytest.approx(TABLE["L_g"])    # partial height
    assert y1 < TABLE["L_f"]                           # feed reaches past it


def test_skeleton_mode_reports_slots_rather_than_placing_them(skeleton):
    assert not any("slot" in s.id for s in skeleton.shapes)
    reported = " ".join(skeleton.underdetermined)
    for symbol in ("W_R", "W_RI", "D", "L_SIII", "L_SIV"):
        assert symbol in reported
    assert "crenellation count" in reported


def test_traced_mode_cuts_the_slots(traced):
    """The horse-shoe slots and crenellations must actually appear."""
    patch = [s for s in traced.shapes if s.id == "patch"][0]
    # A plain rectangle would be 4 points; the slotted outline is far richer.
    assert len(patch.rings[0]) > 30
    from shapely.geometry import Polygon
    poly = Polygon(patch.rings[0])
    x0, y0, x1, y1 = polygon_bounds(patch.rings[0])
    # Slots and crenellations remove a substantial part of the bounding box.
    assert poly.area < 0.75 * (x1 - x0) * (y1 - y0)


def test_traced_mode_still_honours_the_stated_outer_dimensions(traced):
    patch = [s for s in traced.shapes if s.id == "patch"][0]
    x0, y0, x1, y1 = polygon_bounds(patch.rings[0])
    assert x1 - x0 == pytest.approx(TABLE["W_P"], abs=1e-6)
    assert y1 - y0 == pytest.approx(TABLE["L_f"] + TABLE["L_P"], abs=1e-6)
    assert (x0 + x1) / 2 == pytest.approx(TABLE["W"] / 2, abs=1e-6)

    ground = [s for s in traced.shapes if s.id == "ground"][0]
    gx0, gy0, gx1, gy1 = polygon_bounds(ground.rings[0])
    assert gx1 - gx0 == pytest.approx(TABLE["W"], abs=1e-6)
    assert gy1 - gy0 == pytest.approx(TABLE["L_g"], abs=1e-6)


def test_traced_mode_declares_that_the_slots_are_figure_derived(traced):
    """A reader must not mistake traced pixels for stated dimensions."""
    assert any("FIGURE-DERIVED" in a for a in traced.assumptions)
    assert any("could not be checked" in u for u in traced.underdetermined)


def test_everything_stays_inside_the_substrate_when_traced(traced):
    for shape in traced.shapes:
        for ring in shape.rings:
            x0, y0, x1, y1 = polygon_bounds(ring)
            assert x0 >= -1e-6 and x1 <= TABLE["W"] + 1e-6
            assert y0 >= -1e-6 and y1 <= TABLE["L_S"] + 1e-6


def test_containment_relations_confirm(traced):
    assert len(traced.verification.confirmed) == 3
    assert not traced.verification.refuted


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
