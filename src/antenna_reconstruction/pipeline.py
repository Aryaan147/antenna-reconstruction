from typing import List, Optional
from pydantic import BaseModel
from .geometry_extraction.service import GeometryUnderstandingService
from .geometry_extraction.ingestion.models import MockGeometryInput
from .coordinate_engine.service import CoordinateEngineService
from .coordinate_engine.models import SolveStatus
from .cad_builder.service import CADBuilderService
from .cad_builder.models import BuildStatus

class PipelineResult(BaseModel):
    success: bool
    failed_component: Optional[str] = None
    diagnostics: List[str] = []
    output_path: Optional[str] = None

class AntennaReconstructionPipeline:
    """
    Unified Orchestrator that hides the complexity of the three components:
    Component 1: Geometry Extraction
    Component 2: Coordinate Engine
    Component 3: Geometry / CAD Builder
    """
    def __init__(self, mode: str = "mock"):
        self.extraction_service = GeometryUnderstandingService(mode=mode)
        self.coordinate_service = CoordinateEngineService()
        self.cad_service = CADBuilderService()
        
    def run_from_text(self, text: str, output_path: str, source_id: str = "pipeline") -> PipelineResult:
        """
        Executes the entire reconstruction pipeline starting from raw text.
        """
        # Component 1: Extraction
        input_data = MockGeometryInput(source_id=source_id, text=text)
        ir = self.extraction_service.extract(input_data)
        
        # We assume extraction is always "successful" in creating IR, even if empty.
        # But we could check for diagnostics here if needed.
        
        # Component 2: Coordinate Resolution
        resolved = self.coordinate_service.resolve(ir)
        
        if resolved.status != SolveStatus.SOLVED:
            return PipelineResult(
                success=False,
                failed_component="Component 2 (Coordinate Engine)",
                diagnostics=[f"Geometry could not be resolved. Status: {resolved.status.value}"] +
                            [f"[{d.severity}] {d.type}: {d.message}" for d in resolved.diagnostics]
            )
            
        # Component 3: CAD Building
        build_result = self.cad_service.build(resolved)
        
        if build_result.status != BuildStatus.BUILT:
            return PipelineResult(
                success=False,
                failed_component="Component 3 (CAD Builder)",
                diagnostics=[f"Failed to construct CAD model. Status: {build_result.status.value}"] + 
                            build_result.diagnostics
            )
            
        # Component 3: Exporting
        success = self.cad_service.export_dxf(build_result, output_path)
        
        if not success:
            return PipelineResult(
                success=False,
                failed_component="Component 3 (DXF Exporter)",
                diagnostics=["Failed to write DXF file to disk."]
            )
            
        return PipelineResult(
            success=True,
            output_path=output_path
        )
