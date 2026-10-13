import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))
from antenna_reconstruction.visual_completion.vlm import client

def main():
    load_dotenv()
    
    # Use the extracted params from step 1
    params_path = "../../results/step1_extracted_parameters.json"
    with open(params_path, "r") as f:
        params = json.load(f)
        
    figure_path = "../../data/raw/papers/microstrip_patch_antenna.png"
    
    raw_response = client.analyze_figure(figure_path, params)
    
    out_path = "data/raw_vlm_output.json"
    
    try:
        # Attempt to clean markdown
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        data = json.loads(cleaned.strip())
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Raw VLM JSON saved to {out_path}")
    except Exception as e:
        print(f"Failed to parse VLM response as JSON: {e}")
        with open(out_path, "w") as f:
            f.write(raw_response or "")

if __name__ == "__main__":
    main()
