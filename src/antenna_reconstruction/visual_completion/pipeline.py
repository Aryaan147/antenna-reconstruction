from typing import Dict, Optional
from .models import Completion, GeometryCompletionRequest
from .vlm.client import analyze_figure
from .vlm.parser import parse_vlm_response
from .geometry.constructor import construct_geometry

def complete(figure_path: str, parameters: Dict[str, float]) -> Completion:
    """Orchestrate the visual completion process."""
    
    # Base fallback completion if things fail
    base_completion = Completion(
        enriched_parameters=dict(parameters),
        vlm_status="SKIPPED",
        constructor_status="SKIPPED"
    )
    
    # 1. Call VLM
    raw_response = analyze_figure(figure_path, parameters)
    if raw_response is None:
        return base_completion
        
    analysis = parse_vlm_response(raw_response)
    if analysis is None:
        base_completion.vlm_status = "MALFORMED"
        return base_completion
        
    if analysis.status == "COMPLETE":
        base_completion.vlm_status = "COMPLETE"
        return base_completion
        
    # 2. Call Mathematical Constructor
    request = GeometryCompletionRequest(
        parameters=parameters,
        missing_items=analysis.missing_items
    )
    
    construction_result = construct_geometry(request)
    
    # 3. Merge resolved information
    enriched = dict(parameters)
    
    # We do not overwrite existing values silently according to rules.
    for k, v in construction_result.resolved_parameters.items():
        if k not in enriched:
            enriched[k] = v
            
    # Geometry additions (like tapered_base) should ideally be handled by 
    # the downstream pipeline, but for now we just pass them along if needed.
    # The dictionary of parameters is enriched with new explicit values.
            
    return Completion(
        enriched_parameters=enriched,
        vlm_status=analysis.status,
        constructor_status="RESOLVED" if not construction_result.unresolved else "PARTIAL",
        derivations=construction_result.derivations,
        unresolved=construction_result.unresolved
    )
