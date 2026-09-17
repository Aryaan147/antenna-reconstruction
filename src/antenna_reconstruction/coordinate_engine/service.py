from antenna_reconstruction.geometry_extraction.ir.models import GeometryIR
from .models import ResolvedGeometry
from .solver import SympySolver

class CoordinateEngineService:
    def resolve(self, ir: GeometryIR) -> ResolvedGeometry:
        """
        Takes a GeometryIR from Component 1 and resolves it mathematically to produce explicit coordinates.
        """
        solver = SympySolver(ir)
        resolved_geometry = solver.solve()
        
        return resolved_geometry
