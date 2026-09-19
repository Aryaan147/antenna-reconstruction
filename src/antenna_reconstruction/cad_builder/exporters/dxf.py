"""DXF export.

Each shape is written twice, deliberately:

* an LWPOLYLINE per ring, which is what a CAD user edits and measures;
* a HATCH whose boundary paths carry the exterior AND its holes, which is what
  makes a slot a void rather than another piece of metal.

Without the hatch, a slotted patch exports as an outline plus several separate
closed polylines, and an importer has no way to tell a hole from an island -
the horse-shoe patch would arrive in an EM solver as five metal pieces instead
of one piece with four slots.
"""
from typing import Any, Dict, List, Optional, Sequence

import ezdxf
from ezdxf.lldxf.const import BOUNDARY_PATH_EXTERNAL, BOUNDARY_PATH_OUTERMOST

from ..models import CADModel, PolygonShape

APPID = "ANTENNA_RECON"
UNIT_CODE = {"mm": 4, "cm": 5, "m": 6}

# Muted, distinguishable ACI colours per layer.
LAYER_COLOUR = {
    "SUBSTRATE": 8, "RADIATOR": 2, "GROUND": 3, "FEED": 1, "0": 7,
}


class DXFExporter:
    def export(self, model: CADModel, filepath: str,
               metadata: Optional[Dict[str, Any]] = None,
               hatch: bool = True) -> bool:
        """Write the model to `filepath`. Returns True on success."""
        try:
            doc = ezdxf.new("R2010", setup=True)
            doc.header["$INSUNITS"] = UNIT_CODE.get(model.unit, 4)
            doc.appids.add(APPID)
            self._write_metadata(doc, model, metadata)

            msp = doc.modelspace()
            for rect in model.rectangles:
                self._layer(doc, rect.layer)
                msp.add_lwpolyline(
                    [(p.x, p.y) for p in rect.vertices], close=True,
                    dxfattribs={"layer": rect.layer},
                )
            for poly in model.polygons:
                self._write_polygon(doc, msp, poly, hatch)

            doc.saveas(filepath)
            return True
        except Exception as exc:  # pragma: no cover - surfaced to the caller
            print(f"Error exporting to DXF: {exc}")
            return False

    @staticmethod
    def _layer(doc, name: str):
        if name not in doc.layers:
            doc.layers.add(name=name, color=LAYER_COLOUR.get(name, 7))
        return doc.layers.get(name)

    @staticmethod
    def _parts(poly: PolygonShape):
        """Group rings into (exterior, holes), honouring ring_roles."""
        roles = poly.ring_roles or (
            ["exterior"] + ["hole"] * (len(poly.rings) - 1)
        )
        grouped: List = []
        current = None
        for ring, role in zip(poly.rings, roles):
            if role == "exterior":
                current = (ring, [])
                grouped.append(current)
            elif current is not None:
                current[1].append(ring)
        return grouped

    def _write_polygon(self, doc, msp, poly: PolygonShape, hatch: bool) -> None:
        self._layer(doc, poly.layer)
        attribs = {"layer": poly.layer}

        for ring in poly.rings:
            if len(ring) < 3:
                continue
            line = msp.add_lwpolyline(
                [(x, y) for x, y in ring], close=True, dxfattribs=attribs
            )
            self._tag(line, poly)

        if not hatch:
            return

        for exterior, holes in self._parts(poly):
            if len(exterior) < 3:
                continue
            h = msp.add_hatch(color=LAYER_COLOUR.get(poly.layer, 7),
                              dxfattribs=attribs)
            h.paths.add_polyline_path(
                [(x, y) for x, y in exterior], is_closed=True,
                flags=BOUNDARY_PATH_EXTERNAL,
            )
            for hole in holes:
                if len(hole) < 3:
                    continue
                h.paths.add_polyline_path(
                    [(x, y) for x, y in hole], is_closed=True,
                    flags=BOUNDARY_PATH_OUTERMOST,
                )
            self._tag(h, poly)

    @staticmethod
    def _tag(entity, poly: PolygonShape) -> None:
        """Attach the shape's identity and derivation, so the DXF is auditable."""
        data = [(1000, poly.id)]
        if poly.derivation:
            # XDATA strings are capped at 255 characters each.
            text = poly.derivation
            while text:
                data.append((1000, text[:250]))
                text = text[250:]
        if poly.thickness:
            data.append((1040, float(poly.thickness)))
        if poly.z:
            data.append((1040, float(poly.z)))
        try:
            entity.set_xdata(APPID, data)
        except Exception:
            pass

    @staticmethod
    def _write_metadata(doc, model: CADModel,
                        metadata: Optional[Dict[str, Any]]) -> None:
        """Record where this geometry came from, in the file itself."""
        custom = doc.header.custom_vars
        custom.append("GENERATOR", "antenna-reconstruction")
        custom.append("UNITS", model.unit)
        if not metadata:
            return
        for key in ("source", "template", "verified"):
            if metadata.get(key) is not None:
                custom.append(key.upper(), str(metadata[key])[:250])
        for key in ("assumptions", "underdetermined", "derivations"):
            for i, line in enumerate(metadata.get(key) or [], start=1):
                custom.append(f"{key.upper()}_{i}", str(line)[:250])
