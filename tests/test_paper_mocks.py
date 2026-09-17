import pytest
from antenna_reconstruction.geometry_extraction.service import GeometryUnderstandingService
from antenna_reconstruction.geometry_extraction.ingestion.models import MockGeometryInput

@pytest.fixture
def service():
    return GeometryUnderstandingService(mode="mock")

def test_paper_rectangular_patch_array(service):
    # Derived from rectangular_patch_array.pdf
    # The paper mentions: "Substrate height 1.6mm"
    # "single patch having L=29.89mm and W=38.39mm"
    # We map this to our supported Mock Text format for the current extractor.
    input_data = MockGeometryInput(
        source_id="rectangular_patch_array_paper",
        text="The substrate height is 1.6 mm. The rectangular patch has a width of 38.39 mm and a height of 29.89 mm."
    )
    ir = service.extract(input_data)
    
    assert len(ir.entities) == 2
    assert any(e.id == "substrate" for e in ir.entities)
    assert any(e.id == "patch" for e in ir.entities)
    
    assert len(ir.parameters) == 3
    assert any(p.id == "substrate_height" and p.value == 1.6 for p in ir.parameters)
    assert any(p.id == "patch_width" and p.value == 38.39 for p in ir.parameters)
    assert any(p.id == "patch_height" and p.value == 29.89 for p in ir.parameters)
    assert len(ir.diagnostics) == 0

def test_paper_synthetic_antenna(service):
    # Derived from synthetic_antenna.pdf
    # The paper mentions: "rectangular patch on FR-4 substrate... thickness of 1.6mm"
    # Mapped to supported Mock Text format:
    input_data = MockGeometryInput(
        source_id="synthetic_antenna_paper",
        text="The substrate height is 1.6 mm. The rectangular patch is centered on the substrate."
    )
    ir = service.extract(input_data)
    
    assert len(ir.parameters) == 1
    assert any(p.id == "substrate_height" and p.value == 1.6 for p in ir.parameters)
    
    assert len(ir.constraints) == 2
    assert any(c.type == "CENTER_X" and "patch" in c.objects for c in ir.constraints)
    
    assert len(ir.diagnostics) == 0
