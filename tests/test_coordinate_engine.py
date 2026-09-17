import pytest
from antenna_reconstruction.geometry_extraction.service import GeometryUnderstandingService
from antenna_reconstruction.geometry_extraction.ingestion.models import MockGeometryInput
from antenna_reconstruction.coordinate_engine.service import CoordinateEngineService
from antenna_reconstruction.coordinate_engine.models import SolveStatus

@pytest.fixture
def extraction_service():
    return GeometryUnderstandingService(mode="mock")

@pytest.fixture
def coordinate_service():
    return CoordinateEngineService()

def test_engine_solved_centered_patch(extraction_service, coordinate_service):
    text = "The substrate is a rectangle with width 76.8 mm and height 57.8 mm. The rectangular patch has a width of 39.4 mm and a height of 28.9 mm. The patch is centered on the substrate."
    ir = extraction_service.extract(MockGeometryInput(source_id="test", text=text))
    resolved = coordinate_service.resolve(ir)
    
    assert resolved.status == SolveStatus.SOLVED
    assert len(resolved.entities) == 2
    
    # Check substrate
    sub = next(e for e in resolved.entities if e.id == "substrate")
    assert sub.geometry.bottom_left == [0.0, 0.0]
    assert sub.geometry.top_right == [76.8, 57.8]
    
    # Check patch
    patch = next(e for e in resolved.entities if e.id == "patch")
    assert patch.geometry.bottom_left == pytest.approx([18.7, 14.45])
    assert patch.geometry.top_right == pytest.approx([58.1, 43.35])

def test_engine_underdetermined(extraction_service, coordinate_service):
    text = "The substrate is a rectangle with width 76.8 mm and height 57.8 mm. The rectangular patch has a width of 39.4 mm and a height of 28.9 mm."
    ir = extraction_service.extract(MockGeometryInput(source_id="test", text=text))
    resolved = coordinate_service.resolve(ir)
    
    # Patch position is not specified
    assert resolved.status == SolveStatus.UNDERDETERMINED

def test_engine_inconsistent(extraction_service, coordinate_service):
    text = "The patch width is 40.0 mm. The patch width is 42.0 mm."
    ir = extraction_service.extract(MockGeometryInput(source_id="test", text=text))
    resolved = coordinate_service.resolve(ir)
    
    assert resolved.status == SolveStatus.INCONSISTENT
