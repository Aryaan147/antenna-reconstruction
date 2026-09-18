from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

class BuildStatus(str, Enum):
    BUILT = "BUILT"
    INVALID_RESOLVED_GEOMETRY = "INVALID_RESOLVED_GEOMETRY"
    TOPOLOGY_ERROR = "TOPOLOGY_ERROR"
    EXPORT_ERROR = "EXPORT_ERROR"

class Point(BaseModel):
    id: str
    x: float
    y: float
    unit: str = "mm"

class LineSegment(BaseModel):
    id: str
    start: Point
    end: Point

class Rectangle(BaseModel):
    id: str
    layer: str = "0"
    vertices: List[Point]
    edges: List[LineSegment]

class PolygonShape(BaseModel):
    """A shape as one or more closed rings, with CAD/EM layer metadata.

    `rings` holds the exterior boundary first, then any interior boundaries
    (holes). Kept as rings rather than a single vertex list so a conductor with
    a void - a ring, a slot, a split - survives export intact.
    """
    id: str
    layer: str = "0"
    rings: List[List[Tuple[float, float]]] = Field(default_factory=list)
    z: float = 0.0
    thickness: float = 0.0
    derivation: str = ""


class CADModel(BaseModel):
    unit: str = "mm"
    rectangles: List[Rectangle] = Field(default_factory=list)
    polygons: List[PolygonShape] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.rectangles and not self.polygons

class BuildResult(BaseModel):
    status: BuildStatus
    model: Optional[CADModel] = None
    diagnostics: List[str] = Field(default_factory=list)
