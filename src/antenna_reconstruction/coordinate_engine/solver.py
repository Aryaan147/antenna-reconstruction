import sympy as sp
from typing import Dict, List, Tuple
from antenna_reconstruction.geometry_extraction.ir.models import GeometryIR, Diagnostic
from .models import ResolvedGeometry, SolveStatus, ResolvedEntity, ResolvedEntityGeometry, ResolvedParameter

class SympySolver:
    def __init__(self, ir: GeometryIR):
        self.ir = ir
        self.symbols: Dict[str, sp.Symbol] = {}
        self.equations: List[sp.Eq] = []
        self.diagnostics: List[Diagnostic] = []
        
    def get_symbol(self, name: str) -> sp.Symbol:
        if name not in self.symbols:
            self.symbols[name] = sp.Symbol(name)
        return self.symbols[name]

    def build_system(self):
        # Create symbols for all rectangular entities
        for ent in self.ir.entities:
            if ent.primitive == "rectangle":
                self.get_symbol(f"{ent.id}_x_left")
                self.get_symbol(f"{ent.id}_x_right")
                self.get_symbol(f"{ent.id}_y_bottom")
                self.get_symbol(f"{ent.id}_y_top")
                
                # Basic geometric constraints (left <= right, bottom <= top)
                # Note: sympy linsolve doesn't handle inequalities natively, 
                # we'll validate this post-solve.

        # Process Parameters (Width, Height)
        # Note: We need a mapping from parameter ID to what it represents.
        # But in Phase 1, parameters directly map to concepts like patch_width
        for param in self.ir.parameters:
            if param.parameter_type == "width":
                # Find which entity this belongs to (assuming entity ID is prefix)
                ent_id = param.id.split("_width")[0]
                if f"{ent_id}_x_right" in self.symbols:
                    xr = self.get_symbol(f"{ent_id}_x_right")
                    xl = self.get_symbol(f"{ent_id}_x_left")
                    self.equations.append(sp.Eq(xr - xl, param.value))
            elif param.parameter_type == "height":
                ent_id = param.id.split("_height")[0]
                if f"{ent_id}_y_top" in self.symbols:
                    yt = self.get_symbol(f"{ent_id}_y_top")
                    yb = self.get_symbol(f"{ent_id}_y_bottom")
                    self.equations.append(sp.Eq(yt - yb, param.value))
                    
        # Process Constraints
        for c in self.ir.constraints:
            if c.type == "CENTER_X":
                if len(c.objects) == 2:
                    obj1, obj2 = c.objects
                    cx1 = (self.get_symbol(f"{obj1}_x_left") + self.get_symbol(f"{obj1}_x_right")) / 2
                    cx2 = (self.get_symbol(f"{obj2}_x_left") + self.get_symbol(f"{obj2}_x_right")) / 2
                    self.equations.append(sp.Eq(cx1, cx2))
            elif c.type == "CENTER_Y":
                if len(c.objects) == 2:
                    obj1, obj2 = c.objects
                    cy1 = (self.get_symbol(f"{obj1}_y_bottom") + self.get_symbol(f"{obj1}_y_top")) / 2
                    cy2 = (self.get_symbol(f"{obj2}_y_bottom") + self.get_symbol(f"{obj2}_y_top")) / 2
                    self.equations.append(sp.Eq(cy1, cy2))
            elif c.type == "OFFSET_X":
                if len(c.objects) == 2:
                    obj1, obj2 = c.objects
                    val = c.parameters.get("value", 0.0)
                    cx1 = (self.get_symbol(f"{obj1}_x_left") + self.get_symbol(f"{obj1}_x_right")) / 2
                    cx2 = (self.get_symbol(f"{obj2}_x_left") + self.get_symbol(f"{obj2}_x_right")) / 2
                    self.equations.append(sp.Eq(cx1 - cx2, val))
            elif c.type == "OFFSET_Y":
                if len(c.objects) == 2:
                    obj1, obj2 = c.objects
                    val = c.parameters.get("value", 0.0)
                    cy1 = (self.get_symbol(f"{obj1}_y_bottom") + self.get_symbol(f"{obj1}_y_top")) / 2
                    cy2 = (self.get_symbol(f"{obj2}_y_bottom") + self.get_symbol(f"{obj2}_y_top")) / 2
                    self.equations.append(sp.Eq(cy1 - cy2, val))
                    
        # Apply Origin definition
        origin_type = self.ir.coordinate_system.origin_definition.get("type")
        if origin_type == "substrate_bottom_left" and "substrate_x_left" in self.symbols:
            self.equations.append(sp.Eq(self.get_symbol("substrate_x_left"), 0))
            self.equations.append(sp.Eq(self.get_symbol("substrate_y_bottom"), 0))

    def solve(self) -> ResolvedGeometry:
        self.build_system()
        
        sym_list = list(self.symbols.values())
        if not sym_list:
            # An empty system is NOT a solved system. Reporting SOLVED here would
            # let the pipeline emit an empty DXF while claiming success, which
            # violates the "no silent guessing / report what is missing" rule.
            self.diagnostics.append(Diagnostic(
                type="NO_GEOMETRY_EXTRACTED",
                severity="error",
                message=(
                    "No solvable geometry was extracted from the input. "
                    f"IR contained {len(self.ir.entities)} entities, "
                    f"{len(self.ir.parameters)} parameters, "
                    f"{len(self.ir.constraints)} constraints."
                )
            ))
            return ResolvedGeometry(
                status=SolveStatus.INVALID_INPUT,
                coordinate_system=self.ir.coordinate_system,
                diagnostics=self.diagnostics
            )

        if not self.equations:
            self.diagnostics.append(Diagnostic(
                type="UNDERDETERMINED_SYSTEM",
                severity="error",
                message="Entities were found but no dimensions or relationships constrain them."
            ))
            return ResolvedGeometry(
                status=SolveStatus.UNDERDETERMINED,
                coordinate_system=self.ir.coordinate_system,
                diagnostics=self.diagnostics
            )


        try:
            solution = sp.linsolve(self.equations, sym_list)
        except Exception as e:
            self.diagnostics.append(Diagnostic(type="SOLVER_ERROR", message=str(e)))
            return ResolvedGeometry(
                status=SolveStatus.NUMERICALLY_UNRESOLVED,
                coordinate_system=self.ir.coordinate_system,
                diagnostics=self.diagnostics
            )

        if len(solution) == 0:
            status = SolveStatus.INCONSISTENT
            self.diagnostics.append(Diagnostic(
                type="INCONSISTENT_SYSTEM",
                message="Equations cannot all be true simultaneously."
            ))
            return ResolvedGeometry(
                status=status,
                coordinate_system=self.ir.coordinate_system,
                diagnostics=self.diagnostics
            )
            
        # Linsolve returns a FiniteSet of tuples
        sol_tuple = list(solution)[0]
        
        # Check if the solution is underdetermined (contains free symbols)
        if any(isinstance(val, sp.Expr) and not val.is_number for val in sol_tuple):
            status = SolveStatus.UNDERDETERMINED
            self.diagnostics.append(Diagnostic(
                type="UNDERDETERMINED_SYSTEM",
                message="Insufficient constraints to uniquely determine geometry."
            ))
            return ResolvedGeometry(
                status=status,
                coordinate_system=self.ir.coordinate_system,
                diagnostics=self.diagnostics
            )
            
        status = SolveStatus.SOLVED
        
        # Map back to ResolvedEntities
        val_map = {sym.name: float(val) for sym, val in zip(sym_list, sol_tuple)}
        
        resolved_entities = []
        for ent in self.ir.entities:
            if ent.primitive == "rectangle":
                x_left = val_map.get(f"{ent.id}_x_left")
                x_right = val_map.get(f"{ent.id}_x_right")
                y_bottom = val_map.get(f"{ent.id}_y_bottom")
                y_top = val_map.get(f"{ent.id}_y_top")
                
                if None not in (x_left, x_right, y_bottom, y_top):
                    # Validation: check topological constraints
                    if x_right < x_left or y_top < y_bottom:
                        status = SolveStatus.INCONSISTENT
                        self.diagnostics.append(Diagnostic(
                            type="TOPOLOGICAL_ERROR",
                            message=f"Entity {ent.id} has inverted bounds.",
                            objects=[ent.id]
                        ))
                    
                    geo = ResolvedEntityGeometry(
                        bottom_left=[x_left, y_bottom],
                        bottom_right=[x_right, y_bottom],
                        top_right=[x_right, y_top],
                        top_left=[x_left, y_top]
                    )
                    resolved_entities.append(ResolvedEntity(id=ent.id, type=ent.primitive, geometry=geo))
                else:
                    resolved_entities.append(ResolvedEntity(id=ent.id, type=ent.primitive))

        return ResolvedGeometry(
            status=status,
            coordinate_system=self.ir.coordinate_system,
            entities=resolved_entities,
            diagnostics=self.diagnostics
        )
