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
import json
import os
from typing import Dict, List, Optional

from ..binding.verifier import Relation
from ..geometry.feeds import microstrip_line
from ..geometry.primitives import GeometryError, rectangle
from .base import Layer, Shape, Template, TemplateResult

# Slot symbols: each gives an extent but never a location.
SLOT_SYMBOLS = ("W_R", "W_RI", "D", "L_SII", "L_SIII", "L_SIV", "L_sII")

OUTLINE_PATH = os.path.join(
    os.path.dirname(__file__), "figure_outlines", "horse_shoe.json"
)


def load_figure_outline() -> Optional[dict]:
    """The metal outlines traced from Fig. 1, or None if unavailable.

    These are FIGURE-DERIVED. Coordinates are fractions of each shape's own
    bounding box, so they rescale onto the stated outer dimensions - but the
    internal feature sizes come from pixels, not from any stated dimension,
    and the figure is only about 10% faithful to the table.
    """
    try:
        with open(OUTLINE_PATH) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _place(outline: dict, x0: float, y0: float, width: float,
           height: float) -> List[List]:
    """Map a normalised outline onto a rectangle in millimetres.

    An outline may have several disjoint parts: the ground plane is split in
    two by the feed passing between them.
    """
    def ring(points):
        return [(x0 + px * width, y0 + py * height) for px, py in points]

    rings: List[List] = []
    for part in outline["parts"]:
        rings.append(ring(part["exterior"]))
        rings.extend(ring(h) for h in part["holes"])
    return rings


# How far the figure may disagree with the table before it is worth reporting.
# The figure is a drawing, not a measurement, so some slack is expected.
FIGURE_TOLERANCE = 0.12


def _check_figure_against_table(outline: dict, result, expected: dict) -> None:
    """Report where the figure's own proportions contradict the stated ones.

    The traced outline is rescaled onto the table's dimensions, so a
    disagreement is silently absorbed by the stretch. Surfacing it is the only
    way a reader learns that the two sources of truth do not agree.
    """
    for name, (want_w, want_h) in expected.items():
        fraction = outline.get(name, {}).get("substrate_fraction")
        if not fraction:
            continue
        for axis, stated, seen in (("width", want_w, fraction["width"]),
                                   ("height", want_h, fraction["height"])):
            if stated <= 0:
                continue
            error = abs(seen - stated) / stated
            line = (f"{name} {axis}: the table implies {stated:.3f} of the "
                    f"board, Fig. 1 draws {seen:.3f} ({error:.0%} apart)")
            if error > FIGURE_TOLERANCE:
                result.diagnostics.append(
                    "figure contradicts the table - " + line +
                    "; the stated dimension was used and the traced outline "
                    "stretched to fit it"
                )
            else:
                result.assumptions.append("figure agrees with the table - " + line)


class HorseShoePatchTemplate(Template):
    name: str = "horse_shoe_patch"
    required: List[str] = ["L_S", "W", "L_P", "W_P", "L_g", "W_f", "L_f"]
    optional: List[str] = list(SLOT_SYMBOLS)
    # Cut the slots using outlines traced from Fig. 1. Off by default would
    # give the determined skeleton only; on, the shape matches the paper but
    # its internal features are figure-derived rather than stated.
    use_figure_outline: bool = True

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

        outline = load_figure_outline() if self.use_figure_outline else None

        if outline is not None:
            _check_figure_against_table(outline, result, {
                "patch": (W_P / W, (L_f + L_P) / L_S),
                "ground": (1.0, L_g / L_S),
            })
            # The traced gold covers patch and feed as one piece, from the
            # board edge up to the patch top.
            result.shapes.append(Shape(
                id="patch", layer=Layer.RADIATOR,
                rings=_place(outline["patch"], cx - W_P / 2.0, 0.0,
                             W_P, L_f + L_P),
                derivation=(
                    "patch and feed outline TRACED FROM Fig. 1, rescaled to "
                    f"W_P={W_P} x (L_f+L_P)={L_f + L_P}; slots and "
                    "crenellations are figure-derived, not stated"
                ),
            ))
            result.shapes.append(Shape(
                id="ground", layer=Layer.GROUND,
                rings=_place(outline["ground"], 0.0, 0.0, W, L_g),
                derivation=(
                    "ground outline TRACED FROM Fig. 1, rescaled to "
                    f"W={W} x L_g={L_g}; cut-outs are figure-derived"
                ),
            ))
            result.assumptions.append(
                "SLOT GEOMETRY IS FIGURE-DERIVED: the U-slots, crenellations "
                "and ground cut-outs are traced from Fig. 1 and rescaled onto "
                "the stated outer dimensions. Their sizes come from pixels, "
                "not from any stated dimension, and Fig. 1 is only about 10% "
                "faithful to Table 1 (its ground reads ~11.7 mm against a "
                "stated L_g of 13)"
            )
            result.underdetermined.append(
                "slot dimensions: " + ", ".join(SLOT_SYMBOLS) + " are stated as "
                "sizes but no statement places them, so the traced positions "
                "could not be checked against them"
            )
        else:
            try:
                result.shapes.append(Shape(
                    id="patch", layer=Layer.RADIATOR,
                    rings=[rectangle(cx - W_P / 2.0, patch_y,
                                     cx + W_P / 2.0, patch_y + L_P)],
                    derivation=f"patch W_P={W_P} x L_P={L_P}, lower edge at y=L_f",
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
                    derivation=f"partial ground, full width W={W}, L_g={L_g}",
                ))
            except GeometryError as exc:
                result.diagnostics.append(f"ground: {exc}")

            present = [s for s in SLOT_SYMBOLS if s in values]
            if present:
                result.underdetermined.append(
                    "slot placement: " + ", ".join(present) + " each give a size "
                    "but no paper statement gives a position, so the U-slots, "
                    "the crenellated patch edge and the shaped ground cut-outs "
                    "are not cut"
                )
            result.underdetermined.append(
                "crenellation count: the figure shows repeated notches along "
                "the patch edge but no symbol states how many"
            )

        result.assumptions.append(
            "the partial ground spans the full substrate width and lies on the "
            "reverse side (Fig. 1 overlays both faces)"
        )
        return result
