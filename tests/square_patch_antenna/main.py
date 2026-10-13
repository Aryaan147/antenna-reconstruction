import os
import sys
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath

# Ensure the local src is on the python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from antenna_reconstruction.template_pipeline import TemplatePipeline
from antenna_reconstruction.visual_completion import pipeline as visual_completion
from antenna_reconstruction.templates import get_template

def main():
    print("=" * 50)
    print("Running Special Square Patch Antenna Pipeline Test")
    print("=" * 50)

    # Hardcoded paths relative to this script
    base_dir = os.path.dirname(__file__)
    figure_path = os.path.abspath(os.path.join(base_dir, "..", "..", "data", "raw", "papers", "square_patch_antenna.png"))
    output_path = os.path.join(base_dir, "output_antenna.dxf")
    
    # Mock parameters extracted perfectly for variant "(b) Square with inset feed"
    # This represents exactly what the PDF extraction would yield if it only saw this variant.
    extracted_params = {
        "L1": 45.0,
        "L2": 30.0,
        "L3": 17.0,
        "L4": 14.0,
        "L5": 7.0,
        "W1": 40.0,
        "W2": 30.0,
        "W3": 3.0,
        "W4": 1.2,
        "G1": 0.5
    }

    pipeline = TemplatePipeline()

    print("\n--- Step 2: Visual Completion ---")
    completion = visual_completion.complete(figure_path, extracted_params)
    final_params = completion.enriched_parameters
    print(f"Final merged parameters:\n{json.dumps(final_params, indent=2)}")

    print("\n--- Step 3: DXF Generation ---")
    result = pipeline.run_from_parameters(
        final_params, 
        output_path, 
        source_id="square_patch_antenna_variant_b", 
        figure_path=None
    )
    
    print("\nDiagnostics:")
    print(result.render())

    if result.success:
        print(f"\nSUCCESS: DXF successfully generated at {result.output_path}")
        
        # Step 4: Render PNG Preview
        print("\n--- Step 4: PNG Preview ---")
        preview_out = os.path.join(base_dir, "output_preview.png")
        try:
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
            if pts:
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
        except Exception as e:
            print(f"Preview error: {e}")
            
    else:
        print("\nFAILED: Pipeline could not generate DXF.")

if __name__ == "__main__":
    main()
