"""Render the reconstruction beside the paper's own figure.

Comparing against the published figure is what caught three binding errors that
the arithmetic alone could not: a symbol that was metal rather than a gap, an
arc mistaken for a closed ring, and a ground plane wrongly called undetermined.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antenna_reconstruction.templates import get_template

PAPER = "data/raw/papers/hexagonal_ring_antenna.pdf"
FIGURE_PAGE = 1  # zero-based; Fig. 2 sits on page 2
HEX_TABLE = {
    "L": 20.0, "W": 20.0, "S1": 6.5, "S2": 5.3, "S3": 4.2, "S4": 4.76,
    "H1": 1.0, "H2": 0.5, "F1": 0.2, "FW": 1.2, "G1": 0.3, "GL": 6.5,
    "FL": 7.5, "W1": 9.1,
}


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path

    result = get_template("hexagonal_ring_cpw_monopole").build(HEX_TABLE)

    have_paper = os.path.exists(PAPER)
    ncols = 2 if have_paper else 1
    fig, axes = plt.subplots(1, ncols, figsize=(6.5 * ncols, 6.6))
    axes = axes if ncols > 1 else [axes]

    if have_paper:
        import pypdfium2 as pdfium
        page = pdfium.PdfDocument(PAPER)[FIGURE_PAGE]
        image = page.render(scale=2.5).to_pil()
        axes[0].imshow(image.crop((215, 380, 640, 800)))
        axes[0].axis("off")
        axes[0].set_title("Paper, Fig. 2", fontsize=12)

    ax = axes[-1]
    W, L = HEX_TABLE["W"], HEX_TABLE["L"]
    ax.add_patch(Rectangle((0, 0), W, L, facecolor="#9a9a9a", edgecolor="none"))
    for shape in result.shapes:
        if shape.layer.value == "SUBSTRATE":
            continue
        verts, codes = [], []
        for ring in shape.rings:
            verts.extend(list(ring) + [ring[0]])
            codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ring) - 1)
                         + [Path.CLOSEPOLY])
        ax.add_patch(PathPatch(Path(verts, codes), facecolor="#000000",
                               edgecolor="none"))
    ax.set_xlim(-0.6, W + 0.6)
    ax.set_ylim(-0.6, L + 0.6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Reconstructed from Table 1", fontsize=12)

    fig.suptitle("Hexagonal ring CPW monopole", fontsize=13)
    fig.tight_layout()
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "hex_comparison.png")
    fig.savefig(path, dpi=130)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
