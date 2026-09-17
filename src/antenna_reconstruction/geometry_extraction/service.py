from .ir.models import GeometryIR
from .ir.validator import validate_geometry_ir
from .ingestion.models import MockGeometryInput
from .extraction.extractor import RuleBasedExtractor

class GeometryUnderstandingService:
    def __init__(self, mode="mock"):
        self.mode = mode
        if self.mode == "mock":
            self.extractor = RuleBasedExtractor()
        else:
            raise NotImplementedError(f"Mode {self.mode} is not implemented yet.")

    def extract(self, input_data: MockGeometryInput) -> GeometryIR:
        """
        Extracts Geometry IR from the given input data and validates it.
        """
        # Phase 1: Extraction
        ir = self.extractor.extract(input_data)
        
        # Phase 2: Validation
        ir = validate_geometry_ir(ir)
        
        return ir
