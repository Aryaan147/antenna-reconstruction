import json
from typing import Dict, Any, Optional
from ..models import VLMAnalysis, VisualMissingItem

def parse_vlm_response(raw_response: str) -> Optional[VLMAnalysis]:
    """Parse and validate the JSON response from the VLM."""
    try:
        # Strip markdown block if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        data = json.loads(cleaned.strip())
        
        # Validate against the Pydantic model
        analysis = VLMAnalysis(**data)
        
        # Normalize status
        if analysis.status not in ("COMPLETE", "MISSING", "UNCERTAIN"):
            return None
            
        for item in analysis.missing_items:
            if item.type not in ("PARAMETER", "GEOMETRY", "TOPOLOGY"):
                item.type = "GEOMETRY" # fallback
                
        return analysis
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse VLM response: {e}")
        return None
