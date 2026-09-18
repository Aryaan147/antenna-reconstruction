"""Render every paper's own figure beside what the pipeline reconstructs.

This is the check that arithmetic cannot do. Verification relations prove the
numbers are bound to the right symbols; only the figure shows whether the SHAPE
assembled from them is right. Run it for every new template.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antenna_reconstruction.templates import get_template

PAPER_DIR = "data/raw/papers"
OUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# page index (0-based) and the figure's fractional box on that page
FIGURES = {
    "hexagonal_ring_antenna": (1, (0.145, 0.180, 0.430, 0.380)),
    "microstrip_patch_antenna": (1, (0.100, 0.240, 0.400, 0.490)),
    "rectangular_patch_array": (1, (0.220, 0.655, 0.460, 0.850)),
    "square_patch_antenna": (0, (0.520, 0.575, 0.900, 0.820)),
    "synthetic_antenna": (0, (0.130, 0.400, 0.450, 0.620)),
}

# What the pipeline can build for each paper, and how the symbols were obtained.
CASES = {
    "hexagonal_ring_antenna": dict(
        template="hexagonal_ring_cpw_monopole",
        values={"L": 20.0, "W": 20.0, "S1": 6.5, "S2": 5.3, "S3": 4.2,
                "S4": 4.76, "H1": 1.0, "H2": 0.5, "F1": 0.2, "FW": 1.2,
                "G1": 0.3, "GL": 6.5, "FL": 7.5, "W1": 9.1},
        source="automatic, from Table 1",
        note="3 relations CONFIRMED; nothing left undetermined",
    ),
    "microstrip_patch_antenna": dict(
        template="rectangular_patch",
        values={"W": 39.4, "L": 28.9, "SW": 76.8, "SL": 57.8},
        source="automatic, from prose",
        note="UNVERIFIED; inset feed (9.25/23.7 mm) is only in the figure",
    ),
    "rectangular_patch_array": dict(
        template="rectangular_patch",
        values={"W": 38.3934, "L": 29.89},
        source="automatic, from table headers",
        note=("UNVERIFIED; this is the paper's Fig. 1 single element. No "
              "substrate is stated, the inset feed is not modelled, and the "
              "paper's actual 4x2 array is not built (spacing is given only "
              "as lambda/2)"),
    ),
    "square_patch_antenna": dict(
        template="trimmed_square_patch",
        values={"W1": 45.0, "L1": 45.0, "W2": 30.0, "L2": 30.0,
                "W3": 25.0, "L3": 25.0},
        source="MANUAL (variant (a) only)",
        note="2 relations CONFIRMED; auto-extraction refuses: 3 design variants",
    ),
    "synthetic_antenna": dict(
        template=None, values={}, source="nothing extracted",
        note="paper cites a Table I that does not exist; no dimension is given",
    ),
}

STYLE = {
    "SUBSTRATE": "#9a9a9a", "RADIATOR": "#111111",
    "FEED": "#111111", "GROUND": "#111111",
}


def _draw(ax, result):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    for shape in result.shapes:
        verts, codes = [], []
        for ring in shape.rings:
            verts.extend(list(ring) + [ring[0]])
            codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ring) - 1)
                         + [Path.CLOSEPOLY])
        ax.add_patch(PathPatch(
            Path(verts, codes),
            facecolor=STYLE.get(shape.layer.value, "#111111"),
            edgecolor="#d94a4a", linewidth=1.0,
        ))
    xs = [p[0] for s in result.shapes for r in s.rings for p in r]
    ys = [p[1] for s in result.shapes for r in s.rings for p in r]
    pad = 0.04 * max(max(xs) - min(xs), max(ys) - min(ys))
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)


def _figure_image(name):
    import pypdfium2 as pdfium
    path = os.path.join(PAPER_DIR, f"{name}.pdf")
    if not os.path.exists(path) or name not in FIGURES:
        return None
    page_index, (a, b, c, d) = FIGURES[name]
    image = pdfium.PdfDocument(path)[page_index].render(scale=3).to_pil()
    w, h = image.size
    return image.crop((int(w * a), int(h * b), int(w * c), int(h * d)))


def render_one(name, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    case = CASES[name]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.4))

    image = _figure_image(name)
    if image is not None:
        ax1.imshow(image)
    ax1.axis("off")
    ax1.set_title("Paper's own figure", fontsize=11)

    if case["template"] is None:
        ax2.text(0.5, 0.5, "nothing built\n\n" + case["note"],
                 ha="center", va="center", fontsize=11, color="#8a1c1c",
                 transform=ax2.transAxes)
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
    else:
        result = get_template(case["template"]).build(case["values"])
        _draw(ax2, result)
        ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_title(f"Reconstructed  ({case['source']})", fontsize=11)
    ax2.set_facecolor("#ffffff")

    fig.suptitle(f"{name}\n{case['note']}", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in CASES:
        path = render_one(name, os.path.join(OUT_DIR, f"compare_{name}.png"))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
