from typing import Dict, Any
from ..models import GeometryCompletionRequest, GeometryCompletionResult, CompletionDerivation
from . import rules

def construct_geometry(request: GeometryCompletionRequest) -> GeometryCompletionResult:
    """Process missing items and apply deterministic mathematical rules."""
    
    result = GeometryCompletionResult()
    
    for item in request.missing_items:
        feature_lower = item.feature.lower()
        
        # Example 1: explicit dimension or estimation for a known parameter (FI)
        if "inset" in feature_lower or ("notch" in feature_lower and "depth" in feature_lower) or "feed_offset" in feature_lower or feature_lower == "fi":
            val_and_method = rules.construct_inset_feed(request.parameters, item.visible_dimensions, item.estimations)
            if val_and_method is not None:
                val, method = val_and_method
                result.resolved_parameters["FI"] = val
                result.derivations.append(CompletionDerivation(
                    parameter="FI",
                    value=val,
                    source="FIGURE_EXPLICIT" if item.visible_dimensions else "MATHEMATICAL_DERIVATION",
                    method=method
                ))
                continue
                
        # Example 2: proportional estimation for slot gap (FG)
        elif "gap" in feature_lower or "slot" in feature_lower or "width" in feature_lower:
            # First try explicit dimension, though unlikely for FG
            if item.visible_dimensions and len(item.visible_dimensions) == 1:
                val = item.visible_dimensions[0]
                method = "explicit_figure_dimension"
            else:
                val_and_method = rules.derive_parameter_from_estimation(request.parameters, item.estimations)
                if val_and_method is not None:
                    val, method = val_and_method
                else:
                    val = None
                    
            if val is not None:
                result.resolved_parameters["FG"] = val
                result.derivations.append(CompletionDerivation(
                    parameter="FG",
                    value=val,
                    source="FIGURE_EXPLICIT" if item.visible_dimensions else "MATHEMATICAL_DERIVATION",
                    method=method
                ))
                continue
                
        # Example 3: topological geometry addition
        elif item.feature == "tapered_base":
            val_and_method = rules.construct_tapered_base(request.parameters)
            if val_and_method is not None:
                geom, method = val_and_method
                result.derived_geometry["tapered_base"] = geom
                result.derivations.append(CompletionDerivation(
                    parameter="tapered_base",
                    value=0.0, # N/A for complex geometry
                    source="MATHEMATICAL_DERIVATION",
                    method=method
                ))
                continue
                
        # If we reach here, we couldn't resolve the item
        result.unresolved.append(item.feature)
        
    return result
