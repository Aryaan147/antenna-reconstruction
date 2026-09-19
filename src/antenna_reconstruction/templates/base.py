"""Parametric antenna family templates.

A template encodes ONE recurring antenna topology. It declares:
  * the symbols it needs,
  * the redundancy relations that verify a symbol binding (see binding.verifier),
  * how to build exact geometry once the binding is verified,
  * which sub-structures it cannot determine from the given symbols.

Templates never invent a missing number. A part that cannot be determined is
reported as underdetermined and omitted from the output.
"""
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from ..binding.verifier import Relation, VerificationReport

Point = Tuple[float, float]


class Layer(str, Enum):
    SUBSTRATE = "SUBSTRATE"
    RADIATOR = "RADIATOR"
    GROUND = "GROUND"
    FEED = "FEED"


class Shape(BaseModel):
    """One resolved planar shape, with the layer metadata a CAD/EM consumer needs.

    `ring_roles` marks each ring as "exterior" or "hole". Leaving it empty means
    the first ring is the exterior and the rest are its holes, which is right
    for an annulus but wrong for a shape in several disjoint pieces - a ground
    plane split in two by the feed between them.
    """
    id: str
    layer: Layer
    rings: List[List[Point]]
    ring_roles: List[str] = Field(default_factory=list)

    def parts(self):
        """Group the rings into (exterior, holes) pairs."""
        roles = self.ring_roles or (
            ["exterior"] + ["hole"] * (len(self.rings) - 1)
        )
        grouped, current = [], None
        for ring, role in zip(self.rings, roles):
            if role == "exterior":
                current = (ring, [])
                grouped.append(current)
            elif current is not None:
                current[1].append(ring)
        return grouped
    # Carried so a 3D/EM export can be added later without reworking the model.
    z: float = 0.0
    thickness: float = 0.0
    derivation: str = ""


class TemplateResult(BaseModel):
    template: str
    shapes: List[Shape] = Field(default_factory=list)
    verification: Optional[VerificationReport] = None
    underdetermined: List[str] = Field(default_factory=list)
    diagnostics: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class Template(BaseModel):
    name: str
    required: List[str] = Field(default_factory=list)
    optional: List[str] = Field(default_factory=list)

    def relations(self) -> List[Relation]:
        raise NotImplementedError

    def build(self, values: Dict[str, float]) -> TemplateResult:
        raise NotImplementedError

    def missing_required(self, values: Dict[str, float]) -> List[str]:
        return [s for s in self.required if s not in values]
