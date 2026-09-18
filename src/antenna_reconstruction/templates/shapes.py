"""Additional antenna families: circular patch, annular ring, triangular patch, array.

Each declares whatever redundancy its family offers. Three of the four carry a
genuine arithmetic identity, so a mis-binding of their symbols is caught before
any geometry is built:

    circular patch     D  = 2R
    annular ring       WR = RO - RI
    triangular patch   HT = ST * sqrt(3)/2
"""
import math
from typing import Dict, List

from ..binding.verifier import Relation
from ..geometry.primitives import (
    GeometryError, circle, difference, equilateral_triangle_height, rectangle,
    regular_polygon,
)
from .base import Layer, Shape, Template, TemplateResult


def _substrate(values: Dict[str, float], result: TemplateResult):
    """Emit a substrate when its extents are stated; report it when they are not."""
    if "SW" in values and "SL" in values:
        SW, SL = values["SW"], values["SL"]
        result.shapes.append(Shape(
            id="substrate", layer=Layer.SUBSTRATE,
            rings=[rectangle(0.0, 0.0, SW, SL)],
            derivation=f"substrate SW={SW} x SL={SL} anchored at origin",
        ))
        result.assumptions.append(
            "the radiator is centred on the substrate (standard for this family; "
            "no symbol states an offset)"
        )
        return SW / 2.0, SL / 2.0
    result.underdetermined.append(
        "substrate: no SW/SL symbols were found, so the radiator's position on a "
        "substrate is not determined; it is emitted about the origin"
    )
    return 0.0, 0.0


class CircularPatchTemplate(Template):
    """Circular microstrip patch. Symbols: R (radius), optional D (diameter)."""
    name: str = "circular_patch"
    required: List[str] = ["R"]
    optional: List[str] = ["D", "SW", "SL"]

    def relations(self) -> List[Relation]:
        return [Relation(
            name="diameter_is_twice_radius", target="D", requires=["R"],
            description="D = 2R",
            predict=lambda v: 2.0 * v["R"],
        )]

    def build(self, values: Dict[str, float]) -> TemplateResult:
        result = TemplateResult(template=self.name)
        missing = self.missing_required(values)
        if missing:
            result.diagnostics.append(f"missing required symbols: {', '.join(missing)}")
            result.underdetermined.append("entire_structure")
            return result

        from ..binding.verifier import verify
        result.verification = verify(values, self.relations())
        cx, cy = _substrate(values, result)

        try:
            result.shapes.append(Shape(
                id="patch", layer=Layer.RADIATOR,
                rings=[circle((cx, cy), values["R"])],
                derivation=f"circular patch R={values['R']}, polyline-approximated",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"patch: {exc}")
        return result


class AnnularRingTemplate(Template):
    """Circular annular ring. Symbols: RO, RI (outer/inner radius), optional WR."""
    name: str = "annular_ring"
    required: List[str] = ["RO", "RI"]
    optional: List[str] = ["WR", "SW", "SL"]

    def relations(self) -> List[Relation]:
        return [Relation(
            name="ring_width", target="WR", requires=["RO", "RI"],
            description="WR = RO - RI",
            predict=lambda v: v["RO"] - v["RI"],
        )]

    def build(self, values: Dict[str, float]) -> TemplateResult:
        result = TemplateResult(template=self.name)
        missing = self.missing_required(values)
        if missing:
            result.diagnostics.append(f"missing required symbols: {', '.join(missing)}")
            result.underdetermined.append("entire_structure")
            return result

        from ..binding.verifier import verify
        result.verification = verify(values, self.relations())

        RO, RI = values["RO"], values["RI"]
        if RI >= RO:
            result.diagnostics.append(
                f"inner radius RI={RI} is not smaller than outer radius RO={RO}; "
                "the symbols cannot mean what this template assumes"
            )
            return result

        cx, cy = _substrate(values, result)
        try:
            result.shapes.append(Shape(
                id="ring", layer=Layer.RADIATOR,
                rings=difference(circle((cx, cy), RO), [circle((cx, cy), RI)]),
                derivation=f"annular ring RO={RO}, RI={RI}",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"ring: {exc}")
        return result


class TriangularPatchTemplate(Template):
    """Equilateral triangular patch. Symbols: ST (side), optional HT (height)."""
    name: str = "triangular_patch"
    required: List[str] = ["ST"]
    optional: List[str] = ["HT", "SW", "SL"]

    def relations(self) -> List[Relation]:
        return [Relation(
            name="equilateral_height", target="HT", requires=["ST"],
            description="HT = ST * sqrt(3)/2",
            predict=lambda v: equilateral_triangle_height(v["ST"]),
        )]

    def build(self, values: Dict[str, float]) -> TemplateResult:
        result = TemplateResult(template=self.name)
        missing = self.missing_required(values)
        if missing:
            result.diagnostics.append(f"missing required symbols: {', '.join(missing)}")
            result.underdetermined.append("entire_structure")
            return result

        from ..binding.verifier import verify
        from ..geometry.primitives import circumradius_from_edge
        result.verification = verify(values, self.relations())
        cx, cy = _substrate(values, result)

        try:
            # orientation 90 puts one vertex up and a horizontal base, as drawn
            # in essentially every paper using this family.
            result.shapes.append(Shape(
                id="patch", layer=Layer.RADIATOR,
                rings=[regular_polygon(
                    (cx, cy), circumradius_from_edge(values["ST"], 3), 3,
                    orientation_deg=90.0,
                )],
                derivation=f"equilateral triangle side ST={values['ST']}, apex up",
            ))
            result.assumptions.append("the triangle is apex-up with a horizontal base")
        except GeometryError as exc:
            result.diagnostics.append(f"patch: {exc}")
        return result


class PatchArrayTemplate(Template):
    """Planar array of identical rectangular patches.

    Symbols: W, L (element), NX, NY (counts), DX, DY (centre-to-centre spacing).
    """
    name: str = "rectangular_patch_array"
    required: List[str] = ["W", "L", "NX", "NY", "DX", "DY"]
    optional: List[str] = ["SW", "SL"]

    def relations(self) -> List[Relation]:
        # Spacing must at least clear the element, or the symbols are mis-bound.
        return [
            Relation(
                name="x_spacing_clears_element", target="DX", requires=["W"],
                description="DX >= W (elements must not overlap)",
                predict=lambda v: max(v["DX"], v["W"]),
            ),
            Relation(
                name="y_spacing_clears_element", target="DY", requires=["L"],
                description="DY >= L (elements must not overlap)",
                predict=lambda v: max(v["DY"], v["L"]),
            ),
        ]

    def build(self, values: Dict[str, float]) -> TemplateResult:
        result = TemplateResult(template=self.name)
        missing = self.missing_required(values)
        if missing:
            result.diagnostics.append(f"missing required symbols: {', '.join(missing)}")
            result.underdetermined.append("entire_structure")
            return result

        from ..binding.verifier import verify
        result.verification = verify(values, self.relations())

        nx, ny = int(round(values["NX"])), int(round(values["NY"]))
        if nx < 1 or ny < 1:
            result.diagnostics.append(f"element counts must be >= 1, got {nx}x{ny}")
            return result

        W, L, DX, DY = values["W"], values["L"], values["DX"], values["DY"]
        cx, cy = _substrate(values, result)

        span_x, span_y = (nx - 1) * DX, (ny - 1) * DY
        x0, y0 = cx - span_x / 2.0, cy - span_y / 2.0

        for iy in range(ny):
            for ix in range(nx):
                ex, ey = x0 + ix * DX, y0 + iy * DY
                try:
                    result.shapes.append(Shape(
                        id=f"element_{ix}_{iy}", layer=Layer.RADIATOR,
                        rings=[rectangle(ex - W / 2, ey - L / 2,
                                         ex + W / 2, ey + L / 2)],
                        derivation=(
                            f"array element ({ix},{iy}) at ({ex:.4f}, {ey:.4f}), "
                            f"W={W} x L={L}"
                        ),
                    ))
                except GeometryError as exc:
                    result.diagnostics.append(f"element_{ix}_{iy}: {exc}")
        return result
