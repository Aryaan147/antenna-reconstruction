from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class Entity(BaseModel):
    id: str
    semantic_type: str
    primitive: str
    description: Optional[str] = None
    source_refs: List[str] = Field(default_factory=list)


class Parameter(BaseModel):
    id: str
    value: float
    unit: str
    parameter_type: str
    source_refs: List[str] = Field(default_factory=list)
    evidence_type: str = "explicit"
    confidence: Optional[str] = None


class Constraint(BaseModel):
    id: str
    type: str
    objects: List[str]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    source_refs: List[str] = Field(default_factory=list)
    evidence_type: str = "explicit"
    confidence: Optional[str] = None


class CoordinateSystem(BaseModel):
    dimension: int = 2
    unit: str = "mm"
    origin_definition: Dict[str, Any] = Field(default_factory=dict)


class Diagnostic(BaseModel):
    type: str
    severity: str = "error"
    message: Optional[str] = None
    objects: List[str] = Field(default_factory=list)
    parameters: List[str] = Field(default_factory=list)


class GeometryIR(BaseModel):
    schema_version: str = "1.0"
    coordinate_system: CoordinateSystem = Field(default_factory=CoordinateSystem)
    entities: List[Entity] = Field(default_factory=list)
    parameters: List[Parameter] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    equations: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    diagnostics: List[Diagnostic] = Field(default_factory=list)
