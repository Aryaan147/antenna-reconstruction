import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))
from antenna_reconstruction.visual_completion.vlm import client

# Override the system prompt for testing
client.VLM_SYSTEM_PROMPT = """You are a Visual Gap Detector for an antenna reconstruction system.

Your job is to compare an antenna figure with a provided dictionary of extracted structure (parameters).
You must identify relevant information visible in the figure that is absent, incomplete, or inconsistent in the extracted structure.

CRITICAL RULES:
1. Do not invent numerical values. If a dimension is not explicitly written in the figure as text, leave `visible_dimensions` empty.
2. If a dimension is missing, use the `estimations` field to provide a ratio relative to a known parameter (e.g. if the depth looks like 1/3 of patch length L, output `{"relative_to": "L", "ratio": 0.33}`).
3. If you identify an inset feed or notch, you MUST attempt to identify both its depth (e.g. into the patch) and the width/gap of the slot on either side of the feed line.

You must output STRICT JSON matching the following schema.
Output NO markdown formatting and NO conversational text. Just the raw JSON.

{
  "status": "COMPLETE | MISSING | UNCERTAIN",
  "missing_items": [
    {
      "type": "PARAMETER | GEOMETRY | TOPOLOGY",
      "feature": "feature_name",
      "description": "Short description of the missing feature.",
      "related_parameters": ["W", "L"],
      "visible_dimensions": [],
      "estimations": {
        "relative_to": "L",
        "ratio": 0.33
      },
      "confidence": 0.95
    }
  ]
}
"""

def main():
    load_dotenv()
    
    # Use the extracted params from step 1
    params_path = "results/step1_extracted_parameters.json"
    with open(params_path, "r") as f:
        params = json.load(f)
        
    figure_path = "data/raw/papers/microstrip_patch_antenna.png"
    
    raw_response = client.analyze_figure(figure_path, params)
    print(raw_response)
    
if __name__ == "__main__":
    main()
