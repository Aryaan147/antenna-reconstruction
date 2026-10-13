import pytest
from unittest.mock import patch
from antenna_reconstruction.visual_completion.pipeline import complete
from antenna_reconstruction.visual_completion.models import VLMAnalysis, VisualMissingItem
from antenna_reconstruction.template_pipeline import TemplatePipeline

# Mock VLM responses for different test cases
def mock_vlm_complete(*args, **kwargs):
    return """
    {
      "status": "COMPLETE",
      "missing_items": []
    }
    """

def mock_vlm_dimension(*args, **kwargs):
    return """
    {
      "status": "MISSING",
      "missing_items": [
        {
          "type": "PARAMETER",
          "feature": "FI",
          "description": "Inset depth visible.",
          "related_parameters": [],
          "visible_dimensions": [5.0],
          "confidence": 0.95
        }
      ]
    }
    """

def mock_vlm_geometry(*args, **kwargs):
    return """
    {
      "status": "MISSING",
      "missing_items": [
        {
          "type": "GEOMETRY",
          "feature": "tapered_base",
          "description": "Tapered base visible.",
          "related_parameters": ["W", "FW", "GL"],
          "visible_dimensions": [],
          "confidence": 0.95
        }
      ]
    }
    """

def mock_vlm_underdetermined(*args, **kwargs):
    return """
    {
      "status": "MISSING",
      "missing_items": [
        {
          "type": "GEOMETRY",
          "feature": "custom_polygon",
          "description": "Polygon visible but dimensions unknown.",
          "related_parameters": [],
          "visible_dimensions": [],
          "confidence": 0.8
        }
      ]
    }
    """

def mock_vlm_overwrite(*args, **kwargs):
    return """
    {
      "status": "MISSING",
      "missing_items": [
        {
          "type": "PARAMETER",
          "feature": "W",
          "description": "W should be 38.",
          "related_parameters": [],
          "visible_dimensions": [38.0],
          "confidence": 0.9
        }
      ]
    }
    """

def mock_vlm_failure(*args, **kwargs):
    return None

def mock_vlm_malformed(*args, **kwargs):
    return "This is not json"

@patch('antenna_reconstruction.visual_completion.pipeline.analyze_figure', side_effect=mock_vlm_complete)
def test_nothing_missing(mock_analyze):
    params = {"W": 40.0, "L": 30.0}
    completion = complete("dummy.png", params)
    assert completion.vlm_status == "COMPLETE"
    assert completion.enriched_parameters == params

@patch('antenna_reconstruction.visual_completion.pipeline.analyze_figure', side_effect=mock_vlm_dimension)
def test_figure_only_dimension(mock_analyze):
    params = {"W": 40.0, "L": 30.0}
    completion = complete("dummy.png", params)
    assert completion.vlm_status == "MISSING"
    assert completion.constructor_status == "RESOLVED"
    assert "FI" in completion.enriched_parameters
    assert completion.enriched_parameters["FI"] == 5.0
    assert len(completion.derivations) == 1
    assert completion.derivations[0].parameter == "FI"

@patch('antenna_reconstruction.visual_completion.pipeline.analyze_figure', side_effect=mock_vlm_geometry)
def test_figure_only_geometry(mock_analyze):
    params = {"W": 40.0, "FW": 3.0, "GL": 20.0}
    completion = complete("dummy.png", params)
    assert completion.vlm_status == "MISSING"
    assert completion.constructor_status == "RESOLVED"
    assert len(completion.derivations) == 1
    assert completion.derivations[0].parameter == "tapered_base"
    assert completion.derivations[0].source == "MATHEMATICAL_DERIVATION"

@patch('antenna_reconstruction.visual_completion.pipeline.analyze_figure', side_effect=mock_vlm_underdetermined)
def test_underdetermined_geometry(mock_analyze):
    params = {"W": 40.0}
    completion = complete("dummy.png", params)
    assert completion.vlm_status == "MISSING"
    assert completion.constructor_status == "PARTIAL"
    assert "custom_polygon" in completion.unresolved
    assert completion.enriched_parameters == params

@patch('antenna_reconstruction.visual_completion.pipeline.analyze_figure', side_effect=mock_vlm_failure)
def test_vlm_failure(mock_analyze):
    params = {"W": 40.0}
    completion = complete("dummy.png", params)
    assert completion.vlm_status == "SKIPPED"
    assert completion.constructor_status == "SKIPPED"
    assert completion.enriched_parameters == params

@patch('antenna_reconstruction.visual_completion.pipeline.analyze_figure', side_effect=mock_vlm_malformed)
def test_vlm_malformed(mock_analyze):
    params = {"W": 40.0}
    completion = complete("dummy.png", params)
    assert completion.vlm_status == "MALFORMED"
    assert completion.enriched_parameters == params

def test_no_figure_supplied():
    pipeline = TemplatePipeline()
    params = {"W": 40.0, "L": 30.0}
    result = pipeline.run_from_parameters(params, "out.dxf", template_name="rectangular_patch")
    assert result.success is True
    assert result.template == "rectangular_patch"

@patch('antenna_reconstruction.visual_completion.pipeline.analyze_figure', side_effect=mock_vlm_overwrite)
def test_existing_text_values_preserved(mock_analyze):
    params = {"W": 40.0, "L": 30.0}
    completion = complete("dummy.png", params)
    # The VLM suggested W=38, but the constructor shouldn't overwrite existing W=40
    # Actually, our constructor logic explicitly prevents overwriting existing keys
    assert completion.enriched_parameters["W"] == 40.0
