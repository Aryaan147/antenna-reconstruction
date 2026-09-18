import math
import pytest

from antenna_reconstruction.geometry.primitives import (
    GeometryError, circumradius_from_edge, difference, edge_from_circumradius,
    inset_circumradius, inset_edge_length, polygon_bounds, rectangle,
    regular_polygon, trapezoid,
)


def test_hexagon_circumradius_equals_edge():
    # Special property of the hexagon; a useful independent check on the formula.
    assert circumradius_from_edge(6.5, 6) == pytest.approx(6.5)
    assert edge_from_circumradius(6.5, 6) == pytest.approx(6.5)


def test_regular_polygon_is_regular():
    ring = regular_polygon((0.0, 0.0), 5.0, 6)
    assert len(ring) == 6
    edges = [
        math.dist(ring[i], ring[(i + 1) % 6]) for i in range(6)
    ]
    assert all(e == pytest.approx(edges[0]) for e in edges)


def test_inset_matches_the_papers_published_values():
    # Table 1 of the hexagonal-ring paper: S1=6.5, H1=1 -> S2=5.3 (1 d.p.),
    # and S4=4.76, H2=0.5 -> S3=4.2. This is the redundancy the binding
    # verifier relies on, so it is pinned here independently.
    assert inset_edge_length(6.5, 6, 1.0) == pytest.approx(5.3, abs=0.05)
    assert inset_edge_length(4.76, 6, 0.5) == pytest.approx(4.2, abs=0.05)


def test_inset_that_collapses_the_polygon_raises():
    with pytest.raises(GeometryError):
        inset_circumradius(circumradius_from_edge(1.0, 6), 6, 10.0)


def test_degenerate_rectangle_raises():
    with pytest.raises(GeometryError):
        rectangle(5.0, 0.0, 5.0, 10.0)


def test_difference_produces_an_annulus():
    outer = regular_polygon((0.0, 0.0), 6.5, 6)
    inner = regular_polygon((0.0, 0.0), 5.0, 6)
    rings = difference(outer, [inner])
    assert len(rings) == 2  # exterior + hole


def test_difference_can_split_an_annulus_open():
    outer = regular_polygon((0.0, 0.0), 6.5, 6)
    inner = regular_polygon((0.0, 0.0), 5.0, 6)
    # The cutter must span the whole trace: the bottom edges sit at the two
    # apothems, -6.5*cos30 = -5.629 and -5.0*cos30 = -4.330.
    cutter = rectangle(-0.1, -7.0, 0.1, -4.0)
    rings = difference(outer, [inner, cutter])
    assert len(rings) == 1  # a C shape has no enclosed hole


def test_partial_cut_leaves_the_annulus_closed():
    outer = regular_polygon((0.0, 0.0), 6.5, 6)
    inner = regular_polygon((0.0, 0.0), 5.0, 6)
    cutter = rectangle(-0.1, -7.0, 0.1, -5.0)  # stops short of the inner edge
    assert len(difference(outer, [inner, cutter])) == 2


def test_polygon_bounds():
    assert polygon_bounds(rectangle(1.0, 2.0, 4.0, 8.0)) == (1.0, 2.0, 4.0, 8.0)


def test_taper_without_an_explicit_top_edge_refuses_to_guess():
    with pytest.raises(GeometryError):
        trapezoid(0.0, 10.0, 0.0, 5.0)
