"""Render a reconstruction to PNG so it can be compared against the paper's figure.

Visual comparison against the published figure is the cheapest end-to-end check
that the symbol binding is right, so it is worth doing for every new template.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antenna_reconstruction.templates import get_template

LAYER_STYLE = {
    "SUBSTRATE": {"facecolor": "#cccccc", "edgecolor": "#888888", "zorder": 1},
    "RADIATOR": {"facecolor": "#111111", "edgecolor": "#111111", "zorder": 2},
    "FEED": {"facecolor": "#111111", "edgecolor": "#111111", "zorder": 2},
    "GROUND": {"facecolor": "#111111", "edgecolor": "#111111", "zorder": 2},
}


def render(template_name: str, values: dict, out_path: str) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    result = get_template(template_name).build(values)

    fig, ax = plt.subplots(figsize=(6, 6))
    for shape in result.shapes:
        style = LAYER_STYLE.get(shape.layer.value, {})
        verts, codes = [], []
        for ring in shape.rings:
            verts.extend(list(ring) + [ring[0]])
            codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ring) - 1)
                         + [Path.CLOSEPOLY])
        ax.add_patch(PathPatch(Path(verts, codes), **style))

    substrate = next((s for s in result.shapes if s.layer.value == "SUBSTRATE"), None)
    if substrate is not None:
        xs = [p[0] for p in substrate.rings[0]]
        ys = [p[1] for p in substrate.rings[0]]
        ax.set_xlim(min(xs) - 1, max(xs) + 1)
        ax.set_ylim(min(ys) - 1, max(ys) + 1)

    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(f"{template_name}\nreconstructed from the paper's parameter table")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


HEX_TABLE = {
    "L": 20.0, "W": 20.0, "S1": 6.5, "S2": 5.3, "S3": 4.2, "S4": 4.76,
    "H1": 1.0, "H2": 0.5, "F1": 0.2, "FW": 1.2, "G1": 0.3, "GL": 6.5,
    "FL": 7.5, "W1": 9.1,
}

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    path = render("hexagonal_ring_cpw_monopole", HEX_TABLE,
                  os.path.join(out_dir, "hexagonal_ring_antenna.png"))
    print(f"wrote {path}")
