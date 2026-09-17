from antenna_reconstruction.geometry_extraction.service import GeometryUnderstandingService
from antenna_reconstruction.geometry_extraction.ingestion.models import MockGeometryInput

def print_ir(ir, paper_name):
    print(f"\n{'='*50}")
    print(f"Results for {paper_name}")
    print(f"{'='*50}\n")
    
    print("Entities:")
    for ent in ir.entities:
        print(f"  {ent.id:<10} → {ent.primitive}")
        
    print("\nParameters:")
    for param in ir.parameters:
        print(f"  {param.id:<20} = {param.value} {param.unit}")
        
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
            
def main():
    service = GeometryUnderstandingService(mode="mock")
    
    # Paper 1
    input_data_1 = MockGeometryInput(
        source_id="rectangular_patch_array_paper",
        text="The substrate height is 1.6 mm. The rectangular patch has a width of 38.39 mm and a height of 29.89 mm."
    )
    ir_1 = service.extract(input_data_1)
    print_ir(ir_1, "Rectangular Patch Array")

    # Paper 2
    input_data_2 = MockGeometryInput(
        source_id="synthetic_antenna_paper",
        text="The substrate height is 1.6 mm. The rectangular patch is centered on the substrate."
    )
    ir_2 = service.extract(input_data_2)
    print_ir(ir_2, "Synthetic Antenna")


if __name__ == "__main__":
    main()
