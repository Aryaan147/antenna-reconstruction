"""Template-driven reconstruction: PDF -> parameter table -> verified template -> DXF.

This is the path that works on real papers. It differs from the sentence-level
pipeline in `pipeline.py` in one decisive way: a binding is verified against the
paper's own redundant numbers before any geometry is built, so a wrong
interpretation fails loudly instead of producing a plausible wrong antenna.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from .binding.verifier import VerificationReport
from .cad_builder.builder import GeometryBuilder
from .cad_builder.exporters.dxf import DXFExporter
from .cad_builder.models import BuildStatus
from .geometry_extraction.ingestion.pdf import extract_pdf
from .templates import TemplateResult, get_template, rank_templates


class ReconstructionResult(BaseModel):
    source_id: str
    success: bool
    # A build that no relation could test is UNVERIFIED, which is distinct from
    # verified-correct. Callers must not read success as "the binding is right".
    verified: bool = False
    template: Optional[str] = None
    output_path: Optional[str] = None
    parameters: Dict[str, float] = Field(default_factory=dict)
    verification: Optional[VerificationReport] = None
    underdetermined: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    # Values computed from stated facts rather than printed by the paper.
    derivations: List[str] = Field(default_factory=list)
    diagnostics: List[str] = Field(default_factory=list)

    def render(self) -> str:
        lines = [f"=== {self.source_id} ==="]
        lines.append(f"template   : {self.template or '(none matched)'}")
        lines.append(f"parameters : {len(self.parameters)} symbols")
        if self.verification is not None:
            lines.append("verification:")
            lines.extend("  " + ln for ln in self.verification.render().split("\n"))
        if self.derivations:
            lines.append("derived (computed, not printed by the paper):")
            lines.extend(f"  - {d}" for d in self.derivations)
        if self.assumptions:
            lines.append("assumptions:")
            lines.extend(f"  - {a}" for a in self.assumptions)
        if self.underdetermined:
            lines.append("underdetermined (omitted, not guessed):")
            lines.extend(f"  - {u}" for u in self.underdetermined)
        if self.diagnostics:
            lines.append("diagnostics:")
            lines.extend(f"  - {d}" for d in self.diagnostics)
        if self.success and not self.verified:
            lines.append(
                "WARNING    : binding is UNVERIFIED - this family carries no "
                "redundant symbols to test it against."
            )
        lines.append(
            f"result     : {'OK -> ' + str(self.output_path) if self.success else 'FAILED'}"
        )
        return "\n".join(lines)


class TemplatePipeline:
    def __init__(self) -> None:
        self.builder = GeometryBuilder()
        self.exporter = DXFExporter()

    def run_from_pdf(self, pdf_path: str, output_path: str,
                     template_name: Optional[str] = None) -> ReconstructionResult:
        doc = extract_pdf(pdf_path)
        result = self.run_from_parameters(
            doc.merged_parameters(), output_path,
            source_id=doc.source_id, template_name=template_name,
        )
        # Ambiguities found while reading the paper matter even when the build
        # succeeds, so they are carried through rather than discarded.
        result.diagnostics.extend(doc.diagnostics())
        result.derivations.extend(doc.derivations())
        result.assumptions.extend(doc.physics_assumptions())
        return result

    def run_from_parameters(self, values: Dict[str, float], output_path: str,
                            source_id: str = "parameters",
                            template_name: Optional[str] = None
                            ) -> ReconstructionResult:
        result = ReconstructionResult(
            source_id=source_id, success=False, parameters=dict(values)
        )

        if not values:
            result.diagnostics.append(
                "No parameters were extracted; nothing can be reconstructed."
            )
            return result

        if template_name is None:
            ranked = rank_templates(values)
            best_name, coverage, missing = ranked[0]
            if coverage < 1.0:
                result.diagnostics.append(
                    f"No template is fully satisfied. Best match {best_name!r} "
                    f"({coverage:.0%} of required symbols); missing: "
                    f"{', '.join(missing)}."
                )
                return result
            template_name = best_name

        template = get_template(template_name)
        result.template = template.name

        built: TemplateResult = template.build(values)
        result.verification = built.verification
        result.underdetermined = list(built.underdetermined)
        result.assumptions = list(built.assumptions)
        result.diagnostics.extend(built.diagnostics)

        if built.verification is not None and built.verification.refuted:
            result.diagnostics.append(
                "Symbol binding was REFUTED by the paper's own numbers; "
                "refusing to build geometry from an interpretation known to be wrong."
            )
            return result

        build_result = self.builder.build_from_template(built)
        result.diagnostics.extend(build_result.diagnostics)
        if build_result.status is not BuildStatus.BUILT:
            result.diagnostics.append(f"CAD build failed: {build_result.status.value}")
            return result

        if not self.exporter.export(build_result.model, output_path):
            result.diagnostics.append("DXF export failed.")
            return result

        result.success = True
        result.verified = bool(
            built.verification is not None and built.verification.ok
        )
        result.output_path = output_path
        return result
