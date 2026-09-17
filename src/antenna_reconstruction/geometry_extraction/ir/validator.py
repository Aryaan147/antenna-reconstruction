from typing import List, Set
from .models import GeometryIR, Diagnostic

SEMANTIC_TYPES = {
    "substrate", "radiator", "patch", "ground", "feed", "slot", "via", "stub", 
    "cutout", "hole", "connector", "boundary", "unknown"
}

PRIMITIVE_TYPES = {
    "point", "line", "rectangle", "circle", "arc", "polygon", "unknown"
}

PARAMETER_TYPES = {
    "length", "width", "height", "radius", "diameter", "angle", "frequency", 
    "material_property", "coordinate", "other"
}

CONSTRAINT_TYPES = {
    "CENTER", "CENTER_X", "CENTER_Y", "OFFSET_X", "OFFSET_Y", "DISTANCE", 
    "WIDTH", "HEIGHT", "LENGTH", "RADIUS", "DIAMETER", "HORIZONTAL", 
    "VERTICAL", "PARALLEL", "PERPENDICULAR", "SYMMETRIC_X", "SYMMETRIC_Y", 
    "CONNECTED", "INSIDE", "TOUCHING", "INTERSECTS", "MIRROR", "ROTATE", 
    "TRANSLATE"
}

def validate_geometry_ir(ir: GeometryIR) -> GeometryIR:
    """Validates the GeometryIR in-place and adds diagnostics if errors are found."""
    entity_ids: Set[str] = set()
    param_ids: Set[str] = set()
    constraint_ids: Set[str] = set()
    
    # Validation flags
    
    for entity in ir.entities:
        if entity.id in entity_ids:
            ir.diagnostics.append(Diagnostic(
                type="INVALID_ENTITY",
                message=f"Duplicate entity ID: {entity.id}",
                objects=[entity.id]
            ))
        entity_ids.add(entity.id)
        
        if entity.primitive not in PRIMITIVE_TYPES:
            ir.diagnostics.append(Diagnostic(
                type="UNKNOWN_PRIMITIVE",
                message=f"Unknown primitive type: {entity.primitive}",
                objects=[entity.id]
            ))
            
        if entity.semantic_type not in SEMANTIC_TYPES:
            ir.diagnostics.append(Diagnostic(
                type="INVALID_ENTITY",
                message=f"Unknown semantic type: {entity.semantic_type}",
                objects=[entity.id]
            ))

    # Parameter values map (to detect contradictions)
    # Mapping constraint logic for contradiction checking on parameters
    param_value_map = {}

    for param in ir.parameters:
        if param.id in param_ids:
            ir.diagnostics.append(Diagnostic(
                type="INVALID_PARAMETER",
                message=f"Duplicate parameter ID: {param.id}",
                parameters=[param.id]
            ))
        param_ids.add(param.id)
        
        if param.unit != "mm":
            ir.diagnostics.append(Diagnostic(
                type="UNKNOWN_UNIT",
                message=f"Unknown or non-canonical unit: {param.unit}",
                parameters=[param.id]
            ))
            
        if param.parameter_type in {"length", "width", "height", "radius", "diameter"} and param.value < 0:
            ir.diagnostics.append(Diagnostic(
                type="INVALID_PARAMETER",
                message=f"Negative value for length/width/height/radius/diameter: {param.value}",
                parameters=[param.id]
            ))
            
        if not param.source_refs:
            ir.diagnostics.append(Diagnostic(
                type="MISSING_SOURCE_REFERENCE",
                message=f"Missing source reference for parameter {param.id}",
                parameters=[param.id]
            ))
            
        # Check for contradictions
        # Let's say we identify contradictions if same parameter_type is defined for same object
        # We can extract the object ID from the parameter ID if we assume naming convention 'obj_type' 
        # But according to spec, "conflict diagnostic" should be produced.
        # "If input contains: The patch width is 40 mm. The patch width is 42 mm. -> CONFLICTING_PARAMETER_VALUES"
        # We will do a basic check here if multiple parameters have the same base prefix and parameter_type but different values.
        base_name = param.id.rsplit('_', 1)[0] if param.id[-1].isdigit() else param.id
        if base_name in param_value_map:
            if param_value_map[base_name] != param.value:
                ir.diagnostics.append(Diagnostic(
                    type="CONFLICTING_PARAMETER_VALUES",
                    severity="error",
                    message=f"Conflicting values for {base_name}: {param_value_map[base_name]} vs {param.value}",
                    parameters=[param.id]
                ))
        else:
            param_value_map[base_name] = param.value

    for constraint in ir.constraints:
        if constraint.id in constraint_ids:
            ir.diagnostics.append(Diagnostic(
                type="INVALID_CONSTRAINT",
                message=f"Duplicate constraint ID: {constraint.id}",
            ))
        constraint_ids.add(constraint.id)
        
        if constraint.type not in CONSTRAINT_TYPES:
            ir.diagnostics.append(Diagnostic(
                type="UNKNOWN_RELATIONSHIP",
                message=f"Unknown constraint type: {constraint.type}",
            ))
            
        for obj in constraint.objects:
            if obj not in entity_ids:
                ir.diagnostics.append(Diagnostic(
                    type="INVALID_CONSTRAINT",
                    message=f"Constraint references unknown entity: {obj}",
                ))
                
        if not constraint.source_refs:
            ir.diagnostics.append(Diagnostic(
                type="MISSING_SOURCE_REFERENCE",
                message=f"Missing source reference for constraint {constraint.id}"
            ))

    # Coordinate system validation
    if ir.coordinate_system.dimension not in {2, 3}:
        ir.diagnostics.append(Diagnostic(
            type="INVALID_SCHEMA",
            message="Coordinate system dimension must be 2 or 3"
        ))
        
    if ir.coordinate_system.unit != "mm":
        ir.diagnostics.append(Diagnostic(
            type="UNKNOWN_UNIT",
            message=f"Coordinate system unit must be mm, got {ir.coordinate_system.unit}"
        ))

    return ir
