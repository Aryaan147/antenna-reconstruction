from typing import Dict, List, Optional

from .base import Layer, Shape, Template, TemplateResult
from .hexagonal_ring import HexagonalRingTemplate
from .rectangular_patch import RectangularPatchTemplate

TEMPLATES: Dict[str, Template] = {
    t.name: t for t in (HexagonalRingTemplate(), RectangularPatchTemplate())
}


def get_template(name: str) -> Template:
    if name not in TEMPLATES:
        raise KeyError(
            f"unknown template {name!r}; available: {sorted(TEMPLATES)}"
        )
    return TEMPLATES[name]


def rank_templates(values: Dict[str, float]) -> List[tuple]:
    """Templates ordered by how well a symbol table fits them.

    Deterministic shortlisting only. It reports how much of each template's
    required symbol set is present; it does NOT decide meaning, and a template
    whose symbols merely happen to be present is still subject to the
    verification step before anything is built.
    """
    scored = []
    for name, tpl in TEMPLATES.items():
        missing = tpl.missing_required(values)
        present = len(tpl.required) - len(missing)
        coverage = present / len(tpl.required) if tpl.required else 0.0
        scored.append((name, coverage, missing))
    # Fully-satisfied templates first; among those, the one demanding the
    # most symbols, so a specific family beats a generic one.
    return sorted(
        scored,
        key=lambda r: (r[1], len(TEMPLATES[r[0]].required)),
        reverse=True,
    )


__all__ = [
    "Layer", "Shape", "Template", "TemplateResult", "HexagonalRingTemplate",
    "RectangularPatchTemplate", "TEMPLATES", "get_template", "rank_templates",
]
