from antenna_reconstruction.coordinate_engine.models import ResolvedGeometry
from .builder import GeometryBuilder
from .exporters.dxf import DXFExporter
from .models import BuildResult

class CADBuilderService:
    def __init__(self):
        self.builder = GeometryBuilder()
        
    def build(self, resolved_geom: ResolvedGeometry) -> BuildResult:
        """
        Takes a ResolvedGeometry from Component 2 and transforms it into an internal CADModel.
        """
        return self.builder.build(resolved_geom)
        
    def export_dxf(self, result: BuildResult, filepath: str) -> bool:
        """
        Exports a successful BuildResult CADModel to a DXF file.
        """
        if not result.model:
            print("Cannot export: No CADModel in BuildResult.")
            return False
            
        exporter = DXFExporter()
        return exporter.export(result.model, filepath)
