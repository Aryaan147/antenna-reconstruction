import pytest

from antenna_reconstruction.geometry.primitives import polygon_bounds
from antenna_reconstruction.templates import (
    HexagonalRingTemplate, RectangularPatchTemplate, rank_templates,
)
from antenna_reconstruction.templates.base import Layer

# Table 1 of the hexagonal-ring paper, verbatim.
HEX_TABLE = {
    "L": 20.0, "W": 20.0, "S1": 6.5, "S2": 5.3, "S3": 4.2, "S4": 4.76,
    "H1": 1.0, "H2": 0.5, "F1": 0.2, "FW": 1.2, "G1": 0.3, "GL": 6.5,
    "FL": 7.5, "W1": 9.1,
}


@pytest.fixture
def hex_result():
    return HexagonalRingTemplate().build(HEX_TABLE)


def test_all_declared_relations_are_confirmed(hex_result):
    report = hex_result.verification
    assert len(report.confirmed) == 3
    assert not report.refuted
    assert report.ok


def test_shapes_are_built_with_layers(hex_result):
    ids = {s.id: s for s in hex_result.shapes}
    assert set(ids) == {
        "substrate", "outer_ring", "inner_arc", "stub", "feed",
        "ground_left", "ground_right",
    }
    assert ids["substrate"].layer is Layer.SUBSTRATE
    assert ids["outer_ring"].layer is Layer.RADIATOR
    assert ids["inner_arc"].layer is Layer.RADIATOR
    assert ids["feed"].layer is Layer.FEED
    assert ids["ground_left"].layer is Layer.GROUND


def test_everything_fits_inside_the_substrate(hex_result):
    W, L = HEX_TABLE["W"], HEX_TABLE["L"]
    for shape in hex_result.shapes:
        for ring in shape.rings:
            x0, y0, x1, y1 = polygon_bounds(ring)
            assert x0 >= -1e-9 and y0 >= -1e-9
            assert x1 <= W + 1e-9 and y1 <= L + 1e-9


def test_outer_ring_is_closed_but_the_inner_arc_is_not(hex_result):
    """Fig. 2 shows the inner structure open at the top, not a closed ring."""
    ids = {s.id: s for s in hex_result.shapes}
    assert len(ids["outer_ring"].rings) == 2   # exterior plus hole
    assert len(ids["inner_arc"].rings) == 1    # open arc encloses nothing


def test_inner_arc_is_cut_at_the_hexagon_centre_line(hex_result):
    """Its top must sit at the centre of the ring assembly, where Fig. 2 ends it."""
    ids = {s.id: s for s in hex_result.shapes}
    _, oy0, _, oy1 = polygon_bounds(ids["outer_ring"].rings[0])
    _, _, _, arc_top = polygon_bounds(ids["inner_arc"].rings[0])
    assert arc_top == pytest.approx((oy0 + oy1) / 2, abs=1e-6)


def test_f1_is_a_stub_width_not_a_gap(hex_result):
    """The paper calls F1 the "thickness of stub feed"; it must appear as metal."""
    stub = [s for s in hex_result.shapes if s.id == "stub"][0]
    x0, _, x1, _ = polygon_bounds(stub.rings[0])
    assert x1 - x0 == pytest.approx(HEX_TABLE["F1"], abs=1e-6)
    assert (x0 + x1) / 2 == pytest.approx(HEX_TABLE["W"] / 2, abs=1e-6)


def test_ring_trace_width_matches_the_table(hex_result):
    """Measure the built trace width instead of trusting the inset formula.

    For a flat-top hexagon the bounding-box height is twice the apothem, so the
    difference of the two apothems is the trace width - which must be H1.
    """
    outer = [s for s in hex_result.shapes if s.id == "outer_ring"][0]
    _, oy0, _, oy1 = polygon_bounds(outer.rings[0])
    _, hy0, _, hy1 = polygon_bounds(outer.rings[1])
    apothem_outer, apothem_inner = (oy1 - oy0) / 2, (hy1 - hy0) / 2
    assert apothem_outer - apothem_inner == pytest.approx(HEX_TABLE["H1"], abs=1e-6)


def test_feed_is_centred_and_correctly_sized(hex_result):
    feed = [s for s in hex_result.shapes if s.id == "feed"][0]
    x0, y0, x1, y1 = polygon_bounds(feed.rings[0])
    assert (x0 + x1) / 2 == pytest.approx(HEX_TABLE["W"] / 2)
    assert x1 - x0 == pytest.approx(HEX_TABLE["FW"])
    assert y1 - y0 == pytest.approx(HEX_TABLE["FL"])


def test_tapered_ground_is_built_with_base_w1_and_height_gl(hex_result):
    """Fig. 2 fixes the taper: apex at the substrate corner, inner edge GL tall."""
    grounds = [s for s in hex_result.shapes if s.layer is Layer.GROUND]
    assert len(grounds) == 2
    for g in grounds:
        x0, y0, x1, y1 = polygon_bounds(g.rings[0])
        assert x1 - x0 == pytest.approx(HEX_TABLE["W1"], abs=1e-6)
        assert y1 - y0 == pytest.approx(HEX_TABLE["GL"], abs=1e-6)
        assert y0 == pytest.approx(0.0, abs=1e-9)


def test_ground_clears_the_feed_by_g1(hex_result):
    ids = {s.id: s for s in hex_result.shapes}
    fx0, _, fx1, _ = polygon_bounds(ids["feed"].rings[0])
    _, _, lx1, _ = polygon_bounds(ids["ground_left"].rings[0])
    gx0, _, _, _ = polygon_bounds(ids["ground_right"].rings[0])
    assert fx0 - lx1 == pytest.approx(HEX_TABLE["G1"], abs=1e-6)
    assert gx0 - fx1 == pytest.approx(HEX_TABLE["G1"], abs=1e-6)


def test_nothing_is_left_undetermined_for_this_paper(hex_result):
    """Every part of Fig. 2 is fixed by Table 1 once the figure is read correctly."""
    assert hex_result.underdetermined == []
    assert hex_result.diagnostics == []


def test_assumptions_are_recorded(hex_result):
    assert hex_result.assumptions
    assert any("flat-top" in a for a in hex_result.assumptions)


def test_missing_required_symbols_refuse_to_build():
    result = HexagonalRingTemplate().build({"L": 20.0, "W": 20.0})
    assert not result.shapes
    assert result.underdetermined == ["entire_structure"]


def test_refuted_binding_is_surfaced():
    """Corrupting H1 must break the redundancy check rather than pass silently."""
    bad = dict(HEX_TABLE, H1=3.0)
    report = HexagonalRingTemplate().build(bad).verification
    assert report.refuted
    assert not report.ok


def test_patch_without_substrate_reports_position_as_undetermined():
    result = RectangularPatchTemplate().build({"W": 38.39, "L": 29.89})
    assert any("substrate" in u for u in result.underdetermined)
    assert [s.id for s in result.shapes] == ["patch"]
    # No relation exists for this family, so it must not claim verification.
    assert not result.verification.ok


def test_patch_with_substrate_is_centred():
    result = RectangularPatchTemplate().build(
        {"W": 10.0, "L": 20.0, "SW": 30.0, "SL": 40.0}
    )
    patch = [s for s in result.shapes if s.id == "patch"][0]
    x0, y0, x1, y1 = polygon_bounds(patch.rings[0])
    assert (x0 + x1) / 2 == pytest.approx(15.0)
    assert (y0 + y1) / 2 == pytest.approx(20.0)


def test_ranking_prefers_the_fully_satisfied_specific_template():
    assert rank_templates(HEX_TABLE)[0][0] == "hexagonal_ring_cpw_monopole"
    assert rank_templates({"W": 1.0, "L": 2.0})[0][0] == "rectangular_patch"
