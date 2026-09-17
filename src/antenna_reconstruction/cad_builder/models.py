from enum import Enum
from typing import List, Optional
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

class CADModel(BaseModel):
    unit: str = "mm"
    rectangles: List[Rectangle] = Field(default_factory=list)

class BuildResult(BaseModel):
    status: BuildStatus
    model: Optional[CADModel] = None
    diagnostics: List[str] = Field(default_factory=list)
