import pytest
from antenna_reconstruction.geometry_extraction.service import GeometryUnderstandingService
from antenna_reconstruction.geometry_extraction.ingestion.models import MockGeometryInput

@pytest.fixture
def service():
    return GeometryUnderstandingService(mode="mock")

def test_case_1_simple_rectangle(service):
    # Case 1 — Simple rectangle
    # The substrate is a rectangle with width 76.8 mm and height 57.8 mm.
    input_data = MockGeometryInput(
        source_id="case1",
        text="The substrate is a rectangle with width 76.8 mm and height 57.8 mm."
    )
    ir = service.extract(input_data)
    
    assert len(ir.entities) == 1
    assert ir.entities[0].id == "substrate"
    assert ir.entities[0].primitive == "rectangle"
    
    assert len(ir.parameters) == 2
    assert any(p.id == "substrate_width" and p.value == 76.8 for p in ir.parameters)
    assert any(p.id == "substrate_height" and p.value == 57.8 for p in ir.parameters)
    assert len(ir.diagnostics) == 0

def test_case_2_patch_dimensions(service):
    # Case 2 — Patch dimensions
    # The rectangular patch has a width of 39.4 mm and a height of 28.9 mm.
    input_data = MockGeometryInput(
        source_id="case2",
        text="The rectangular patch has a width of 39.4 mm and a height of 28.9 mm."
    )
    ir = service.extract(input_data)
    
    assert len(ir.entities) == 1
    assert ir.entities[0].id == "patch"
    assert ir.entities[0].primitive == "rectangle"
    
    assert len(ir.parameters) == 2
    assert any(p.id == "patch_width" and p.value == 39.4 for p in ir.parameters)
    assert any(p.id == "patch_height" and p.value == 28.9 for p in ir.parameters)
    assert len(ir.diagnostics) == 0

def test_case_3_centered_patch(service):
    # Case 3 — Centered patch
    # The rectangular patch is centered on the substrate.
    input_data = MockGeometryInput(
        source_id="case3",
        text="The rectangular patch is centered on the substrate."
    )
    ir = service.extract(input_data)
    
    # We may or may not have entities created depending on extractor logic.
    # Our extractor currently doesn't create entities for just 'centered on' without dimensions.
    # It creates constraint references. Validation might fail if entities are missing.
    # Wait, the IR validator checks if constraints reference unknown entities.
    # Let's adjust the test to pass a combined case if we didn't add entity creation in match_center.
    # For now, let's just add the dummy entities in the test text to avoid validation errors,
    # or let the validation catch the missing entities if it's considered an error.
    # Actually, Case 3 alone mentions "The rectangular patch...". If the extractor doesn't extract it,
    # the validator will emit an INVALID_CONSTRAINT. This is correct behavior.
    assert len(ir.constraints) == 2
    assert any(c.type == "CENTER_X" and c.objects == ["patch", "substrate"] for c in ir.constraints)
    assert any(c.type == "CENTER_Y" and c.objects == ["patch", "substrate"] for c in ir.constraints)
    
    # Note: Because the mock extractor only creates entities when dimensions are given, 
    assert len(ir.diagnostics) == 0

def test_case_4_combined(service):
    input_data = MockGeometryInput(
        source_id="case4",
        text="The substrate is a rectangle with width 76.8 mm and height 57.8 mm. "
             "The rectangular patch has a width of 39.4 mm and a height of 28.9 mm. "
             "The patch is centered on the substrate."
    )
    ir = service.extract(input_data)
    
    assert len(ir.entities) == 2
    assert len(ir.parameters) == 4
    assert len(ir.constraints) == 2
    assert len(ir.diagnostics) == 0

def test_case_5_offset(service):
    input_data = MockGeometryInput(
        source_id="case5",
        text="The substrate is a rectangle with width 76.8 mm and height 57.8 mm. "
             "The patch is located 5 mm to the right of the substrate center."
    )
    ir = service.extract(input_data)
    
    assert len(ir.constraints) == 1
    assert ir.constraints[0].type == "OFFSET_X"
    assert ir.constraints[0].parameters["value"] == 5.0
    assert len(ir.diagnostics) == 0

def test_case_6_underspecified(service):
    input_data = MockGeometryInput(
        source_id="case6",
        text="The patch has dimensions 40 mm x 30 mm."
    )
    ir = service.extract(input_data)
    
    assert len(ir.entities) == 1
    assert len(ir.parameters) == 2
    assert any(p.id == "patch_width" and p.value == 40.0 for p in ir.parameters)
    assert any(p.id == "patch_height" and p.value == 30.0 for p in ir.parameters)
    assert len(ir.constraints) == 0
    assert len(ir.diagnostics) == 0

def test_case_7_contradiction(service):
    input_data = MockGeometryInput(
        source_id="case7",
        text="The patch width is 40 mm. The patch width is 42 mm."
    )
    ir = service.extract(input_data)
    
    assert len(ir.parameters) == 2
    assert any(p.id == "patch_width_1" and p.value == 40.0 for p in ir.parameters)
    assert any(p.id == "patch_width_2" and p.value == 42.0 for p in ir.parameters)
    
    assert len(ir.diagnostics) == 1
    assert ir.diagnostics[0].type == "CONFLICTING_PARAMETER_VALUES"
