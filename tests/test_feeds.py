import pytest

from antenna_reconstruction.geometry.feeds import (
    feed_to_patch_gap, inset_feed_length, inset_notches, microstrip_line,
)
from antenna_reconstruction.geometry.primitives import GeometryError, polygon_bounds
from antenna_reconstruction.templates import RectangularPatchTemplate

# The microstrip paper: 76.8 x 57.8 substrate, 39.4 x 28.9 patch, 3.1 feed.
# Its figure also annotates a 23.7 mm feed with a 9.25 mm inset.
MICROSTRIP = {"W": 39.4, "L": 28.9, "SW": 76.8, "SL": 57.8, "FW": 3.1}


def test_microstrip_line_is_centred_and_sized():
    x0, y0, x1, y1 = polygon_bounds(microstrip_line(10.0, 0.0, 5.0, 2.0))
    assert (x0 + x1) / 2 == pytest.approx(10.0)
    assert x1 - x0 == pytest.approx(2.0)
    assert y1 - y0 == pytest.approx(5.0)


def test_degenerate_feeds_raise():
    with pytest.raises(GeometryError):
        microstrip_line(0.0, 0.0, 5.0, 0.0)
    with pytest.raises(GeometryError):
        microstrip_line(0.0, 5.0, 5.0, 2.0)


def test_inset_length_identity_matches_the_paper():
    """(57.8 - 28.9)/2 + 9.25 = 23.7, exactly what the figure annotates."""
    assert feed_to_patch_gap(57.8, 28.9) == pytest.approx(14.45)
    assert inset_feed_length(57.8, 28.9, 9.25) == pytest.approx(23.7)


def test_patch_too_big_for_its_substrate_raises():
    with pytest.raises(GeometryError):
        feed_to_patch_gap(20.0, 30.0)


def test_two_notches_are_cut_symmetrically():
    left, right = inset_notches(10.0, 5.0, 2.0, 1.0, 3.0)
    lx0, ly0, lx1, ly1 = polygon_bounds(left)
    rx0, _, rx1, _ = polygon_bounds(right)
    assert lx1 == pytest.approx(9.0) and rx0 == pytest.approx(11.0)
    assert (lx1 - lx0) == pytest.approx(1.0) == (rx1 - rx0)
    assert (ly1 - ly0) == pytest.approx(3.0)


def test_feed_line_is_built_when_the_substrate_fixes_its_start():
    result = RectangularPatchTemplate().build(MICROSTRIP)
    feed = [s for s in result.shapes if s.id == "feed"][0]
    x0, y0, x1, y1 = polygon_bounds(feed.rings[0])
    assert x1 - x0 == pytest.approx(3.1)
    assert y0 == pytest.approx(0.0)
    assert y1 == pytest.approx(14.45)  # reaches the patch edge
    assert any("inset depth" in u for u in result.underdetermined)


def test_no_substrate_means_no_feed():
    result = RectangularPatchTemplate().build({"W": 39.4, "L": 28.9, "FW": 3.1})
    assert not any(s.id == "feed" for s in result.shapes)
    assert any("no edge for the feed line" in u for u in result.underdetermined)


def test_no_feed_width_means_no_feed():
    result = RectangularPatchTemplate().build(
        {"W": 39.4, "L": 28.9, "SW": 76.8, "SL": 57.8}
    )
    assert not any(s.id == "feed" for s in result.shapes)
    assert any("no feed width" in u for u in result.underdetermined)


def test_inset_feed_confirms_its_length_relation():
    result = RectangularPatchTemplate().build(
        dict(MICROSTRIP, FI=9.25, FG=1.0, FL=23.7)
    )
    assert result.verification.ok
    feed = [s for s in result.shapes if s.id == "feed"][0]
    _, _, _, y1 = polygon_bounds(feed.rings[0])
    assert y1 == pytest.approx(23.7)


def test_a_wrong_inset_depth_is_refuted():
    result = RectangularPatchTemplate().build(
        dict(MICROSTRIP, FI=5.0, FG=1.0, FL=23.7)
    )
    assert result.verification.refuted


def test_a_partial_inset_specification_is_reported_not_assumed():
    result = RectangularPatchTemplate().build(dict(MICROSTRIP, FI=9.25))
    assert any("inset feed" in u for u in result.underdetermined)
