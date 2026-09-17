import ezdxf
from typing import Optional
from ..models import CADModel

class DXFExporter:
    def export(self, model: CADModel, filepath: str) -> bool:
        """
        Exports the internal CADModel to a DXF file using ezdxf.
        Returns True if successful, False otherwise.
        """
        try:
            # Create a new DXF document.
            doc = ezdxf.new('R2010')
            
            # Setup units.
            # DXF uses 4 for mm.
            if model.unit == "mm":
                doc.header['$INSUNITS'] = 4 
                
            msp = doc.modelspace()
            
            for rect in model.rectangles:
                # Ensure the layer exists
                if rect.layer not in doc.layers:
                    doc.layers.add(name=rect.layer)
                    
                points = [(p.x, p.y) for p in rect.vertices]
                
                # lwpolyline can take a list of (x,y) points.
                # close=True makes it a closed polygon.
                msp.add_lwpolyline(points, close=True, dxfattribs={'layer': rect.layer})
                
            doc.saveas(filepath)
            return True
            
        except Exception as e:
            print(f"Error exporting to DXF: {e}")
            return False
