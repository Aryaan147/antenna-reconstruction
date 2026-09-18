import math
import pytest

from antenna_reconstruction.geometry.primitives import (
    GeometryError, circle, ellipse, equilateral_triangle_height, polygon_bounds,
)
from antenna_reconstruction.templates import (
    AnnularRingTemplate, CircularPatchTemplate, PatchArrayTemplate,
    TriangularPatchTemplate,
)


def test_circle_area_converges():
    ring = circle((0.0, 0.0), 10.0)
    from shapely.geometry import Polygon
    assert Polygon(ring).area == pytest.approx(math.pi * 100, rel=1e-3)


def test_circle_rejects_bad_inputs():
    with pytest.raises(GeometryError):
        circle((0.0, 0.0), -1.0)
    with pytest.raises(GeometryError):
        circle((0.0, 0.0), 5.0, segments=3)


def test_ellipse_bounds_match_its_semi_axes():
    x0, y0, x1, y1 = polygon_bounds(ellipse((0.0, 0.0), 10.0, 4.0))
    assert (x1 - x0) == pytest.approx(20.0, rel=1e-3)
    assert (y1 - y0) == pytest.approx(8.0, rel=1e-3)


def test_equilateral_height():
    assert equilateral_triangle_height(20.0) == pytest.approx(17.3205, abs=1e-4)


def test_circular_patch_confirms_diameter_relation():
    result = CircularPatchTemplate().build(
        {"R": 12.5, "D": 25.0, "SW": 50.0, "SL": 50.0}
    )
    assert result.verification.ok
    x0, y0, x1, y1 = polygon_bounds(
        [s for s in result.shapes if s.id == "patch"][0].rings[0]
    )
    assert (x1 - x0) == pytest.approx(25.0, rel=1e-3)
    assert (x0 + x1) / 2 == pytest.approx(25.0, rel=1e-6)  # centred


def test_circular_patch_refutes_a_wrong_diameter():
    result = CircularPatchTemplate().build({"R": 12.5, "D": 30.0})
    assert result.verification.refuted


def test_annular_ring_confirms_width_and_has_a_hole():
    result = AnnularRingTemplate().build({"RO": 15.0, "RI": 10.0, "WR": 5.0})
    assert result.verification.ok
    ring = [s for s in result.shapes if s.id == "ring"][0]
    assert len(ring.rings) == 2  # exterior plus hole


def test_annular_ring_rejects_an_impossible_radius_pair():
    result = AnnularRingTemplate().build({"RO": 10.0, "RI": 15.0})
    assert not result.shapes
    assert any("not smaller" in d for d in result.diagnostics)


def test_triangular_patch_confirms_height_relation():
    result = TriangularPatchTemplate().build({"ST": 20.0, "HT": 17.32})
    assert result.verification.ok
    patch = [s for s in result.shapes if s.id == "patch"][0]
    assert len(patch.rings[0]) == 3
    x0, y0, x1, y1 = polygon_bounds(patch.rings[0])
    assert (y1 - y0) == pytest.approx(17.3205, abs=1e-3)


def test_array_places_the_right_number_of_elements():
    result = PatchArrayTemplate().build({
        "W": 10.0, "L": 8.0, "NX": 4, "NY": 2, "DX": 20.0, "DY": 15.0,
        "SW": 100.0, "SL": 60.0,
    })
    elements = [s for s in result.shapes if s.id.startswith("element_")]
    assert len(elements) == 8
    assert result.verification.ok


def test_array_elements_are_spaced_exactly():
    result = PatchArrayTemplate().build({
        "W": 10.0, "L": 8.0, "NX": 3, "NY": 1, "DX": 20.0, "DY": 15.0,
    })
    centres = sorted(
        (polygon_bounds(s.rings[0])[0] + polygon_bounds(s.rings[0])[2]) / 2
        for s in result.shapes if s.id.startswith("element_")
    )
    assert centres[1] - centres[0] == pytest.approx(20.0)
    assert centres[2] - centres[1] == pytest.approx(20.0)


def test_array_refutes_spacing_that_would_overlap_elements():
    result = PatchArrayTemplate().build({
        "W": 30.0, "L": 8.0, "NX": 2, "NY": 1, "DX": 10.0, "DY": 15.0,
    })
    assert result.verification.refuted


def test_missing_substrate_is_reported_for_every_family():
    for template, values in [
        (CircularPatchTemplate(), {"R": 5.0}),
        (AnnularRingTemplate(), {"RO": 5.0, "RI": 2.0}),
        (TriangularPatchTemplate(), {"ST": 5.0}),
    ]:
        result = template.build(values)
        assert any("substrate" in u for u in result.underdetermined)
