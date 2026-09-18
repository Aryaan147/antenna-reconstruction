"""Rectangular microstrip patch on a rectangular substrate.

The most common antenna family in the literature. Symbols:

  W,  L    patch width / length
  SW, SL   substrate width / length (optional)
  FW       microstrip feed width (optional)
  FI, FG   inset depth and slot gap for an inset feed (optional)
  FL       total feed length, when the paper states it (optional)

When substrate dimensions are absent the patch is still exact, but its
POSITION relative to a substrate is not determined, and that is reported
rather than defaulted. The feed follows the same rule: the line is emitted
only when the substrate fixes where it must start and end.
"""
from typing import Dict, List

from ..binding.verifier import Relation
from ..geometry.feeds import (
    apply_inset, feed_to_patch_gap, inset_feed_length, microstrip_line,
)
from ..geometry.primitives import GeometryError, rectangle
from .base import Layer, Shape, Template, TemplateResult


class RectangularPatchTemplate(Template):
    name: str = "rectangular_patch"
    required: List[str] = ["W", "L"]
    optional: List[str] = ["SW", "SL", "FW", "FI", "FG", "FL"]

    def relations(self) -> List[Relation]:
        # A bare patch carries no redundancy: W and L are independent, and an
        # empty relation set means "unverifiable", which is NOT "verified".
        # An inset feed does add one, so a paper that states its feed length
        # becomes checkable.
        return [Relation(
            name="inset_feed_length", target="FL",
            requires=["SL", "L", "FI"],
            description="FL = (SL - L)/2 + FI (line reaches the patch, then insets)",
            predict=lambda v: inset_feed_length(v["SL"], v["L"], v["FI"]),
        )]

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
        W, L = values["W"], values["L"]

        has_substrate = "SW" in values and "SL" in values
        if has_substrate:
            SW, SL = values["SW"], values["SL"]
            try:
                result.shapes.append(Shape(
                    id="substrate", layer=Layer.SUBSTRATE,
                    rings=[rectangle(0.0, 0.0, SW, SL)],
                    derivation=f"substrate SW={SW} x SL={SL} anchored at origin",
                ))
            except GeometryError as exc:
                result.diagnostics.append(f"substrate: {exc}")
            x0, y0 = (SW - W) / 2.0, (SL - L) / 2.0
            result.assumptions.append(
                "the patch is centred on the substrate (standard for this family; "
                "no symbol in the table fixes its offset)"
            )
        else:
            x0, y0 = 0.0, 0.0
            result.underdetermined.append(
                "substrate: no substrate width/length symbols were found, so the "
                "patch's position on a substrate is not determined; the patch is "
                "emitted anchored at the origin"
            )

        result.underdetermined.append(
            "reverse-side ground plane: this family is a microstrip antenna, so "
            "a ground sheet on the back of the substrate is implied. No paper "
            "figure shows it (they are front views) and no symbol gives its "
            "extent, so it is neither drawn nor assumed to be full-sheet"
        )

        patch_ring = None
        try:
            patch_ring = rectangle(x0, y0, x0 + W, y0 + L)
        except GeometryError as exc:
            result.diagnostics.append(f"patch: {exc}")

        if patch_ring is not None:
            self._add_feed(result, values, has_substrate, patch_ring,
                           cx=x0 + W / 2.0, patch_y_bottom=y0)

        return result

    def _add_feed(self, result: TemplateResult, values: Dict[str, float],
                  has_substrate: bool, patch_ring, cx: float,
                  patch_y_bottom: float) -> None:
        """Emit the feed line, and inset the patch, where the symbols allow."""
        W, L = values["W"], values["L"]
        rings = [patch_ring]
        derivation = f"patch W={W} x L={L}"

        feed_width = values.get("FW")
        inset = values.get("FI")
        gap = values.get("FG")

        if inset is not None and gap is not None and feed_width is not None:
            try:
                rings = apply_inset(patch_ring, cx, patch_y_bottom,
                                    feed_width, gap, inset)
                derivation += f"; inset by FI={inset} with FG={gap} slots"
            except GeometryError as exc:
                result.diagnostics.append(f"inset: {exc}")
        elif inset is not None or gap is not None:
            result.underdetermined.append(
                "inset feed: an inset needs FW, FI and FG together; only "
                f"{sorted(k for k in ('FW', 'FI', 'FG') if values.get(k) is not None)} "
                "were found"
            )

        result.shapes.append(Shape(
            id="patch", layer=Layer.RADIATOR, rings=rings,
            derivation=derivation,
        ))

        if feed_width is None:
            result.underdetermined.append(
                "feed: no feed width (FW) is stated, so the feed line is not built"
            )
            return
        if not has_substrate:
            result.underdetermined.append(
                "feed: without substrate dimensions there is no edge for the "
                "feed line to start from, so it is not built"
            )
            return

        try:
            y_end = patch_y_bottom + (inset or 0.0)
            result.shapes.append(Shape(
                id="feed", layer=Layer.FEED,
                rings=[microstrip_line(cx, 0.0, y_end, feed_width)],
                derivation=(
                    f"microstrip line FW={feed_width} wide, running "
                    f"{y_end:.4f} mm from the substrate edge"
                    + (f" and {inset} into the patch" if inset else
                       " to the patch edge")
                ),
            ))
            if inset is None:
                result.underdetermined.append(
                    "inset depth (FI): the feed is drawn only as far as the "
                    "patch edge; how far it insets is not stated"
                )
        except GeometryError as exc:
            result.diagnostics.append(f"feed: {exc}")

    def _verify(self, values: Dict[str, float]):
        from ..binding.verifier import verify
        return verify(values, self.relations())
