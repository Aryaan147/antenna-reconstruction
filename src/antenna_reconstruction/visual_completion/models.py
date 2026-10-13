from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class VisualMissingItem(BaseModel):
    """A missing parameter or geometry identified by the VLM from the figure."""
    type: str  # "PARAMETER", "GEOMETRY", "TOPOLOGY"
    feature: str
    description: str
    related_parameters: List[str] = Field(default_factory=list)
    visible_dimensions: List[float] = Field(default_factory=list)
    estimations: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0

class VLMAnalysis(BaseModel):
    """The structured response from the Visual Language Model."""
    status: str  # "COMPLETE", "MISSING", "UNCERTAIN"
    missing_items: List[VisualMissingItem] = Field(default_factory=list)

class GeometryCompletionRequest(BaseModel):
    """The input to the mathematical geometry constructor."""
    parameters: Dict[str, float]
    missing_items: List[VisualMissingItem]

class CompletionDerivation(BaseModel):
    """Provenance for an added parameter or geometry."""
    parameter: str
    value: float
    source: str  # e.g., "FIGURE_EXPLICIT", "MATHEMATICAL_DERIVATION"
    method: str

class GeometryCompletionResult(BaseModel):
    """The output of the mathematical geometry constructor."""
    resolved_parameters: Dict[str, float] = Field(default_factory=dict)
    derived_geometry: Dict[str, Any] = Field(default_factory=dict) # E.g., for complex topological additions
    unresolved: List[str] = Field(default_factory=list)
    derivations: List[CompletionDerivation] = Field(default_factory=list)
    
class Completion(BaseModel):
    """The final enriched structure to pass to the existing pipeline."""
    enriched_parameters: Dict[str, float]
    vlm_status: str
    constructor_status: str
    derivations: List[CompletionDerivation] = Field(default_factory=list)
    unresolved: List[str] = Field(default_factory=list)

# Avoid Any in model definitions to prevent Pydantic errors if possible
from typing import Any
GeometryCompletionResult.model_rebuild()
