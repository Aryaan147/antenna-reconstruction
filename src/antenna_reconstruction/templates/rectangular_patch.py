"""Rectangular microstrip patch on a rectangular substrate.

The most common antenna family in the literature. Symbols:

  W,  L    patch width / length
  SW, SL   substrate width / length (optional)

When substrate dimensions are absent the patch is still exact, but its
POSITION relative to a substrate is not determined, and that is reported
rather than defaulted.
"""
from typing import Dict, List

from ..binding.verifier import Relation
from ..geometry.primitives import GeometryError, rectangle
from .base import Layer, Shape, Template, TemplateResult


class RectangularPatchTemplate(Template):
    name: str = "rectangular_patch"
    required: List[str] = ["W", "L"]
    optional: List[str] = ["SW", "SL"]

    def relations(self) -> List[Relation]:
        # This family carries no intrinsic redundancy: W and L are independent.
        # An empty relation set means "unverifiable", which the caller must
        # surface - it is explicitly NOT the same as "verified".
        return []

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

        try:
            result.shapes.append(Shape(
                id="patch", layer=Layer.RADIATOR,
                rings=[rectangle(x0, y0, x0 + W, y0 + L)],
                derivation=f"patch W={W} x L={L}",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"patch: {exc}")

        return result

    def _verify(self, values: Dict[str, float]):
        from ..binding.verifier import verify
        return verify(values, self.relations())
