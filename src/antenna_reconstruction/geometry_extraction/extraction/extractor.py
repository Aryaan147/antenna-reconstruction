import re
from typing import List, Tuple
from ..ir.models import GeometryIR, Entity, Parameter, Constraint
from ..ingestion.models import MockGeometryInput

class RuleBasedExtractor:
    def __init__(self):
        # We need simple deterministic regex rules to handle the specific mock cases.
        pass
        
    def extract(self, input_data: MockGeometryInput) -> GeometryIR:
        ir = GeometryIR()
        text = input_data.text
        source_id = input_data.source_id
        
        # Split into sentences for processing, being careful not to split on decimal points
        sentences = [s.strip() for s in re.split(r'\.\s*(?=[A-Z]|$)', text) if s.strip()]
        
        for idx, sentence in enumerate(sentences):
            # Evidence source ref tracking
            ref_id = f"e{idx+1:03d}"
            ir.evidence.append({
                "id": ref_id,
                "source_id": source_id,
                "source_type": input_data.metadata.get("source_type", "mock_text"),
                "location": {
                    "type": "text",
                    "offset_start": text.find(sentence),
                    "offset_end": text.find(sentence) + len(sentence)
                },
                "content": sentence
            })

            # Case 1 & 2 variant A: "The X is a rectangle with width Y mm and height Z mm."
            # Case 2 variant B: "The rectangular X has a width of Y mm and a height of Z mm."
            # Case 6 variant C: "The X has dimensions Y mm x Z mm" or "Y mm × Z mm"
            
            # Helper to add entity
            def add_entity(entity_id: str, primitive: str, semantic_type: str):
                if not any(e.id == entity_id for e in ir.entities):
                    ir.entities.append(Entity(
                        id=entity_id,
                        primitive=primitive,
                        semantic_type=semantic_type,
                        source_refs=[ref_id]
                    ))
            
            # Helper to add parameter
            def add_param(param_id: str, value: float, unit: str, p_type: str):
                ir.parameters.append(Parameter(
                    id=param_id,
                    value=value,
                    unit=unit,
                    parameter_type=p_type,
                    source_refs=[ref_id],
                    evidence_type="explicit"
                ))
            
            # Match Entity Declarations and Dimensions
            # Matches: The substrate is a rectangle with width 76.8 mm and height 57.8 mm
            # Matches: The rectangular patch has a width of 39.4 mm and a height of 28.9 mm
            match_dims1 = re.search(r"The (?:rectangular )?(\w+) (?:is a rectangle with|has a) width (?:of )?([\d.]+) (mm) and (?:a )?height (?:of )?([\d.]+) (mm)", sentence, re.IGNORECASE)
            # Matches: The patch has dimensions 40 mm x 30 mm
            match_dims2 = re.search(r"The (?:rectangular )?(\w+) has dimensions ([\d.]+) (mm) [x×] ([\d.]+) (mm)", sentence, re.IGNORECASE)
            # Matches: The patch width is 40 mm
            match_dims3 = re.search(r"The (\w+) (width|height|length) is ([\d.]+) (mm)", sentence, re.IGNORECASE)
            
            if match_dims1:
                obj, w_val, w_unit, h_val, h_unit = match_dims1.groups()
                sem_type = "substrate" if obj.lower() == "substrate" else "radiator"
                add_entity(obj.lower(), "rectangle", sem_type)
                add_param(f"{obj.lower()}_width", float(w_val), w_unit, "width")
                add_param(f"{obj.lower()}_height", float(h_val), h_unit, "height")
                
            elif match_dims2:
                obj, w_val, w_unit, h_val, h_unit = match_dims2.groups()
                sem_type = "substrate" if obj.lower() == "substrate" else "radiator"
                # If it just says "The patch", we assume it's a rectangle based on width/height or context
                # but to be strict, if it wasn't specified as rectangular, maybe 'unknown'. We'll assume rectangle for now if dimensions are w x h.
                add_entity(obj.lower(), "rectangle", sem_type)
                add_param(f"{obj.lower()}_width", float(w_val), w_unit, "width")
                add_param(f"{obj.lower()}_height", float(h_val), h_unit, "height")
                
            elif match_dims3:
                obj, dim_type, val, unit = match_dims3.groups()
                sem_type = "substrate" if obj.lower() == "substrate" else "radiator"
                # If only one dimension is given, we can't be sure of primitive, but we add it if not exists.
                add_entity(obj.lower(), "rectangle", sem_type)  # Defaulting to rectangle for mock
                # Handle contradicting case (Case 7): if it already exists, append another parameter
                # We append a unique ID like patch_width_1, patch_width_2
                existing = [p for p in ir.parameters if p.id.startswith(f"{obj.lower()}_{dim_type.lower()}")]
                if existing:
                    # Rename the existing one if it doesn't have a suffix
                    if not existing[0].id[-1].isdigit():
                        existing[0].id = f"{existing[0].id}_1"
                    new_idx = len(existing) + 1
                    add_param(f"{obj.lower()}_{dim_type.lower()}_{new_idx}", float(val), unit, dim_type.lower())
                else:
                    add_param(f"{obj.lower()}_{dim_type.lower()}", float(val), unit, dim_type.lower())

            # Match Relationships
            # Matches: The patch is centered on the substrate
            match_center = re.search(r"The (?:rectangular )?(\w+) is centered on the (\w+)", sentence, re.IGNORECASE)
            # Matches: The patch is located 5 mm to the right of the substrate center
            match_offset = re.search(r"The (\w+) is located ([\d.]+) (mm) to the right of the (\w+) center", sentence, re.IGNORECASE)
            
            if match_center:
                obj1, obj2 = match_center.groups()
                sem_type1 = "substrate" if obj1.lower() == "substrate" else "radiator"
                sem_type2 = "substrate" if obj2.lower() == "substrate" else "radiator"
                
                # Ensure both entities exist before adding constraints
                add_entity(obj1.lower(), "rectangle", sem_type1)
                add_entity(obj2.lower(), "rectangle", sem_type2)
                
                ir.constraints.append(Constraint(
                    id=f"c{len(ir.constraints)+1:03d}",
                    type="CENTER_X",
                    objects=[obj1.lower(), obj2.lower()],
                    source_refs=[ref_id]
                ))
                ir.constraints.append(Constraint(
                    id=f"c{len(ir.constraints)+1:03d}",
                    type="CENTER_Y",
                    objects=[obj1.lower(), obj2.lower()],
                    source_refs=[ref_id]
                ))
            elif match_offset:
                obj1, val, unit, obj2 = match_offset.groups()
                sem_type1 = "substrate" if obj1.lower() == "substrate" else "radiator"
                sem_type2 = "substrate" if obj2.lower() == "substrate" else "radiator"
                
                # Ensure both entities exist
                add_entity(obj1.lower(), "rectangle", sem_type1)
                add_entity(obj2.lower(), "rectangle", sem_type2)
                
                ir.constraints.append(Constraint(
                    id=f"c{len(ir.constraints)+1:03d}",
                    type="OFFSET_X",
                    objects=[obj1.lower(), obj2.lower()],
                    parameters={"value": float(val), "unit": unit},
                    source_refs=[ref_id]
                ))

        if any(e.id == "substrate" for e in ir.entities):
            ir.coordinate_system.origin_definition = {"type": "substrate_bottom_left"}

        return ir
