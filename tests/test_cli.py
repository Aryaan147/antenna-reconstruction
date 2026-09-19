import json
import os
import ezdxf
import pytest

from antenna_reconstruction.cli import main

HEX = {
    "L": 20.0, "W": 20.0, "S1": 6.5, "S2": 5.3, "S3": 4.2, "S4": 4.76,
    "H1": 1.0, "H2": 0.5, "F1": 0.2, "FW": 1.2, "G1": 0.3, "GL": 6.5,
    "FL": 7.5, "W1": 9.1,
}
PAPER = "data/raw/papers/hexagonal_ring_antenna.pdf"


@pytest.fixture
def params_file(tmp_path):
    path = tmp_path / "hex.json"
    path.write_text(json.dumps(HEX))
    return path


def test_list_templates(capsys):
    assert main(["--list-templates"]) == 0
    out = capsys.readouterr().out
    assert "hexagonal_ring_cpw_monopole" in out
    assert "requires:" in out


def test_builds_a_dxf_from_a_parameter_file(params_file, tmp_path):
    out = tmp_path / "hex.dxf"
    assert main(["-p", str(params_file), "-o", str(out)]) == 0
    assert out.exists()
    doc = ezdxf.readfile(str(out))
    assert doc.modelspace().query("HATCH")
    assert doc.header["$INSUNITS"] == 4


def test_output_defaults_to_the_input_name(params_file):
    assert main(["-p", str(params_file)]) == 0
    assert params_file.with_suffix(".dxf").exists()


def test_quiet_prints_only_the_path(params_file, tmp_path, capsys):
    out = tmp_path / "q.dxf"
    assert main(["-p", str(params_file), "-o", str(out), "-q"]) == 0
    assert capsys.readouterr().out.strip() == str(out)


def test_no_hatch_writes_outlines_only(params_file, tmp_path):
    out = tmp_path / "nohatch.dxf"
    assert main(["-p", str(params_file), "-o", str(out), "--no-hatch"]) == 0
    doc = ezdxf.readfile(str(out))
    assert not doc.modelspace().query("HATCH")
    assert doc.modelspace().query("LWPOLYLINE")


def test_a_forced_template_is_honoured(params_file, tmp_path):
    out = tmp_path / "forced.dxf"
    assert main(["-p", str(params_file), "-o", str(out),
                 "-t", "hexagonal_ring_cpw_monopole"]) == 0
    assert out.exists()


def test_unbuildable_input_fails_without_writing(tmp_path, capsys):
    empty = tmp_path / "none.json"
    empty.write_text(json.dumps({"Q": 1.0}))
    out = tmp_path / "none.dxf"
    assert main(["-p", str(empty), "-o", str(out)]) == 1
    assert not out.exists()
    assert "No DXF was written" in capsys.readouterr().err


def test_a_parameter_file_must_be_an_object(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2, 3]")
    with pytest.raises(ValueError):
        main(["-p", str(bad), "-o", str(tmp_path / "x.dxf")])


def test_no_input_is_an_error():
    with pytest.raises(SystemExit):
        main([])


@pytest.mark.skipif(not os.path.exists(PAPER), reason="paper PDF not available")
def test_builds_a_dxf_straight_from_a_pdf(tmp_path):
    out = tmp_path / "paper.dxf"
    assert main([PAPER, "-o", str(out)]) == 0
    doc = ezdxf.readfile(str(out))
    layers = {e.dxf.layer for e in doc.modelspace()}
    assert {"SUBSTRATE", "RADIATOR", "FEED", "GROUND"} <= layers
    props = dict(doc.header.custom_vars.properties)
    assert props["TEMPLATE"] == "hexagonal_ring_cpw_monopole"


@pytest.mark.skipif(not os.path.exists(PAPER), reason="paper PDF not available")
def test_preview_png_is_written(tmp_path):
    pytest.importorskip("matplotlib")
    out = tmp_path / "p.dxf"
    png = tmp_path / "p.png"
    assert main([PAPER, "-o", str(out), "--preview", str(png)]) == 0
    assert png.exists() and png.stat().st_size > 0
