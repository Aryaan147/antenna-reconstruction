import pytest
import os
import sys

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from antenna_reconstruction.visual_completion.models import GeometryCompletionRequest, VisualMissingItem
from antenna_reconstruction.visual_completion.geometry.constructor import construct_geometry

def test_constructor_handles_vlm_aliases():
    """Verify the constructor correctly maps 'notch_depth' and 'feed_offset' to FI."""
    
    request = GeometryCompletionRequest(
        parameters={"W": 40.0, "L": 30.0, "FW": 3.1},
        missing_items=[
            VisualMissingItem(
                type="PARAMETER",
                feature="notch_depth",
                description="The inset feed notch depth",
                related_parameters=["L"],
                visible_dimensions=[9.25],
                confidence=0.95
            ),
            VisualMissingItem(
                type="PARAMETER",
                feature="feed_offset",
                description="Distance to the feed point",
                related_parameters=["SL"],
                visible_dimensions=[23.7],
                confidence=0.95
            ),
            VisualMissingItem(
                type="PARAMETER",
                feature="slot_gap",
                description="The gap on either side of the feed line",
                related_parameters=["FW"],
                visible_dimensions=[],
                estimations={"relative_to": "FW", "ratio": 0.5},
                confidence=0.9
            ),
            VisualMissingItem(
                type="PARAMETER",
                feature="unknown_feature",
                description="Something else entirely",
                related_parameters=[],
                visible_dimensions=[10.0],
                confidence=0.9
            )
        ]
    )
    
    result = construct_geometry(request)
    
    # It should have resolved FI (from the first one it hits that has dimensions, or overwritten)
    assert "FI" in result.resolved_parameters
    # We should have at least one derivation for FI
    fi_derivations = [d for d in result.derivations if d.parameter == "FI"]
    assert len(fi_derivations) > 0
    assert fi_derivations[-1].value in [9.25, 23.7]
    
    # It should have resolved FG from the estimation
    assert "FG" in result.resolved_parameters
    assert result.resolved_parameters["FG"] == 1.55 # FW=3.1 * 0.5 = 1.55
    
    # "unknown_feature" should still be unresolved
    assert "unknown_feature" in result.unresolved
