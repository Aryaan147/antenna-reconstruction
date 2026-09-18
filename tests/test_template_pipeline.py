import os
import pytest
import ezdxf

from antenna_reconstruction.template_pipeline import TemplatePipeline

HEX_TABLE = {
    "L": 20.0, "W": 20.0, "S1": 6.5, "S2": 5.3, "S3": 4.2, "S4": 4.76,
    "H1": 1.0, "H2": 0.5, "F1": 0.2, "FW": 1.2, "G1": 0.3, "GL": 6.5,
    "FL": 7.5, "W1": 9.1,
}
PAPER = "data/raw/papers/hexagonal_ring_antenna.pdf"


@pytest.fixture
def pipeline():
    return TemplatePipeline()


def test_end_to_end_from_parameters(pipeline, tmp_path):
    out = tmp_path / "hex.dxf"
    result = pipeline.run_from_parameters(HEX_TABLE, str(out), source_id="hex")

    assert result.success and result.verified
    assert result.template == "hexagonal_ring_cpw_monopole"
    assert os.path.exists(out)

    doc = ezdxf.readfile(str(out))
    entities = list(doc.modelspace())
    assert len(entities) >= 4
    layers = {e.dxf.layer for e in entities}
    assert {"SUBSTRATE", "RADIATOR", "FEED"} <= layers
    assert doc.header["$INSUNITS"] == 4  # mm


def test_empty_parameters_fail_without_writing(pipeline, tmp_path):
    out = tmp_path / "nothing.dxf"
    result = pipeline.run_from_parameters({}, str(out))

    assert result.success is False
    assert not os.path.exists(out)


def test_refuted_binding_blocks_the_build(pipeline, tmp_path):
    out = tmp_path / "refuted.dxf"
    result = pipeline.run_from_parameters(dict(HEX_TABLE, H1=3.0), str(out))

    assert result.success is False
    assert result.verification.refuted
    assert any("REFUTED" in d for d in result.diagnostics)
    assert not os.path.exists(out)


def test_unverifiable_family_succeeds_but_is_flagged(pipeline, tmp_path):
    out = tmp_path / "patch.dxf"
    result = pipeline.run_from_parameters({"W": 38.39, "L": 29.89}, str(out))

    assert result.success is True
    assert result.verified is False  # built, but nothing could test the binding
    assert "UNVERIFIED" in result.render()


def test_no_matching_template_is_reported(pipeline, tmp_path):
    out = tmp_path / "none.dxf"
    result = pipeline.run_from_parameters({"Q": 1.0, "Z": 2.0}, str(out))

    assert result.success is False
    assert any("No template is fully satisfied" in d for d in result.diagnostics)


@pytest.mark.skipif(not os.path.exists(PAPER), reason="paper PDF not available")
def test_end_to_end_from_the_real_pdf(pipeline, tmp_path):
    out = tmp_path / "from_pdf.dxf"
    result = pipeline.run_from_pdf(PAPER, str(out))

    assert result.success and result.verified
    # All 14 symbols of Table 1 must survive extraction.
    assert len(result.parameters) == 14
    assert result.parameters["S1"] == 6.5
    assert result.parameters["W1"] == 9.1
    assert any("tapered_ground" in u for u in result.underdetermined)
