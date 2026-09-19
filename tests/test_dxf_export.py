"""DXF export: holes must survive as holes.

Written as separate closed polylines, a slot is indistinguishable from another
piece of metal - the horse-shoe patch would reach an EM solver as five metal
pieces instead of one with four slots. A HATCH carries the exterior and its
holes as one boundary set, which is what makes the difference.
"""
import os
import ezdxf
import pytest
from shapely.geometry import Polygon

from antenna_reconstruction.cad_builder.builder import GeometryBuilder
from antenna_reconstruction.cad_builder.exporters.dxf import APPID, DXFExporter
from antenna_reconstruction.cad_builder.models import BuildStatus
from antenna_reconstruction.templates import get_template
from antenna_reconstruction.templates.base import Layer, Shape, TemplateResult

HEX = {
    "L": 20.0, "W": 20.0, "S1": 6.5, "S2": 5.3, "S3": 4.2, "S4": 4.76,
    "H1": 1.0, "H2": 0.5, "F1": 0.2, "FW": 1.2, "G1": 0.3, "GL": 6.5,
    "FL": 7.5, "W1": 9.1,
}


def _export(template_result, tmp_path, **kwargs):
    build = GeometryBuilder().build_from_template(template_result)
    assert build.status is BuildStatus.BUILT
    path = tmp_path / "out.dxf"
    assert DXFExporter().export(build.model, str(path), **kwargs) is True
    return ezdxf.readfile(str(path)), path


def test_units_are_millimetres(tmp_path):
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    doc, _ = _export(result, tmp_path)
    assert doc.header["$INSUNITS"] == 4


def test_a_ring_exports_as_a_hatch_with_its_hole(tmp_path):
    """The outer ring is an annulus: its hatch must carry two boundary paths."""
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    doc, _ = _export(result, tmp_path)
    hatches = [h for h in doc.modelspace().query("HATCH")
               if h.dxf.layer == "RADIATOR"]
    assert any(len(h.paths) == 2 for h in hatches)


def test_hole_area_is_actually_subtracted(tmp_path):
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    doc, _ = _export(result, tmp_path)
    annulus = next(h for h in doc.modelspace().query("HATCH")
                   if h.dxf.layer == "RADIATOR" and len(h.paths) == 2)
    rings = [Polygon([(v[0], v[1]) for v in p.vertices]) for p in annulus.paths]
    outer, inner = sorted(rings, key=lambda p: -p.area)
    assert inner.area > 0
    assert outer.area - inner.area < outer.area   # the hole removes metal
    # Odd-parity island detection is what turns the inner loop into a hole.
    assert annulus.dxf.hatch_style == 0


def test_disjoint_pieces_get_one_hatch_each(tmp_path):
    """A shape in two pieces must not be hatched as one region with a hole."""
    shape = Shape(
        id="split", layer=Layer.GROUND,
        rings=[[(0, 0), (4, 0), (4, 4), (0, 4)],
               [(6, 0), (10, 0), (10, 4), (6, 4)]],
        ring_roles=["exterior", "exterior"],
    )
    doc, _ = _export(TemplateResult(template="t", shapes=[shape]), tmp_path)
    hatches = list(doc.modelspace().query("HATCH"))
    assert len(hatches) == 2
    assert all(len(h.paths) == 1 for h in hatches)


def test_ring_roles_default_to_exterior_then_holes(tmp_path):
    shape = Shape(
        id="annulus", layer=Layer.RADIATOR,
        rings=[[(0, 0), (10, 0), (10, 10), (0, 10)],
               [(3, 3), (7, 3), (7, 7), (3, 7)]],
    )
    doc, _ = _export(TemplateResult(template="t", shapes=[shape]), tmp_path)
    hatch = next(iter(doc.modelspace().query("HATCH")))
    assert len(hatch.paths) == 2


def test_outlines_are_written_alongside_the_fill(tmp_path):
    """CAD users measure the polylines; solvers use the hatch. Emit both."""
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    doc, _ = _export(result, tmp_path)
    assert doc.modelspace().query("LWPOLYLINE")
    assert doc.modelspace().query("HATCH")


def test_hatch_can_be_turned_off(tmp_path):
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    doc, _ = _export(result, tmp_path, hatch=False)
    assert not doc.modelspace().query("HATCH")
    assert doc.modelspace().query("LWPOLYLINE")


def test_every_entity_carries_its_shape_id_and_derivation(tmp_path):
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    doc, _ = _export(result, tmp_path)
    tagged = 0
    for entity in doc.modelspace():
        xdata = entity.get_xdata(APPID) if entity.has_xdata(APPID) else None
        if xdata:
            tagged += 1
            assert any(code == 1000 and value for code, value in xdata)
    assert tagged == len(list(doc.modelspace()))


def test_provenance_is_recorded_in_the_file(tmp_path):
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    build = GeometryBuilder().build_from_template(result)
    path = tmp_path / "meta.dxf"
    DXFExporter().export(build.model, str(path), metadata={
        "source": "a_paper", "template": "hexagonal_ring_cpw_monopole",
        "verified": True, "assumptions": ["flat-top hexagons"],
        "underdetermined": [], "derivations": [],
    })
    doc = ezdxf.readfile(str(path))
    props = dict(doc.header.custom_vars.properties)
    assert props["GENERATOR"] == "antenna-reconstruction"
    assert props["UNITS"] == "mm"
    assert props["SOURCE"] == "a_paper"
    assert props["VERIFIED"] == "True"
    assert props["ASSUMPTIONS_1"] == "flat-top hexagons"


def test_layers_are_named_after_the_conductor(tmp_path):
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    doc, _ = _export(result, tmp_path)
    names = {layer.dxf.name for layer in doc.layers}
    assert {"SUBSTRATE", "RADIATOR", "FEED", "GROUND"} <= names


def test_export_failure_is_reported_not_raised(tmp_path):
    result = get_template("hexagonal_ring_cpw_monopole").build(HEX)
    build = GeometryBuilder().build_from_template(result)
    bad = tmp_path / "no_such_dir" / "x.dxf"
    assert DXFExporter().export(build.model, str(bad)) is False
