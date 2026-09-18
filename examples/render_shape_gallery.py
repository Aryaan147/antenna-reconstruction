"""Render every registered template so the shape vocabulary can be eyeballed."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antenna_reconstruction.templates import get_template

STYLE = {
    "SUBSTRATE": {"facecolor": "#d0d0d0", "edgecolor": "#909090", "zorder": 1},
    "RADIATOR": {"facecolor": "#111111", "edgecolor": "#111111", "zorder": 2},
    "FEED": {"facecolor": "#111111", "edgecolor": "#111111", "zorder": 2},
    "GROUND": {"facecolor": "#111111", "edgecolor": "#111111", "zorder": 2},
}

CASES = {
    "hexagonal_ring_cpw_monopole": {
        "L": 20.0, "W": 20.0, "S1": 6.5, "S2": 5.3, "S3": 4.2, "S4": 4.76,
        "H1": 1.0, "H2": 0.5, "F1": 0.2, "FW": 1.2, "G1": 0.3, "GL": 6.5,
        "FL": 7.5, "W1": 9.1,
    },
    "rectangular_patch": {"W": 39.4, "L": 28.9, "SW": 76.8, "SL": 57.8},
    "circular_patch": {"R": 12.5, "D": 25.0, "SW": 50.0, "SL": 50.0},
    "annular_ring": {"RO": 15.0, "RI": 10.0, "WR": 5.0, "SW": 40.0, "SL": 40.0},
    "triangular_patch": {"ST": 20.0, "HT": 17.32, "SW": 40.0, "SL": 40.0},
    "rectangular_patch_array": {
        "W": 38.39, "L": 29.89, "NX": 4, "NY": 2, "DX": 45.0, "DY": 40.0,
        "SW": 200.0, "SL": 110.0,
    },
}


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    for ax, (name, values) in zip(axes.ravel(), CASES.items()):
        result = get_template(name).build(values)
        for shape in result.shapes:
            verts, codes = [], []
            for ring in shape.rings:
                verts.extend(list(ring) + [ring[0]])
                codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ring) - 1)
                             + [Path.CLOSEPOLY])
            ax.add_patch(PathPatch(Path(verts, codes),
                                   **STYLE.get(shape.layer.value, {})))

        xs = [p[0] for s in result.shapes for r in s.rings for p in r]
        ys = [p[1] for s in result.shapes for r in s.rings for p in r]
        pad = 0.05 * max(max(xs) - min(xs), max(ys) - min(ys))
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
        ax.set_aspect("equal")

        report = result.verification
        status = "unverified"
        if report is not None and report.confirmed:
            status = f"{len(report.confirmed)} relation(s) CONFIRMED"
        ax.set_title(f"{name}\n{status}", fontsize=10)
        ax.tick_params(labelsize=7)

    fig.suptitle("Template shape vocabulary (all built from symbols alone)",
                 fontsize=13)
    fig.tight_layout()
    path = os.path.join(out_dir, "shape_gallery.png")
    fig.savefig(path, dpi=130)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
