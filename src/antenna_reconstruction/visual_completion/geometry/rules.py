from typing import Dict, Any, Optional, Tuple

def construct_inset_feed(parameters: Dict[str, float], visible_dimensions: list[float], estimations: Dict[str, Any] = None) -> Optional[Tuple[float, str]]:
    """
    Attempt to construct an inset feed parameter (FI) if one is missing but visible in the figure.
    This rule grabs the explicitly visible dimension if it exists and is unambiguous.
    If no explicit dimension exists, it falls back to parsing proportional estimations.
    """
    if visible_dimensions and len(visible_dimensions) == 1:
        return visible_dimensions[0], "explicit_figure_dimension"
        
    if estimations:
        return derive_parameter_from_estimation(parameters, estimations)
        
    return None

def derive_parameter_from_estimation(parameters: Dict[str, float], estimations: Dict[str, Any]) -> Optional[Tuple[float, str]]:
    """
    Derive a parameter from a proportional estimation (e.g. {"relative_to": "FW", "ratio": 0.5}).
    """
    try:
        relative_to = estimations.get("relative_to")
        ratio = float(estimations.get("ratio", 0.0))
        
        if relative_to in parameters and ratio > 0:
            val = parameters[relative_to] * ratio
            return val, f"estimated as {ratio}x of {relative_to} ({parameters[relative_to]})"
    except (ValueError, TypeError):
        pass
        
    return None



def construct_tapered_base(parameters: Dict[str, float]) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Construct a symmetric tapered polygonal base if requested by the VLM.
    Required inputs: W (patch width), FW (feed width), GL (ground/base length or similar metric).
    
    This is a simplistic deterministic rule matching the architecture document's example.
    """
    if "W" not in parameters or "FW" not in parameters or "GL" not in parameters:
        return None
        
    W = parameters["W"]
    FW = parameters["FW"]
    GL = parameters["GL"]
    
    center_x = W / 2.0
    feed_left = center_x - FW / 2.0
    feed_right = center_x + FW / 2.0
    base_y = GL
    
    # Constructing a basic taper from full width W down to feed width FW over distance GL
    geometry = {
        "vertices": [
            (0.0, 0.0),
            (W, 0.0),
            (feed_right, base_y),
            (feed_left, base_y)
        ]
    }
    
    return geometry, "tapered_base_geometry"
