"""Hexagonal-ring CPW-fed monopole (two nested split rings over a tapered ground).

Symbol binding for this family, each item CONFIRMED against the paper's own
numbers by binding.verifier rather than assumed:

  L,  W   substrate length / width
  S1, S2  outer ring: outer and inner hexagon edge, trace width H1
  S4, S3  inner ring: outer and inner hexagon edge, trace width H2
  F1      split gap in the inner ring
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
    rectangle, regular_polygon,
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
                description="ground inner edge to substrate edge, feed on the x-midline",
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

        split = values.get("F1")
        if split is None:
            result.underdetermined.append("inner_ring_split (F1 absent)")
        else:
            result.assumptions.append(
                "the inner ring's F1 split is centred on its bottom edge (Fig. 2)"
            )
        try:
            result.shapes.append(self._ring(
                shape_id="inner_ring", center=(cx, cy),
                outer_edge=S4, thickness=H2, split_gap=split,
                derivation=f"regular hexagon edge S4={S4}, inset by H2={H2}",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"inner_ring: {exc}")
        result.assumptions.append("the two rings are concentric (Fig. 2)")

        try:
            result.shapes.append(Shape(
                id="feed", layer=Layer.FEED,
                rings=[rectangle(cx - FW / 2.0, 0.0, cx + FW / 2.0, FL)],
                derivation=f"feed line FW={FW} wide, FL={FL} long, on the x-midline",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"feed: {exc}")

        # The tapered ground is genuinely not determined by Table 1: GL gives its
        # height and G1/W1 give its inner edge, but nothing fixes where the taper
        # starts or its slope. Reporting that is the correct outcome.
        result.underdetermined.append(
            "tapered_ground: GL, G1 and W1 fix the height and inner edge, but the "
            "taper's slope and apex are not given by any symbol; 2 more values "
            "(or an explicit relationship) are required"
        )

        return result

    def _verify(self, values: Dict[str, float]):
        from ..binding.verifier import verify
        return verify(values, self.relations())

    @staticmethod
    def _ring(shape_id: str, center, outer_edge: float, thickness: float,
              derivation: str, split_gap=None) -> Shape:
        """A hexagonal annulus, optionally split by a gap in its bottom edge.

        The split is cut in the SAME boolean operation as the ring's hole, so
        the annulus is always treated as one polygon-with-hole rather than as
        two independent rings.
        """
        cx, cy = center
        r_out = circumradius_from_edge(outer_edge, N)
        r_in = inset_circumradius(r_out, N, thickness)

        cutters = [regular_polygon(center, r_in, N)]
        if split_gap is not None and split_gap > 0:
            cos_half = math.cos(math.pi / N)
            apothem_out, apothem_in = r_out * cos_half, r_in * cos_half
            eps = max(thickness, split_gap) * 1e-3
            cutters.append(rectangle(
                cx - split_gap / 2.0, cy - apothem_out - eps,
                cx + split_gap / 2.0, cy - apothem_in + eps,
            ))
            derivation += f"; split by F1={split_gap} at the bottom edge"

        return Shape(
            id=shape_id, layer=Layer.RADIATOR,
            rings=difference(regular_polygon(center, r_out, N), cutters),
            derivation=derivation,
        )
