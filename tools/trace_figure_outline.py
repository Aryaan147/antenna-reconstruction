"""Trace the metal outlines of Fig. 1 by colour.

Arrows drawn over the figure are inpainted by nearest known colour, which keeps
thin features (the horse-shoe slots the arrows sit inside) intact. The mask is
then converted to a polygon by unioning its row runs, which is exact - contour
tracing plus buffer(0) silently fills open notches.
"""
import json, sys
import numpy as np, pypdfium2 as pdfium
from scipy.ndimage import distance_transform_edt, binary_opening, label
from shapely.geometry import box
from shapely.ops import unary_union

P='/Users/adityapathania/Downloads/A machine learning driven computationally efficient horse shoe shaped antenna design for internet of medical things.pdf'
im=pdfium.PdfDocument(P)[4].render(scale=8).to_pil().convert('RGB')
w,h=im.size
a=np.asarray(im.crop((int(w*0.32),int(h*0.085),int(w*0.90),int(h*0.49)))).astype(float)
def near(c,t=60): return (np.abs(a-np.array(c)).sum(2)<t)
g,b,o = near([191,145,0]), near([46,117,181]), near([251,143,53])
dark=(a.sum(2)<250); known=g|b|o
lab=np.zeros(known.shape,np.uint8); lab[g]=1; lab[b]=2; lab[o]=3
_,idx=distance_transform_edt(~known,return_indices=True)
todo=dark&~known
filled=lab.copy(); filled[todo]=lab[idx[0][todo],idx[1][todo]]

def clean(m):
    m=binary_opening(m,np.ones((5,5),bool))
    l,n=label(m)
    if n==0: return m
    sz=np.bincount(l.ravel()); sz[0]=0
    return l==sz.argmax()

def polygonize(mask, block=8):
    H,W=mask.shape
    H2,W2=H//block, W//block
    small=mask[:H2*block,:W2*block].reshape(H2,block,W2,block).mean((1,3))>0.5
    boxes=[]
    for y in range(H2):
        row=small[y]; x=0
        while x<W2:
            if row[x]:
                x2=x
                while x2+1<W2 and row[x2+1]: x2+=1
                boxes.append(box(x, y, x2+1, y+1))
                x=x2+1
            x+=1
    return unary_union(boxes)

out={}
for name,code in (('patch',1),('ground',3)):
    m=clean(filled==code)
    poly=polygonize(m)
    if poly.geom_type=='MultiPolygon': poly=max(poly.geoms,key=lambda p:p.area)
    poly=poly.simplify(1.2, preserve_topology=True)
    xs,ys=poly.exterior.xy
    X0,X1,Y0,Y1=min(xs),max(xs),min(ys),max(ys)
    n=lambda cs:[[round((x-X0)/(X1-X0),5),round(1-(y-Y0)/(Y1-Y0),5)] for x,y in cs]
    out[name]={'exterior':n(poly.exterior.coords[:-1]),
               'holes':[n(r.coords[:-1]) for r in poly.interiors if
                        abs(r.convex_hull.area)>poly.area*0.001]}
    print(f'{name}: {len(out[name]["exterior"])} pts, {len(out[name]["holes"])} holes, '
          f'area/bbox={poly.area/((X1-X0)*(Y1-Y0)):.3f}')
json.dump(out,open(sys.argv[1],'w'),indent=1)

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(5,6))
for nm,col in (('ground','#f08b33'),('patch','#c8960c')):
    e=out[nm]['exterior']; ax.fill([p[0] for p in e],[p[1] for p in e],color=col)
    for hh in out[nm]['holes']: ax.fill([p[0] for p in hh],[p[1] for p in hh],color='white')
ax.set_aspect('equal'); ax.set_title('traced from Fig. 1')
fig.savefig(sys.argv[2],dpi=110)
print('saved')
