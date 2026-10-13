import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))
from antenna_reconstruction.visual_completion.vlm import client

def main():
    load_dotenv()
    params_path = "../../results/step1_extracted_parameters.json"
    with open(params_path, "r") as f:
        params = json.load(f)
        
    figure_path = "../../data/raw/papers/microstrip_patch_antenna.png"
    
    raw_response = client.analyze_figure(figure_path, params)
    print(raw_response)

if __name__ == "__main__":
    main()
