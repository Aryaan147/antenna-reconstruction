"""The regression that motivated this work.

Running the pipeline over a real paper used to return success=True with zero
diagnostics and write a DXF containing no geometry. A green result that means
nothing is worse than a loud failure, so these tests pin the honest behaviour.
"""
import os
import pytest

from antenna_reconstruction.coordinate_engine.models import SolveStatus
from antenna_reconstruction.coordinate_engine.service import CoordinateEngineService
from antenna_reconstruction.geometry_extraction.ingestion.models import MockGeometryInput
from antenna_reconstruction.geometry_extraction.service import GeometryUnderstandingService
from antenna_reconstruction.pipeline import AntennaReconstructionPipeline

UNPARSEABLE = (
    "This paper presents a novel wideband antenna for 5G applications. "
    "Measurements were performed in an anechoic chamber."
)


@pytest.fixture
def services():
    return GeometryUnderstandingService(mode="mock"), CoordinateEngineService()


def test_empty_extraction_is_not_solved(services):
    extraction, coordinate = services
    ir = extraction.extract(MockGeometryInput(source_id="t", text=UNPARSEABLE))
    resolved = coordinate.resolve(ir)

    assert resolved.status is SolveStatus.INVALID_INPUT
    assert any(d.type == "NO_GEOMETRY_EXTRACTED" for d in resolved.diagnostics)


def test_pipeline_fails_loudly_and_writes_no_file(tmp_path):
    out = tmp_path / "should_not_exist.dxf"
    result = AntennaReconstructionPipeline().run_from_text(UNPARSEABLE, str(out))

    assert result.success is False
    assert result.diagnostics
    assert not os.path.exists(out)


def test_entities_without_constraints_are_underdetermined(services):
    extraction, coordinate = services
    # An entity with no dimension at all: nothing pins its coordinates.
    ir = extraction.extract(MockGeometryInput(
        source_id="t", text="The rectangular patch is centered on the substrate."
    ))
    resolved = coordinate.resolve(ir)

    assert resolved.status is not SolveStatus.SOLVED
