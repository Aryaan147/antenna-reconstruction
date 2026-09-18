"""Deterministic parametric geometry primitives.

Everything here is pure mathematics on already-resolved numbers. No antenna
semantics, no evidence interpretation, no guessing: given exact inputs these
functions return exact outputs, and they raise rather than invent when an
input is unusable.
"""
import math
from typing import List, Optional, Sequence, Tuple

Point = Tuple[float, float]
Ring = List[Point]


class GeometryError(ValueError):
    """Raised when a primitive cannot be constructed from the given inputs."""


def regular_polygon(
    center: Point,
    circumradius: float,
    n_sides: int,
    orientation_deg: float = 0.0,
) -> Ring:
    """Vertices of a regular n-gon, counter-clockwise.

    orientation_deg rotates the polygon; 0 places the first vertex on the +x
    axis from the center ("pointy-right").
    """
    if n_sides < 3:
        raise GeometryError(f"n_sides must be >= 3, got {n_sides}")
    if circumradius <= 0:
        raise GeometryError(f"circumradius must be > 0, got {circumradius}")

    cx, cy = center
    step = 2.0 * math.pi / n_sides
    phase = math.radians(orientation_deg)
    return [
        (cx + circumradius * math.cos(phase + i * step),
         cy + circumradius * math.sin(phase + i * step))
        for i in range(n_sides)
    ]


def circumradius_from_edge(edge_length: float, n_sides: int) -> float:
    """Regular polygon circumradius from its edge length."""
    if n_sides < 3:
        raise GeometryError(f"n_sides must be >= 3, got {n_sides}")
    if edge_length <= 0:
        raise GeometryError(f"edge_length must be > 0, got {edge_length}")
    return edge_length / (2.0 * math.sin(math.pi / n_sides))


def edge_from_circumradius(circumradius: float, n_sides: int) -> float:
    """Inverse of circumradius_from_edge."""
    if n_sides < 3:
        raise GeometryError(f"n_sides must be >= 3, got {n_sides}")
    return 2.0 * circumradius * math.sin(math.pi / n_sides)


def inset_edge_length(edge_length: float, n_sides: int, thickness: float) -> float:
    """Edge length of a regular polygon inset inward by a uniform `thickness`.

    Offsetting a regular n-gon inward by t along its apothem shortens each edge
    by 2t/tan(interior_half_angle). For a hexagon this is the 2t/tan(60 deg)
    relation that Table 1 of the hexagonal-ring paper satisfies.
    """
    if n_sides < 3:
        raise GeometryError(f"n_sides must be >= 3, got {n_sides}")
    half_interior = math.pi * (n_sides - 2) / (2 * n_sides)
    return edge_length - 2.0 * thickness / math.tan(half_interior)


def inset_circumradius(circumradius: float, n_sides: int, thickness: float) -> float:
    """Circumradius of a regular polygon inset inward by a uniform thickness."""
    inner_edge = inset_edge_length(
        edge_from_circumradius(circumradius, n_sides), n_sides, thickness
    )
    if inner_edge <= 0:
        raise GeometryError(
            f"thickness {thickness} collapses the polygon (inner edge {inner_edge})"
        )
    return circumradius_from_edge(inner_edge, n_sides)


# Curves are emitted as polylines. 180 segments keeps the chord error below
# ~0.02% of the radius, which is far under the precision any paper states, and
# it gives EM meshers a single uniform representation to work from.
DEFAULT_CIRCLE_SEGMENTS = 180


def circle(center: Point, radius: float,
           segments: int = DEFAULT_CIRCLE_SEGMENTS) -> Ring:
    """A circle discretised as a closed polyline, counter-clockwise."""
    if radius <= 0:
        raise GeometryError(f"radius must be > 0, got {radius}")
    if segments < 8:
        raise GeometryError(f"segments must be >= 8, got {segments}")
    cx, cy = center
    step = 2.0 * math.pi / segments
    return [
        (cx + radius * math.cos(i * step), cy + radius * math.sin(i * step))
        for i in range(segments)
    ]


def ellipse(center: Point, semi_major: float, semi_minor: float,
            rotation_deg: float = 0.0,
            segments: int = DEFAULT_CIRCLE_SEGMENTS) -> Ring:
    """An ellipse discretised as a closed polyline, counter-clockwise."""
    if semi_major <= 0 or semi_minor <= 0:
        raise GeometryError(
            f"semi-axes must be > 0, got {semi_major}, {semi_minor}"
        )
    if segments < 8:
        raise GeometryError(f"segments must be >= 8, got {segments}")
    cx, cy = center
    phi = math.radians(rotation_deg)
    cos_p, sin_p = math.cos(phi), math.sin(phi)
    step = 2.0 * math.pi / segments
    out: Ring = []
    for i in range(segments):
        x = semi_major * math.cos(i * step)
        y = semi_minor * math.sin(i * step)
        out.append((cx + x * cos_p - y * sin_p, cy + x * sin_p + y * cos_p))
    return out


def equilateral_triangle_height(side: float) -> float:
    """Height of an equilateral triangle from its side length."""
    if side <= 0:
        raise GeometryError(f"side must be > 0, got {side}")
    return side * math.sqrt(3.0) / 2.0


def rectangle(x_left: float, y_bottom: float, x_right: float, y_top: float) -> Ring:
    """Axis-aligned rectangle, counter-clockwise from bottom-left."""
    if x_right <= x_left or y_top <= y_bottom:
        raise GeometryError(
            f"degenerate rectangle: x[{x_left},{x_right}] y[{y_bottom},{y_top}]"
        )
    return [
        (x_left, y_bottom), (x_right, y_bottom),
        (x_right, y_top), (x_left, y_top),
    ]


def polygon_bounds(ring: Sequence[Point]) -> Tuple[float, float, float, float]:
    """(min_x, min_y, max_x, max_y)."""
    if not ring:
        raise GeometryError("cannot take bounds of an empty ring")
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def difference(outer: Sequence[Point], holes: Sequence[Sequence[Point]]) -> List[Ring]:
    """Boolean difference: `outer` minus each ring in `holes`.

    Returns a list of rings: the resulting exterior(s) followed by the
    interior boundaries, which is what a DXF/EM consumer needs in order to
    render a conductor with a void (a ring, a slot, a split).
    """
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    shape = Polygon(outer)
    if not shape.is_valid:
        raise GeometryError("outer ring is not a valid polygon")
    if holes:
        cut = unary_union([Polygon(h) for h in holes])
        shape = shape.difference(cut)

    if shape.is_empty:
        raise GeometryError("difference produced an empty result")

    geoms = list(getattr(shape, "geoms", [shape]))
    rings: List[Ring] = []
    for g in geoms:
        rings.append([(x, y) for x, y in g.exterior.coords[:-1]])
        for interior in g.interiors:
            rings.append([(x, y) for x, y in interior.coords[:-1]])
    return rings


def trapezoid(
    x_left: float, x_right: float, y_bottom: float, y_top: float,
    top_x_left: Optional[float] = None, top_x_right: Optional[float] = None,
) -> Ring:
    """A tapered quadrilateral: full width at the bottom, narrowed at the top.

    Used for tapered ground planes. Both top_x_* must be supplied; a taper with
    an unspecified top edge is underdetermined and must be reported as such by
    the caller rather than defaulted here.
    """
    if top_x_left is None or top_x_right is None:
        raise GeometryError(
            "trapezoid requires an explicit top edge (top_x_left, top_x_right); "
            "an unspecified taper is underdetermined"
        )
    if y_top <= y_bottom:
        raise GeometryError(f"degenerate trapezoid height: [{y_bottom},{y_top}]")
    return [
        (x_left, y_bottom), (x_right, y_bottom),
        (top_x_right, y_top), (top_x_left, y_top),
    ]
