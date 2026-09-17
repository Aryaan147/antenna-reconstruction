import os
import pytest
from antenna_reconstruction.geometry_extraction.service import GeometryUnderstandingService
from antenna_reconstruction.geometry_extraction.ingestion.models import MockGeometryInput
from antenna_reconstruction.coordinate_engine.service import CoordinateEngineService
from antenna_reconstruction.cad_builder.service import CADBuilderService
from antenna_reconstruction.cad_builder.models import BuildStatus

@pytest.fixture
def extraction_service():
    return GeometryUnderstandingService(mode="mock")

@pytest.fixture
def coordinate_service():
    return CoordinateEngineService()

@pytest.fixture
def cad_service():
    return CADBuilderService()

def test_builder_rejects_underdetermined(extraction_service, coordinate_service, cad_service):
    # This text lacks patch placement, so Component 2 returns UNDERDETERMINED
    text = "The substrate is a rectangle with width 76.8 mm and height 57.8 mm. The rectangular patch has a width of 39.4 mm and a height of 28.9 mm."
    
    ir = extraction_service.extract(MockGeometryInput(source_id="test", text=text))
    resolved = coordinate_service.resolve(ir)
    
    build_result = cad_service.build(resolved)
    
    # Component 3 MUST reject anything not SOLVED
    assert build_result.status == BuildStatus.INVALID_RESOLVED_GEOMETRY
    assert build_result.model is None

def test_builder_constructs_valid_dxf(extraction_service, coordinate_service, cad_service, tmp_path):
    # This text is fully solvable
    text = "The substrate is a rectangle with width 76.8 mm and height 57.8 mm. The rectangular patch has a width of 39.4 mm and a height of 28.9 mm. The patch is centered on the substrate."
    
    ir = extraction_service.extract(MockGeometryInput(source_id="test", text=text))
    resolved = coordinate_service.resolve(ir)
    
    build_result = cad_service.build(resolved)
    
    assert build_result.status == BuildStatus.BUILT
    assert build_result.model is not None
    assert len(build_result.model.rectangles) == 2
    
    # Check that export works
    output_dxf = tmp_path / "test_output.dxf"
    success = cad_service.export_dxf(build_result, str(output_dxf))
    
    assert success is True
    assert os.path.exists(output_dxf)
    assert os.path.getsize(output_dxf) > 0
