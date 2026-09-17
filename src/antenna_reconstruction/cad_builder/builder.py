from antenna_reconstruction.coordinate_engine.models import ResolvedGeometry, SolveStatus
from .models import Point, LineSegment, Rectangle, CADModel, BuildStatus, BuildResult

class GeometryBuilder:
    def build(self, resolved_geom: ResolvedGeometry) -> BuildResult:
        diagnostics = []
        
        # Validation: Must be SOLVED
        if resolved_geom.status != SolveStatus.SOLVED:
            diagnostics.append(f"Cannot build geometry. Expected SOLVED, got {resolved_geom.status}")
            return BuildResult(
                status=BuildStatus.INVALID_RESOLVED_GEOMETRY,
                diagnostics=diagnostics
            )
            
        cad_model = CADModel()
        
        for ent in resolved_geom.entities:
            if ent.type == "rectangle" and ent.geometry:
                geom = ent.geometry
                
                # Create Points
                bl = Point(id=f"{ent.id}_BL", x=geom.bottom_left[0], y=geom.bottom_left[1])
                br = Point(id=f"{ent.id}_BR", x=geom.bottom_right[0], y=geom.bottom_right[1])
                tr = Point(id=f"{ent.id}_TR", x=geom.top_right[0], y=geom.top_right[1])
                tl = Point(id=f"{ent.id}_TL", x=geom.top_left[0], y=geom.top_left[1])
                
                # Create LineSegments
                bottom = LineSegment(id=f"{ent.id}_bottom", start=bl, end=br)
                right = LineSegment(id=f"{ent.id}_right", start=br, end=tr)
                top = LineSegment(id=f"{ent.id}_top", start=tr, end=tl)
                left = LineSegment(id=f"{ent.id}_left", start=tl, end=bl)
                
                # In the future we would use a mapping for layers based on entity id/metadata
                # For now, put all geometries in layer "0"
                rect = Rectangle(
                    id=ent.id,
                    layer="0",
                    vertices=[bl, br, tr, tl],
                    edges=[bottom, right, top, left]
                )
                
                cad_model.rectangles.append(rect)
                
        return BuildResult(
            status=BuildStatus.BUILT,
            model=cad_model,
            diagnostics=diagnostics
        )
