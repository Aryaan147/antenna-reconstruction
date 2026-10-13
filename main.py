import os
import sys
from dotenv import load_dotenv

# Ensure the local src is on the python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from antenna_reconstruction.template_pipeline import TemplatePipeline

def main():
    # Load environment variables (e.g. GROQ_API_KEY)
    load_dotenv()
    
    # Input files (can be passed as CLI arguments, defaults to hexagonal_ring_antenna.pdf)
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/papers/hexagonal_ring_antenna.pdf"
    figure_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.replace(".pdf", ".png")
    
    # Ensure results directory exists and use a fixed output name
    os.makedirs("results", exist_ok=True)
    output_path = "results/output_antenna.dxf"

    if not os.path.exists(pdf_path):
        print(f"ERROR: The PDF path does not exist: {pdf_path}")
        return
        
    if not os.path.exists(figure_path):
        print(f"ERROR: The Figure path does not exist: {figure_path}")
        print("Visual completion step cannot be skipped. Please provide a valid image.")
        return

    print("=" * 50)
    print("Running Antenna Reconstruction Pipeline")
    print(f"PDF Input   : {pdf_path}")
    print(f"Figure Input: {figure_path}")
    print(f"DXF Output  : {output_path}")
    print("=" * 50)

    # Initialize the pipeline
    pipeline = TemplatePipeline()
    
    import json
    from antenna_reconstruction.geometry_extraction.ingestion.pdf import extract_pdf
    from antenna_reconstruction.visual_completion import pipeline as visual_completion

    # Step 1: Extract Text & Parameters from PDF
    print("\n--- Step 1: PDF Extraction ---")
    doc = extract_pdf(pdf_path)
    extracted_params = doc.merged_parameters()
    step1_out = "results/step1_extracted_parameters.json"
    with open(step1_out, "w") as f:
        json.dump(extracted_params, f, indent=2)
    print(f"Extracted parameters saved to {step1_out}")

    # Step 2: Visual Completion
    print("\n--- Step 2: Visual Completion ---")
    completion = visual_completion.complete(figure_path, extracted_params)
    step2_out = "results/step2_visual_completion.json"
    with open(step2_out, "w") as f:
        json.dump(completion.model_dump(), f, indent=2)
    final_params = completion.enriched_parameters
    print(f"Visual completion data saved to {step2_out}")

    # Save final merged parameters before DXF generation
    step3_out = "results/step3_final_parameters.json"
    with open(step3_out, "w") as f:
        json.dump(final_params, f, indent=2)
    print(f"Final merged parameters saved to {step3_out}")

    # Step 3: Reconstruction and DXF Generation
    print("\n--- Step 3: DXF Generation ---")
    # figure_path=None because we already ran it manually above
    result = pipeline.run_from_parameters(
        final_params, 
        output_path, 
        source_id=doc.source_id, 
        figure_path=None
    )
    
    # Add doc diagnostics that are normally added by run_from_pdf
    result.diagnostics.extend(doc.diagnostics())
    result.derivations.extend(doc.derivations())
    result.assumptions.extend(doc.physics_assumptions())

    # Save diagnostics
    step4_out = "results/step4_diagnostics.txt"
    with open(step4_out, "w") as f:
        f.write(result.render())
    print(f"Diagnostics saved to {step4_out}")

    print("\n" + "=" * 50)
    if result.success:
        print(f"SUCCESS: DXF successfully generated at {result.output_path}")
        
        # Step 4: Render PNG Preview
        print("\n--- Step 4: PNG Preview ---")
        preview_out = "results/output_preview.png"
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.patches import PathPatch
            from matplotlib.path import Path as MplPath
            
            from antenna_reconstruction.templates import get_template
            built = get_template(result.template).build(final_params)
            colour = {"SUBSTRATE": "#c9c9c9", "RADIATOR": "#111111",
                      "FEED": "#111111", "GROUND": "#555555"}
            order = {"SUBSTRATE": 1, "GROUND": 2, "FEED": 3, "RADIATOR": 3}
        
            fig, ax = plt.subplots(figsize=(6, 6))
            for shape in built.shapes:
                for exterior, holes in shape.parts():
                    verts = list(exterior) + [exterior[0]]
                    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(exterior) - 1) \
                        + [MplPath.CLOSEPOLY]
                    for hole in holes:
                        verts += list(hole) + [hole[0]]
                        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(hole) - 1) \
                            + [MplPath.CLOSEPOLY]
                    ax.add_patch(PathPatch(
                        MplPath(verts, codes),
                        facecolor=colour.get(shape.layer.value, "#111111"),
                        edgecolor="none", zorder=order.get(shape.layer.value, 3),
                    ))
            pts = [p for s in built.shapes for r in s.rings for p in r]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            pad = 0.04 * max(max(xs) - min(xs), max(ys) - min(ys))
            ax.set_xlim(min(xs) - pad, max(xs) + pad)
            ax.set_ylim(min(ys) - pad, max(ys) + pad)
            ax.set_aspect("equal")
            ax.set_xlabel("x (mm)")
            ax.set_ylabel("y (mm)")
            ax.set_title(result.template)
            fig.tight_layout()
            fig.savefig(preview_out, dpi=150)
            plt.close(fig)
            print(f"PNG preview successfully generated at {preview_out}")
            
            # Step 5: Side-by-Side Comparison Image
            import matplotlib.image as mpimg
            print("\n--- Step 5: Comparison Preview ---")
            comparison_out = "results/output_comparison_v2.png"
            fig_comp, (ax_orig, ax_recon) = plt.subplots(1, 2, figsize=(12, 6))
            
            # Left: Original Image
            try:
                img = mpimg.imread(figure_path)
                ax_orig.imshow(img)
                ax_orig.set_title("Original Figure")
                ax_orig.axis('off')
            except Exception as e:
                ax_orig.text(0.5, 0.5, f"Could not load image\n{e}", ha='center', va='center')
                ax_orig.set_title("Original Figure (Load Failed)")
                ax_orig.axis('off')
                
            # Right: Reconstructed Geometry
            for shape in built.shapes:
                for exterior, holes in shape.parts():
                    verts = list(exterior) + [exterior[0]]
                    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(exterior) - 1) \
                        + [MplPath.CLOSEPOLY]
                    for hole in holes:
                        verts += list(hole) + [hole[0]]
                        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(hole) - 1) \
                            + [MplPath.CLOSEPOLY]
                    ax_recon.add_patch(PathPatch(
                        MplPath(verts, codes),
                        facecolor=colour.get(shape.layer.value, "#111111"),
                        edgecolor="none", zorder=order.get(shape.layer.value, 3),
                    ))
            ax_recon.set_xlim(min(xs) - pad, max(xs) + pad)
            ax_recon.set_ylim(min(ys) - pad, max(ys) + pad)
            ax_recon.set_aspect("equal")
            ax_recon.set_xlabel("x (mm)")
            ax_recon.set_ylabel("y (mm)")
            ax_recon.set_title("Reconstructed DXF")
            
            fig_comp.tight_layout()
            fig_comp.savefig(comparison_out, dpi=150)
            plt.close(fig_comp)
            print(f"Comparison preview successfully generated at {comparison_out}")
            
        except ImportError:
            print("Preview skipped: matplotlib is not installed. (pip install matplotlib)")
            
    else:
        print("FAILED: Pipeline could not generate DXF.")

if __name__ == "__main__":
    main()
