"""Per-paper coverage, pinned.

Without a metric there is no way to tell whether a change is progress, so each
paper's expected outcome is asserted here. A paper that starts or stops
reconstructing will fail this file, which is the point.
"""
import os
import pytest
import ezdxf

from antenna_reconstruction.template_pipeline import TemplatePipeline

PAPER_DIR = "data/raw/papers"

# (built?, verified?, template, why)
EXPECTED = {
    "hexagonal_ring_antenna": (
        True, True, "hexagonal_ring_cpw_monopole",
        "full parameter table with three verifiable redundancies",
    ),
    "microstrip_patch_antenna": (
        True, False, "rectangular_patch",
        "dimensions stated in prose; family offers no redundancy to check",
    ),
    "rectangular_patch_array": (
        True, True, "rectangular_patch_array",
        "element from table headers; 4x2 count and lambda/2 spacing derived "
        "from the stated 2.4 GHz centre frequency",
    ),
    "square_patch_antenna": (
        False, False, None,
        "three design variants; symbols contested, so nothing is chosen",
    ),
    "synthetic_antenna": (
        False, False, None,
        "states only substrate thickness; no planar geometry at all",
    ),
}


@pytest.fixture(scope="module")
def pipeline():
    return TemplatePipeline()


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_paper_outcome_is_pinned(name, pipeline, tmp_path):
    path = os.path.join(PAPER_DIR, f"{name}.pdf")
    if not os.path.exists(path):
        pytest.skip(f"{name}.pdf not available")

    built, verified, template, why = EXPECTED[name]
    result = pipeline.run_from_pdf(path, str(tmp_path / f"{name}.dxf"))

    assert result.success is built, f"{name}: expected built={built} ({why})"
    assert result.verified is verified, f"{name}: expected verified={verified}"
    if template is not None:
        assert result.template == template

    if built:
        doc = ezdxf.readfile(str(tmp_path / f"{name}.dxf"))
        assert list(doc.modelspace()), f"{name}: DXF must not be empty"
    else:
        # A failure must explain itself and must not leave a file behind.
        assert result.diagnostics
        assert not os.path.exists(tmp_path / f"{name}.dxf")


def test_failures_never_claim_partial_success(pipeline, tmp_path):
    for name, (built, _, _, _) in EXPECTED.items():
        path = os.path.join(PAPER_DIR, f"{name}.pdf")
        if built or not os.path.exists(path):
            continue
        result = pipeline.run_from_pdf(path, str(tmp_path / f"{name}.dxf"))
        assert result.success is False
        assert result.output_path is None


@pytest.mark.skipif(
    not os.path.exists(f"{PAPER_DIR}/microstrip_patch_antenna.pdf"),
    reason="paper not available",
)
def test_prose_derived_dimensions_match_the_paper(pipeline, tmp_path):
    result = pipeline.run_from_pdf(
        f"{PAPER_DIR}/microstrip_patch_antenna.pdf",
        str(tmp_path / "m.dxf"),
    )
    # "fabricated on 76.8 X 57.8 mm2 FR-4 substrate" / "patch ... 39.4X28.9mm2"
    assert result.parameters["SW"] == 76.8
    assert result.parameters["SL"] == 57.8
    assert result.parameters["W"] == 39.4
    assert result.parameters["L"] == 28.9


@pytest.mark.skipif(
    not os.path.exists(f"{PAPER_DIR}/rectangular_patch_array.pdf"),
    reason="paper not available",
)
def test_array_spacing_is_derived_not_stated(pipeline, tmp_path):
    """The paper never prints a spacing; it prints lambda/2 and 2.4 GHz."""
    result = pipeline.run_from_pdf(
        f"{PAPER_DIR}/rectangular_patch_array.pdf", str(tmp_path / "a.dxf")
    )
    assert result.parameters["NX"] == 4 and result.parameters["NY"] == 2
    assert result.parameters["DX"] == pytest.approx(62.4568, abs=1e-3)
    assert any("lambda0 = c / f" in d for d in result.derivations)
    # A derived value must be labelled as such, not passed off as stated.
    assert any("lambda" in a for a in result.assumptions)
