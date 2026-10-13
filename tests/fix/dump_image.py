import json
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))
from antenna_reconstruction.templates import get_template

def main():
    with open("../../results/step3_final_parameters.json", "r") as f:
        params = json.load(f)
        
    built = get_template("rectangular_patch").build(params)
    
    for shape in built.shapes:
        if shape.id == "patch":
            print(f"PATCH LAYER: {shape.layer}")
            for ext, holes in shape.parts():
                print(f"  EXTERIOR: {ext}")
                print(f"  HOLES: {holes}")
        elif shape.id == "feed":
            print(f"FEED LAYER: {shape.layer}")
            for ext, holes in shape.parts():
                print(f"  EXTERIOR: {ext}")

if __name__ == "__main__":
    main()
