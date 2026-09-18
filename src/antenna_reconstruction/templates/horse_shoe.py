"""Horse-shoe (U-slotted) patch monopole over a partial ground.

Symbols follow the horse-shoe paper's Table 1:

  L_S, W        substrate length / width
  L_P, W_P      radiating patch length / width
  L_g           partial ground length, measured up from the substrate edge
  W_f, L_f      feed width / length
  W_R, W_RI, D  the two U-slot widths and the slot-end diameter
  L_SII..L_SIV  slot and crenellation depths

Only the skeleton is determined. Every slot symbol gives a SIZE and no paper
statement gives its POSITION, so the U-slots, the crenellated patch edge and
the shaped ground cut-outs are reported rather than placed. The figure shows
where they go, but reading positions off a figure that is not drawn to scale
would be measuring pixels, which the stated dimensions outrank.
"""
from typing import Dict, List

from ..binding.verifier import Relation
from ..geometry.feeds import microstrip_line
from ..geometry.primitives import GeometryError, rectangle
from .base import Layer, Shape, Template, TemplateResult

# Slot symbols: each gives an extent but never a location.
SLOT_SYMBOLS = ("W_R", "W_RI", "D", "L_SII", "L_SIII", "L_SIV", "L_sII")


class HorseShoePatchTemplate(Template):
    name: str = "horse_shoe_patch"
    required: List[str] = ["L_S", "W", "L_P", "W_P", "L_g", "W_f", "L_f"]
    optional: List[str] = list(SLOT_SYMBOLS)

    def relations(self) -> List[Relation]:
        # These are containment bounds, not redundancies: they catch a symbol
        # bound to the wrong quantity but they do not prove a correct binding,
        # because they pass for any set of sane numbers.
        return [
            Relation(
                name="patch_fits_substrate", target="W", requires=["W_P"],
                description="W >= W_P (the patch fits across the substrate)",
                predict=lambda v: max(v["W"], v["W_P"]),
            ),
            Relation(
                name="stack_fits_substrate", target="L_S", requires=["L_f", "L_P"],
                description="L_S >= L_f + L_P (feed and patch fit up the board)",
                predict=lambda v: max(v["L_S"], v["L_f"] + v["L_P"]),
            ),
            Relation(
                name="feed_clears_ground", target="L_f", requires=["L_g"],
                description="L_f >= L_g (the feed reaches past the partial ground)",
                predict=lambda v: max(v["L_f"], v["L_g"]),
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

        L_S, W = values["L_S"], values["W"]
        L_P, W_P = values["L_P"], values["W_P"]
        L_g, W_f, L_f = values["L_g"], values["W_f"], values["L_f"]

        if W_P > W or L_f + L_P > L_S:
            result.diagnostics.append(
                f"patch {W_P} x {L_P} plus a {L_f} feed does not fit on a "
                f"{W} x {L_S} substrate; the symbols cannot mean what this "
                "template assumes"
            )
            return result

        cx = W / 2.0
        try:
            result.shapes.append(Shape(
                id="substrate", layer=Layer.SUBSTRATE,
                rings=[rectangle(0.0, 0.0, W, L_S)],
                derivation=f"substrate W={W} x L_S={L_S} anchored at origin",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"substrate: {exc}")

        # The patch must sit on top of the feed, or the two would not touch.
        # That places the unstated slack (L_S - L_f - L_P) above the patch,
        # which is where the figure shows it.
        patch_y = L_f
        result.assumptions.append(
            "the patch sits directly on top of the feed, so its lower edge is "
            "at y = L_f; nothing states the gap, and any other placement would "
            "leave the feed not touching the patch"
        )
        result.assumptions.append(
            "the patch and feed are centred on the substrate's x-midline; no "
            "symbol states an offset"
        )

        try:
            result.shapes.append(Shape(
                id="patch", layer=Layer.RADIATOR,
                rings=[rectangle(cx - W_P / 2.0, patch_y,
                                 cx + W_P / 2.0, patch_y + L_P)],
                derivation=f"patch W_P={W_P} x L_P={L_P}, lower edge at y=L_f={L_f}",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"patch: {exc}")

        try:
            result.shapes.append(Shape(
                id="feed", layer=Layer.FEED,
                rings=[microstrip_line(cx, 0.0, L_f, W_f)],
                derivation=f"feed W_f={W_f} wide, L_f={L_f} long, on the x-midline",
            ))
        except GeometryError as exc:
            result.diagnostics.append(f"feed: {exc}")

        try:
            result.shapes.append(Shape(
                id="ground", layer=Layer.GROUND,
                rings=[rectangle(0.0, 0.0, W, L_g)],
                derivation=(
                    f"partial ground, full width W={W}, L_g={L_g} up from the "
                    "substrate edge, on the reverse side"
                ),
            ))
            result.assumptions.append(
                "the partial ground spans the full substrate width and lies on "
                "the reverse side (Fig. 1 overlays both faces)"
            )
        except GeometryError as exc:
            result.diagnostics.append(f"ground: {exc}")

        present = [s for s in SLOT_SYMBOLS if s in values]
        if present:
            result.underdetermined.append(
                "slot placement: " + ", ".join(present) + " each give a size but "
                "no paper statement gives a position, so the U-slots, the "
                "crenellated patch edge and the shaped ground cut-outs are not cut"
            )
        result.underdetermined.append(
            "crenellation count: the figure shows repeated notches along the "
            "patch edge but no symbol states how many"
        )

        return result
