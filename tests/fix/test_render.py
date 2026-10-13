import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
import os

def render():
    fig, ax = plt.subplots(figsize=(6, 6))
    
    verts = [(18.7, 14.45), (18.7, 43.349999999999994), (58.099999999999994, 43.349999999999994), (58.099999999999994, 14.45), (43.05, 14.45), (43.05, 23.7), (39.949999999999996, 23.7), (39.949999999999996, 14.45), (36.85, 14.45), (36.85, 23.7), (33.75, 23.7), (33.75, 14.45), (18.7, 14.45)]
    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(verts) - 2) + [MplPath.CLOSEPOLY]
    
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor="#111111", edgecolor="none"))
    
    # Add substrate
    ax.set_xlim(0, 76.8)
    ax.set_ylim(0, 57.8)
    ax.set_aspect("equal")
    
    os.makedirs("../../brain/3e2f44b7-5e7a-40f1-b1cb-03809f805fba/scratch", exist_ok=True)
    fig.savefig("../../brain/3e2f44b7-5e7a-40f1-b1cb-03809f805fba/scratch/test_patch.png", dpi=150)
    print("Saved test patch!")

if __name__ == "__main__":
    render()
