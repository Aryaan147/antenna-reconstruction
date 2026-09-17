import os
import sys

# Add src to sys.path so we can run this directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from antenna_reconstruction.pipeline import AntennaReconstructionPipeline

def main():
    print("Initializing Antenna Reconstruction Pipeline...")
    pipeline = AntennaReconstructionPipeline(mode="mock")
    
    text = "The substrate is a rectangle with width 76.8 mm and height 57.8 mm. The rectangular patch has a width of 39.4 mm and a height of 28.9 mm. The patch is centered on the substrate."
    output_dxf = os.path.join(os.path.dirname(__file__), "reconstructed_antenna.dxf")
    
    print("\nRunning full pipeline (Extraction -> Coordinate Solving -> CAD Building)...")
    result = pipeline.run_from_text(text=text, output_path=output_dxf)
    
    if result.success:
        print(f"\n✅ Pipeline succeeded! CAD file saved to: {result.output_path}")
    else:
        print(f"\n❌ Pipeline failed at {result.failed_component}:")
        for diag in result.diagnostics:
            print(f"   - {diag}")

if __name__ == "__main__":
    main()
