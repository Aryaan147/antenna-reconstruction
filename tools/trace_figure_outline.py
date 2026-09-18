"""Trace the metal outlines of Fig. 1 by colour.

Arrows drawn over the figure are inpainted by nearest known colour, which keeps
thin features (the horse-shoe slots the arrows sit inside) intact. The mask is
then converted to a polygon by unioning its row runs, which is exact - contour
tracing plus buffer(0) silently fills open notches.
"""
import json, sys
import numpy as np, pypdfium2 as pdfium
from scipy.ndimage import distance_transform_edt, label
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
# Only inpaint arrows that lie over the antenna itself; the dimension arrows
# outside it must not be absorbed into the metal.
ys,xs=np.where(known)
pad=6
box_mask=np.zeros(known.shape,bool)
box_mask[max(ys.min()-pad,0):ys.max()+pad, max(xs.min()-pad,0):xs.max()+pad]=True
_,idx=distance_transform_edt(~known,return_indices=True)
todo=dark&~known&box_mask
filled=lab.copy(); filled[todo]=lab[idx[0][todo],idx[1][todo]]

def clean(m, keep_frac=0.05):
    """Drop speckle WITHOUT eroding the shape or discarding real parts.

    Two mistakes were made here. A binary opening ate the thin parts - the feed
    strip and the semicircular edge tabs - which shrank the traced bounding
    box and so misplaced every feature inside it on rescaling. Then keeping
    only the LARGEST component threw away half the ground plane, which the
    feed splits into two separate pieces. Every component of a meaningful size
    is kept instead.
    """
    l,n=label(m)
    if n==0:
        return m
    sz=np.bincount(l.ravel()); sz[0]=0
    keep=np.where(sz >= sz.max()*keep_frac)[0]
    return np.isin(l, keep)

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

# The substrate's own extent, so each shape's size can be recorded as a
# fraction of the board and later checked against the stated dimensions.
sy,sx=np.where(filled>0)
SUB=(sx.min(), sx.max(), sy.min(), sy.max())
SUB_W, SUB_H = SUB[1]-SUB[0], SUB[3]-SUB[2]

out={}
for name,code in (('patch',1),('ground',3)):
    m=clean(filled==code)
    poly=polygonize(m).simplify(1.2, preserve_topology=True)
    parts=list(getattr(poly,'geoms',None) or [poly])
    parts=[p for p in parts if p.area > max(q.area for q in parts)*0.02]
    allx=[x for p in parts for x in p.exterior.xy[0]]
    ally=[y for p in parts for y in p.exterior.xy[1]]
    X0,X1,Y0,Y1=min(allx),max(allx),min(ally),max(ally)
    n=lambda cs:[[round((x-X0)/(X1-X0),5),round(1-(y-Y0)/(Y1-Y0),5)] for x,y in cs]
    m_ys,m_xs=np.where(m)
    out[name]={'parts':[{'exterior':n(p.exterior.coords[:-1]),
                         'holes':[n(r.coords[:-1]) for r in p.interiors
                                  if abs(r.convex_hull.area)>p.area*0.001]}
                        for p in parts],
               # What the FIGURE says this shape's size is, as a fraction of
               # the board. Lets a caller test the figure against the table.
               'substrate_fraction':{
                   'width': round(float(m_xs.max()-m_xs.min())/SUB_W, 4),
                   'height': round(float(m_ys.max()-m_ys.min())/SUB_H, 4)}}
    sf=out[name]['substrate_fraction']
    pts=sum(len(p['exterior']) for p in out[name]['parts'])
    print(f'{name}: {len(out[name]["parts"])} part(s), {pts} pts, '
          f'figure says {sf["width"]:.3f} x {sf["height"]:.3f} of the board')
json.dump(out,open(sys.argv[1],'w'),indent=1)

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(5,6))
for nm,col in (('ground','#f08b33'),('patch','#c8960c')):
    for part in out[nm]['parts']:
        e=part['exterior']; ax.fill([p[0] for p in e],[p[1] for p in e],color=col)
        for hh in part['holes']: ax.fill([p[0] for p in hh],[p[1] for p in hh],color='white')
ax.set_aspect('equal'); ax.set_title('traced from Fig. 1')
fig.savefig(sys.argv[2],dpi=110)
print('saved')
