import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from antenna_reconstruction.geometry_extraction.ingestion.pdf import extract_pdf
from antenna_reconstruction.visual_completion import pipeline as visual_completion
from antenna_reconstruction.visual_completion.vlm.client import analyze_figure
from antenna_reconstruction.visual_completion.vlm.parser import parse_vlm_response
from antenna_reconstruction.templates import get_template, rank_templates
from antenna_reconstruction.cad_builder.builder import GeometryBuilder
from antenna_reconstruction.cad_builder.exporters.dxf import DXFExporter

def main():
    load_dotenv()
    
    pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "papers", "hexagonal_ring_antenna.pdf"))
    figure_path = pdf_path.replace(".pdf", ".png")
    
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "diagnostic_pipeline", "outputs"))
    os.makedirs(out_dir, exist_ok=True)
    
    def save_json(name, data):
        with open(os.path.join(out_dir, name), "w") as f:
            json.dump(data, f, indent=2)

    # 1. PDF Extraction
    doc = extract_pdf(pdf_path)
    extracted_params = doc.merged_parameters()
    save_json("01_pdf_extraction.json", extracted_params)
    
    # 2. Raw VLM Output (Checkpoint 2)
    raw_vlm_response = analyze_figure(figure_path, extracted_params)
    vlm_parsed = parse_vlm_response(raw_vlm_response) if raw_vlm_response else None
    
    save_json("02_visual_analysis.json", {
        "raw_response": raw_vlm_response,
        "parsed_json": vlm_parsed.model_dump() if vlm_parsed else None
    })
    
    # 3. Visual Completion (Checkpoint 3)
    completion = visual_completion.complete(figure_path=figure_path, parameters=extracted_params)
    save_json("03_visual_completion.json", completion.model_dump())
    
    # 4. Final Parameters (Checkpoint 4)
    final_params = completion.enriched_parameters
    save_json("04_parameter_merge.json", {"original": extracted_params, "final": final_params})
    save_json("05_final_parameters.json", final_params)
    
    # Template Matching
    ranked = rank_templates(final_params)
    best_name, coverage, missing = ranked[0]
    save_json("06_template_matching.json", {
        "ranked": [{"name": n, "coverage": c, "missing": m} for n, c, m in ranked],
        "selected": best_name
    })
    
    template = get_template(best_name)
    built = template.build(final_params)
    
    # 5. Verification (Checkpoint 5)
    ver_report = built.verification
    if ver_report:
        save_json("07_verification.json", {
            "results": [
                {
                    "name": r.name,
                    "target": r.target,
                    "description": r.description,
                    "outcome": r.outcome.value,
                    "predicted": r.predicted,
                    "stated": r.stated,
                    "error": r.error,
                    "tolerance": r.tolerance,
                    "missing": r.missing
                } for r in ver_report.results
            ],
            "ok": ver_report.ok,
            "confirmed_count": len(ver_report.confirmed),
            "refuted_count": len(ver_report.refuted),
            "skipped_count": len(ver_report.skipped)
        })
    else:
        save_json("07_verification.json", {"results": [], "ok": False})
        
    # 6. Template Geometry (Checkpoint 6)
    def serialize_shape(s):
        return {
            "id": s.id,
            "layer": s.layer.value,
            "rings": s.rings,
            "ring_roles": s.ring_roles,
            "z": s.z,
            "thickness": s.thickness,
            "derivation": s.derivation
        }
    
    save_json("08_template_geometry.json", {
        "shapes": [serialize_shape(s) for s in built.shapes],
        "underdetermined": built.underdetermined,
        "assumptions": built.assumptions,
        "diagnostics": built.diagnostics
    })
    
    # 7. CAD Model (Checkpoint 7)
    builder = GeometryBuilder()
    build_result = builder.build_from_template(built)
    
    save_json("09_geometry_diagnostics.json", {
        "status": build_result.status.value,
        "diagnostics": build_result.diagnostics
    })
    
    save_json("10_cad_model.json", build_result.model.model_dump() if build_result.model else None)
    
    # 8. DXF Export (Checkpoint 8)
    exporter = DXFExporter()
    dxf_out = os.path.join(out_dir, "output.dxf")
    if build_result.model:
        metadata = {
            "source": doc.source_id,
            "template": template.name,
            "verified": ver_report.ok if ver_report else False,
            "assumptions": built.assumptions,
            "underdetermined": built.underdetermined,
            "derivations": built.diagnostics 
        }
        exporter.export(build_result.model, dxf_out, metadata=metadata)
        
    dxf_lines = []
    if os.path.exists(dxf_out):
        with open(dxf_out, "r") as f:
            dxf_lines = f.readlines()
    
    dxf_inventory = {
        "path": dxf_out,
        "entities": {}
    }
    for i, line in enumerate(dxf_lines):
        line = line.strip()
        if line in ["POLYLINE", "LWPOLYLINE", "HATCH", "LINE", "CIRCLE", "ARC"]:
            dxf_inventory["entities"][line] = dxf_inventory["entities"].get(line, 0) + 1
            
    save_json("11_dxf_inventory.json", dxf_inventory)
    
    # Final summary
    summary_lines = [
        "# Diagnostic Run Summary",
        "",
        "## Pipeline Execution",
        f"Stage 1 (PDF Extraction) -> SUCCESS",
        f"Stage 2 (Visual Completion) -> {completion.vlm_status} / {completion.constructor_status}",
        f"Stage 3 (Template Matching) -> Match: {best_name} (Coverage: {coverage:.2f})",
        f"Stage 4 (Verification) -> {'SUCCESS' if ver_report and ver_report.ok else 'FAIL'}",
        f"Stage 5 (Geometry Build) -> {build_result.status.value}",
        "",
        "## Parameters",
        "```json",
        json.dumps(final_params, indent=2),
        "```",
        "",
        "## VLM Findings",
        "```json",
        json.dumps([d.model_dump() for d in completion.derivations], indent=2),
        "```",
        "",
        "## Verification"
    ]
    
    if ver_report:
        for r in ver_report.results:
            summary_lines.append(f"- {r.name}: {r.outcome.value} (predicted={r.predicted}, stated={r.stated})")
    
    summary_lines.extend([
        "",
        "## Problems Observed",
        "```json",
        json.dumps(built.diagnostics + build_result.diagnostics, indent=2),
        "```"
    ])
    
    with open(os.path.join(out_dir, "12_final_summary.md"), "w") as f:
        f.write("\n".join(summary_lines))

if __name__ == "__main__":
    main()
