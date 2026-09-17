from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from antenna_reconstruction.geometry_extraction.ir.models import CoordinateSystem, Diagnostic

class SolveStatus(str, Enum):
    SOLVED = "SOLVED"
    UNDERDETERMINED = "UNDERDETERMINED"
    INCONSISTENT = "INCONSISTENT"
    NUMERICALLY_UNRESOLVED = "NUMERICALLY_UNRESOLVED"
    INVALID_INPUT = "INVALID_INPUT"
    MULTIPLE_SOLUTIONS = "MULTIPLE_SOLUTIONS"
    VALIDATION_FAILED = "VALIDATION_FAILED"

class DerivationRecord(BaseModel):
    target: str
    value: float
    unit: str
    operation: str
    inputs: List[str]
    equation: str

class ResolvedEntityGeometry(BaseModel):
    bottom_left: List[float]
    bottom_right: List[float]
    top_right: List[float]
    top_left: List[float]

class ResolvedEntity(BaseModel):
    id: str
    type: str
    geometry: Optional[ResolvedEntityGeometry] = None

class ResolvedParameter(BaseModel):
    id: str
    value: float
    unit: str

class ResolvedGeometry(BaseModel):
    status: SolveStatus
    coordinate_system: CoordinateSystem
    entities: List[ResolvedEntity] = Field(default_factory=list)
    parameters: List[ResolvedParameter] = Field(default_factory=list)
    constraints: List[Any] = Field(default_factory=list)
    derivations: List[DerivationRecord] = Field(default_factory=list)
    diagnostics: List[Diagnostic] = Field(default_factory=list)
