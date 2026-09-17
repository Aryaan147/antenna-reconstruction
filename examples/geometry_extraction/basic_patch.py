from antenna_reconstruction.geometry_extraction.service import GeometryUnderstandingService
from antenna_reconstruction.geometry_extraction.ingestion.models import MockGeometryInput

def main():
    service = GeometryUnderstandingService(mode="mock")
    
    mock_input = MockGeometryInput(
        source_id="mock_patch_001",
        text=(
            "The substrate is a rectangle with width 76.8 mm and height 57.8 mm. "
            "The rectangular patch has a width of 39.4 mm and a height of 28.9 mm. "
            "The rectangular patch is centered on the substrate."
        ),
        metadata={"source_type": "mock_text"}
    )
    
    try:
        ir = service.extract(mock_input)
        print("Geometry IR generated successfully\n")
        
        print("Entities:")
        for ent in ir.entities:
            print(f"  {ent.id:<10} → {ent.primitive}")
            
        print("\nParameters:")
        for param in ir.parameters:
            print(f"  {param.id:<16} = {param.value} {param.unit}")
            
        print("\nConstraints:")
        for c in ir.constraints:
            objs = ", ".join(c.objects)
            print(f"  {c.type}({objs})")
            
        print("\nCoordinates:")
        print("  NONE")
        
        if ir.diagnostics:
            print("\nDiagnostics:")
            for d in ir.diagnostics:
                print(f"  [{d.severity.upper()}] {d.type}: {d.message}")
    except Exception as e:
        print(f"Failed to generate IR: {e}")

if __name__ == "__main__":
    main()
