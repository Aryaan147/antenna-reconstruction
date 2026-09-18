"""Hexagonal-ring CPW-fed monopole (two nested split rings over a tapered ground).

Symbol binding for this family, each item CONFIRMED against the paper's own
numbers by binding.verifier rather than assumed:

  L,  W   substrate length / width
  S1, S2  outer ring: outer and inner hexagon edge, trace width H1
  S4, S3  inner ring: outer and inner hexagon edge, trace width H2
  F1      width of the narrow stub connecting the inner arc to the feed
          (the paper calls it "thickness of stub feed", not a gap)
  FW, FL  feed width / length
  G1      coplanar gap between feed and ground
  GL      ground height
  W1      ground inner edge to substrate edge  (= W/2 - FW/2 - G1)
"""
import math
from typing import Dict, List

from ..binding.verifier import Relation
from ..geometry.primitives import (
    GeometryError, circumradius_from_edge, difference, inset_circumradius,
    rectangle, regular_polygon, triangle, union,
)
from .base import Layer, Shape, Template, TemplateResult

N = 6  # hexagon


class HexagonalRingTemplate(Template):
    name: str = "hexagonal_ring_cpw_monopole"
    required: List[str] = ["L", "W", "S1", "H1", "S4", "H2", "FW", "FL"]
    optional: List[str] = ["S2", "S3", "F1", "G1", "GL", "W1"]

    def relations(self) -> List[Relation]:
        from ..geometry.primitives import inset_edge_length

        return [
            Relation(
                name="outer_ring_inset",
                target="S2",
                requires=["S1", "H1"],
                description="inner edge of outer ring = S1 inset by trace width H1",
                predict=lambda v: inset_edge_length(v["S1"], N, v["H1"]),
            ),
            Relation(
                name="inner_ring_inset",
                target="S3",
                requires=["S4", "H2"],
                description="inner edge of inner ring = S4 inset by trace width H2",
                predict=lambda v: inset_edge_length(v["S4"], N, v["H2"]),
            ),
            Relation(
                name="feed_is_centered",
                target="W1",
                requires=["W", "FW", "G1"],
                description=(
                    "ground taper base: substrate edge to ground inner edge, "
                    "feed on the x-midline"
                ),
                predict=lambda v: v["W"] / 2.0 - v["FW"] / 2.0 - v["G1"],
            ),
        ]

    def build(self, values: Dict[str, float]) -> TemplateResult:
        result = TemplateResult(template=self.name)

        missing = self.missing_required(values)
        if missing:
            result.diagnostics.append(
                f"missing required symbols: {', '.join(missing)}"
            )
            result.underdetermined.append("entire_structure")
            return result

        result.verification = self._verify(values)

        L, W = values["L"], values["W"]
        S1, H1 = values["S1"], values["H1"]
        S4, H2 = values["S4"], values["H2"]
        FW, FL = values["FW"], values["FL"]

        # Origin at the substrate's bottom-left, y up (CAD convention).
        result.shapes.append(Shape(
            id="substrate", layer=Layer.SUBSTRATE,
            rings=[rectangle(0.0, 0.0, W, L)],
            derivation="substrate = W x L anchored at origin",
        ))

        cx = W / 2.0
        result.assumptions.append(
            "feed and rings lie on the substrate x-midline "
            "(CONFIRMED by the W1 relation where G1 and W1 are present)"
        )

        # Flat-top hexagon: vertices left/right, horizontal top and bottom edges,
        # matching Fig. 2. orientation 0 puts the first vertex on +x.
        r_outer = circumradius_from_edge(S1, N)
        apothem_outer = r_outer * math.cos(math.pi / N)
        result.assumptions.append(
            "hexagons are flat-top (vertices left/right), read from Fig. 2"
        )

        # Anchor the ring stack vertically on the feed: the feed runs from the
        # substrate's bottom edge to the bottom of the outer ring.
        cy = FL + apothem_outer
        result.assumptions.append(
            "ring assembly sits directly on top of the feed, so the outer ring's "
            "bottom edge is at y = FL (read from Fig. 2; no table value fixes it)"
        )

        try:
            result.shapes.append(self._ring(
                shape_id="outer_ring", center=(cx, cy),
                outer_edge=S1, thickness=H1,
                derivation=f"regular hexagon edge S1={S1}, inset by H1={H1}",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"outer_ring: {exc}")

        # The inner structure is NOT a closed ring. Fig. 2 shows only the
        # lower-left, bottom and lower-right edges, with blunt ends at the
        # hexagon's left and right vertices, joined to the feed by a narrow
        # stub of width F1.
        try:
            result.shapes.append(self._lower_arc(
                shape_id="inner_arc", center=(cx, cy),
                outer_edge=S4, thickness=H2,
                derivation=f"lower half of a hexagon edge S4={S4}, inset by H2={H2}",
            ))
            result.assumptions.append(
                "the inner arc spans the hexagon's lower three edges, cut at the "
                "left/right vertices (Fig. 2)"
            )
        except GeometryError as exc:
            result.diagnostics.append(f"inner_arc: {exc}")

        if "F1" in values:
            try:
                result.shapes.append(self._stub(
                    center=(cx, cy), outer_edge=S1, outer_thickness=H1,
                    inner_edge=S4, width=values["F1"],
                ))
            except GeometryError as exc:
                result.diagnostics.append(f"stub: {exc}")
        else:
            result.underdetermined.append(
                "stub connecting the inner arc to the feed (F1 absent)"
            )
        result.assumptions.append("the two hexagons are concentric (Fig. 2)")

        try:
            result.shapes.append(Shape(
                id="feed", layer=Layer.FEED,
                rings=[rectangle(cx - FW / 2.0, 0.0, cx + FW / 2.0, FL)],
                derivation=f"feed line FW={FW} wide, FL={FL} long, on the x-midline",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"feed: {exc}")

        # The tapered ground planes ARE determined: Fig. 2 shows each as a right
        # triangle whose apex is the substrate's bottom outer corner and whose
        # vertical inner edge has height GL, standing G1 clear of the feed. Its
        # base is exactly W1, which the feed_is_centered relation confirms.
        if "GL" in values and "G1" in values:
            GL, G1 = values["GL"], values["G1"]
            x_left = cx - FW / 2.0 - G1
            x_right = cx + FW / 2.0 + G1
            result.assumptions.append(
                "each ground plane tapers linearly from the substrate's bottom "
                "outer corner to a vertical inner edge of height GL (Fig. 2)"
            )
            for shape_id, x_inner, x_outer in (
                ("ground_left", x_left, 0.0), ("ground_right", x_right, W),
            ):
                try:
                    result.shapes.append(Shape(
                        id=shape_id, layer=Layer.GROUND,
                        rings=[triangle((x_outer, 0.0), (x_inner, 0.0),
                                        (x_inner, GL))],
                        derivation=(
                            f"tapered ground: base {abs(x_inner - x_outer):.4f} "
                            f"(= W1), height GL={GL}, G1={G1} clear of the feed"
                        ),
                    ))
                except GeometryError as exc:
                    result.diagnostics.append(f"{shape_id}: {exc}")
        else:
            result.underdetermined.append(
                "tapered_ground: GL and/or G1 are absent, so the ground taper's "
                "height and inner edge are not determined"
            )

        return result

    def _verify(self, values: Dict[str, float]):
        from ..binding.verifier import verify
        return verify(values, self.relations())

    @staticmethod
    def _ring(shape_id: str, center, outer_edge: float, thickness: float,
              derivation: str) -> Shape:
        """A closed hexagonal annulus."""
        r_out = circumradius_from_edge(outer_edge, N)
        r_in = inset_circumradius(r_out, N, thickness)
        return Shape(
            id=shape_id, layer=Layer.RADIATOR,
            rings=difference(regular_polygon(center, r_out, N),
                             [regular_polygon(center, r_in, N)]),
            derivation=derivation,
        )

    @staticmethod
    def _lower_arc(shape_id: str, center, outer_edge: float, thickness: float,
                   derivation: str) -> Shape:
        """The lower half of a hexagonal annulus: three edges, open at the top.

        Cutting at the centre line passes exactly through the hexagon's left
        and right vertices, which is where Fig. 2 shows the arc terminating.
        """
        cx, cy = center
        r_out = circumradius_from_edge(outer_edge, N)
        r_in = inset_circumradius(r_out, N, thickness)
        upper_half = rectangle(cx - 2 * r_out, cy, cx + 2 * r_out, cy + 2 * r_out)
        return Shape(
            id=shape_id, layer=Layer.RADIATOR,
            rings=difference(
                regular_polygon(center, r_out, N),
                [regular_polygon(center, r_in, N), upper_half],
            ),
            derivation=derivation + "; cut at the centre line, open at the top",
        )

    @staticmethod
    def _stub(center, outer_edge: float, outer_thickness: float,
              inner_edge: float, width: float) -> Shape:
        """The narrow bar of width F1 joining the inner arc down to the feed."""
        if width <= 0:
            raise GeometryError(f"stub width must be > 0, got {width}")
        cx, cy = center
        cos_half = math.cos(math.pi / N)

        r_outer_in = inset_circumradius(
            circumradius_from_edge(outer_edge, N), N, outer_thickness
        )
        y_bottom = cy - r_outer_in * cos_half          # outer ring's inner edge
        y_top = cy - circumradius_from_edge(inner_edge, N) * cos_half
        if y_top <= y_bottom:
            raise GeometryError(
                "the inner arc does not sit inside the outer ring; the symbols "
                "cannot mean what this template assumes"
            )
        eps = width * 1e-3
        bar = rectangle(cx - width / 2.0, y_bottom - eps,
                        cx + width / 2.0, y_top + eps)
        return Shape(
            id="stub", layer=Layer.RADIATOR, rings=union([bar]),
            derivation=(
                f"stub feed of width F1={width} bridging "
                f"{y_top - y_bottom:.4f} mm between the outer ring and inner arc"
            ),
        )
