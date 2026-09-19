"""Command line entry point: a paper in, a DXF out.

    antenna-reconstruct paper.pdf -o antenna.dxf
"""
import argparse
import json
import os
import sys
from typing import Dict, Optional

from .template_pipeline import ReconstructionResult, TemplatePipeline
from .templates import TEMPLATES


def _load_parameters(path: str) -> Dict[str, float]:
    with open(path) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("a parameter file must be a JSON object of symbol -> value")
    return {str(k): float(v) for k, v in data.items()}


def _write_preview(result: ReconstructionResult, values: Dict[str, float],
                   path: str) -> Optional[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import PathPatch
        from matplotlib.path import Path as MplPath
    except ImportError:
        print("preview needs matplotlib: pip install 'antenna-reconstruction[viz]'")
        return None

    from .templates import get_template
    built = get_template(result.template).build(values)
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
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="antenna-reconstruct",
        description="Reconstruct antenna geometry from a paper and write a DXF.",
    )
    parser.add_argument("paper", nargs="?", help="path to the paper's PDF")
    parser.add_argument("-o", "--output", help="DXF to write "
                        "(default: alongside the input)")
    parser.add_argument("-p", "--parameters",
                        help="JSON file of symbol -> value, instead of a PDF")
    parser.add_argument("-t", "--template", choices=sorted(TEMPLATES),
                        help="force a template instead of matching one")
    parser.add_argument("--preview", metavar="PNG",
                        help="also render a PNG of the reconstruction")
    parser.add_argument("--no-hatch", action="store_true",
                        help="write outlines only, without filled regions")
    parser.add_argument("--list-templates", action="store_true",
                        help="list the antenna families that can be built")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="print only the output path")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_templates:
        for name in sorted(TEMPLATES):
            template = TEMPLATES[name]
            print(f"{name}\n    requires: {', '.join(template.required)}")
        return 0

    if not args.paper and not args.parameters:
        build_parser().error("give a PDF, or -p with a parameter file")

    stem = os.path.splitext(os.path.basename(args.paper or args.parameters))[0]
    output = args.output or os.path.join(
        os.path.dirname(args.paper or args.parameters) or ".", f"{stem}.dxf"
    )

    pipeline = TemplatePipeline()
    if args.no_hatch:
        original = pipeline.exporter.export
        pipeline.exporter.export = (
            lambda model, path, metadata=None, hatch=True:
            original(model, path, metadata=metadata, hatch=False)
        )

    if args.parameters:
        values = _load_parameters(args.parameters)
        result = pipeline.run_from_parameters(
            values, output, source_id=stem, template_name=args.template
        )
    else:
        result = pipeline.run_from_pdf(
            args.paper, output, template_name=args.template
        )
        values = result.parameters

    if not args.quiet:
        print(result.render())

    if not result.success:
        print("\nNo DXF was written.", file=sys.stderr)
        return 1

    if args.quiet:
        print(result.output_path)
    if args.preview:
        written = _write_preview(result, values, args.preview)
        if written and not args.quiet:
            print(f"preview    : {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
