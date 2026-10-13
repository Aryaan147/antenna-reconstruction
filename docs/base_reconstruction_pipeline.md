# Base Antenna Reconstruction Pipeline

## 1. Executive Summary

This document describes the existing text-driven base antenna reconstruction pipeline. The current system extracts physical dimensions and symbols from research paper text and tables, matches them to a predefined parametric antenna template, resolves the geometry coordinates, verifies the bindings using redundant parameters, and finally generates a 2D DXF CAD model. 

Crucially, this system operates strictly on text. It does not look at figures, meaning any information conveyed exclusively through visual diagrams is lost to the current pipeline. Understanding this pipeline is the prerequisite for designing a visual-evidence reconciliation system.

## 2. Repository Structure

The relevant source files for the reconstruction pipeline are located in `src/antenna_reconstruction/`.

*   **CLI / Entry Points**: `src/antenna_reconstruction/cli.py`, `src/antenna_reconstruction/template_pipeline.py`
*   **Extraction Modules**: `src/antenna_reconstruction/geometry_extraction/ingestion/` (`pdf.py`, `prose.py`, `word_tables.py`)
*   **Template Modules**: `src/antenna_reconstruction/templates/` (`base.py`, `rectangular_patch.py`, `__init__.py`, etc.)
*   **Binding & Verification**: `src/antenna_reconstruction/binding/verifier.py`
*   **Geometry / CAD Modules**: `src/antenna_reconstruction/cad_builder/` (`builder.py`), `src/antenna_reconstruction/geometry/`
*   **DXF Generation Modules**: `src/antenna_reconstruction/cad_builder/exporters/dxf.py`
*   **Tests**: `tests/` (`test_template_pipeline.py`, `test_binding_verifier.py`, `test_pdf_ingestion.py`, etc.)

## 3. End-to-End Pipeline

The end-to-end flow from a research paper to a DXF file is as follows:

```text
Research Paper (PDF)
      ↓
Text/Table Extraction (pdfplumber, regex heuristics)
      ↓
Structured Antenna Data (Dict[str, float] of symbol -> value)
      ↓
Template Selection (rank_templates based on symbol coverage)
      ↓
Parameter Processing & Verification (Template.build() + verify())
      ↓
Geometry Construction (GeometryBuilder -> CADModel)
      ↓
DXF (DXFExporter)
```

## 4. Pipeline Entry Point

The true entry point is `cli.py`, which delegates execution to `TemplatePipeline` in `template_pipeline.py`. 

The execution path is:
1.  `cli.py::main()` parses arguments.
2.  Instantiates `pipeline = TemplatePipeline()`.
3.  Calls `pipeline.run_from_pdf(...)` (or `run_from_parameters(...)` if JSON is provided directly).
4.  Inside `run_from_pdf`, `extract_pdf(...)` returns a `PdfDocument` object, which exposes `merged_parameters()` to yield a flat dictionary.
5.  `run_from_parameters` takes this dictionary and runs:
    *   `rank_templates(values)`
    *   `get_template(best_name).build(values)`
    *   `builder.build_from_template(built)`
    *   `exporter.export(...)`

## 5. Input Data

The base reconstruction pipeline logic operates on a flat dictionary of `symbol -> value` pairings.

**Input format:**
```python
{
    "W": 40.0,
    "L": 30.0,
    "SW": 50.0,
    "SL": 50.0,
    "FI": 5.0
}
```

*   **Parameter names**: Strings (normalized, e.g., "S1", "W").
*   **Parameter types**: Floats (units are implicitly assumed or converted to a standard unit during extraction, normally `mm`).
*   **Required/Optional**: Governed by the chosen template.
*   **Categorical values**: Not supported in this flat numerical dictionary.
*   **Missing parameters**: Simply omitted from the dictionary.

This dictionary originates from the text extraction phase (or a provided JSON file via the `-p` CLI flag).

## 6. Text/Table Extraction

Data is extracted using `pdfplumber` in `geometry_extraction/ingestion/pdf.py`.

*   **Tables**: The code searches for explicit parameter tables using cell grids. It identifies geometry tables by looking for length unit headers (e.g., `(mm)`). It matches a symbol column with a value column. 
*   **Prose**: Extracts parameters directly from sentences using regex (e.g., "patch width W is 40 mm").
*   **Physics/Equations**: Extracts known antenna physics parameters.
*   **Normalization**: Symbol names are normalized (`S_1` -> `S1`, `F W` -> `FW`).
*   **Conflict Resolution**: Tables outrank Prose, which outranks Physics equations. Within a table, the first occurrence wins.
*   **Limitations**: The extractor does **not** understand antenna topology, nor does it capture geometry relationships explicitly. It simply finds symbols and numbers.

## 7. Structured Data Model

Before reconstruction begins, the rich document is flattened into a dictionary.

While `extract_pdf` produces a `PdfDocument` containing `ParameterTable`s (which have `provenance` metadata like page and row number), the reconstruction pipeline solely consumes the output of `doc.merged_parameters()`:

```python
Dict[str, float]
```

At this boundary, **all structural, visual, and relational context from the paper is lost**. The pipeline only knows that `W = 40.0`, not where `W` was located or what `W` points to in a figure.

## 8. Template Selection

Template selection occurs in `rank_templates()` within `templates/__init__.py`.

1.  Each template declares a `required` list of symbols.
2.  The engine checks which required symbols are missing from the input dictionary.
3.  Templates are scored by **coverage** (`present_required / total_required`).
4.  If multiple templates have the same coverage (e.g., 100%), they are tie-broken by the **total number of required symbols**. This ensures a more specific template (e.g., one requiring 6 symbols) beats a generic one (e.g., one requiring 2 symbols).
5.  If the top template has `< 1.0` (100%) coverage, the pipeline halts with a diagnostic error: `No template is fully satisfied`.

## 9. Template Input Contracts

A template acts as a parametric contract. For example, `RectangularPatchTemplate`:

```text
Template: rectangular_patch
Supported antenna: Rectangular microstrip patch on a rectangular substrate.
Required parameters: ["W", "L"] (Patch dimensions)
Optional parameters: ["SW", "SL", "FW", "FI", "FG", "FL"] (Substrate and feed dimensions)
Output: TemplateResult containing a list of `Shape` objects (Layer, Rings).
```

A template explicitly maps these generic symbols to geometric primitives. If an optional feature's required sub-parameters are incomplete (e.g., `FI` is present but `FW` is missing), the template logs an `underdetermined` warning and skips drawing that specific sub-feature (e.g., the inset feed).

## 10. Parameter Processing

Inside `Template.build(values)`, numerical parameters are translated into geometry. 

1.  **Verification (`verifier.py`)**: Before building, templates define `Relation`s to test the binding. For example, if a paper provides patch length (`L`), substrate length (`SL`), inset depth (`FI`), and feed length (`FL`), the template checks if `FL = (SL - L)/2 + FI`. If the math contradicts the provided numbers beyond a floating-point tolerance, the binding is `REFUTED` and construction halts.
2.  **Derived Parameters**: The template computes offsets. For a rectangular patch, if the substrate (`SW`, `SL`) is provided, it centers the patch by deriving `x0 = (SW - W) / 2.0`. 
3.  **Validation**: `GeometryError` is caught and logged to `diagnostics`.

## 11. Geometry Construction

The parameter processing outputs `Shape` objects containing coordinate rings. 
The `GeometryBuilder.build_from_template()` in `cad_builder/builder.py` takes these `Shape` objects and constructs a `CADModel` containing `PolygonShape`s.

```text
parameters -> calculated origins (x0, y0) -> primitive generation (e.g., rectangle(), apply_inset()) -> Shape (list of rings) -> PolygonShape in CADModel
```

## 12. DXF Generation

The `DXFExporter` in `cad_builder/exporters/dxf.py` converts the `CADModel` to a DXF file.

*   **Library**: `ezdxf`.
*   **Layers**: Maps logical layers to colors (e.g., SUBSTRATE -> 8, RADIATOR -> 2, GROUND -> 3).
*   **Entities**: Each shape is written as both an `LWPOLYLINE` (for boundaries) and a `HATCH`.
*   **Holes/Slots**: The `HATCH` entity supports an `EXTERNAL` boundary path and multiple `OUTERMOST` paths (holes). This ensures slots are treated as voids in the metal, rather than standalone pieces of metal, which is critical for EM solvers.
*   **Metadata**: Adds custom XDATA variables containing the template used, derivations, and assumptions for auditability.

## 13. Defaults and Fallbacks

A core philosophy of this pipeline is: **Templates never invent a missing number.**

However, there are structural defaults:
*   **Substrate positioning**: If `SW` and `SL` are missing, the patch is anchored at the origin `(0.0, 0.0)` instead of centered on a substrate.
*   **Ground Plane**: An implied full-sheet ground plane on the reverse side is intentionally omitted because it is rarely explicitly dimensioned in the text.
*   **Feed Line**: If the feed width `FW` is missing, the feed line is simply not drawn. If `FI` is missing, the feed is drawn exactly to the patch edge.

These defaults are always logged in the `underdetermined` or `assumptions` arrays rather than happening silently.

## 14. Failure Handling

*   **Missing Required Parameter**: `TemplatePipeline` halts during ranking. DXF is not generated.
*   **Malformed Parameter**: Excluded during text extraction.
*   **Contradictory Parameters (Same Symbol)**: First occurrence in extraction wins.
*   **Contradictory Parameters (Physics/Redundancy)**: Caught by `verifier.py`. Status becomes `REFUTED`. DXF is not generated.
*   **Feature mentioned but dimensions missing**: Template continues building the rest of the antenna, but appends a note to the `underdetermined` list and skips the incomplete feature.
*   **Geometry Generation Fails**: Generates a diagnostic error and halts.

## 15. Diagnostics

The pipeline yields a `ReconstructionResult` with rich diagnostics:
*   `diagnostics`: Errors and general pipeline warnings.
*   `underdetermined`: Features that were skipped or defaulted because parameters were missing.
*   `assumptions`: Standard assumptions made by the template (e.g., "patch is centered").
*   `derivations`: Values computed via physics rather than extracted from text.
*   `verification`: The report from `verifier.py` (Confirmed, Refuted, Skipped).

## 16. Existing Tests

The `tests/` directory contains comprehensive unit and integration tests:
*   `test_template_pipeline.py`: Tests the end-to-end `TemplatePipeline` mock flows.
*   `test_binding_verifier.py`: Tests the arithmetic verification logic and tolerances.
*   `test_pdf_ingestion.py` & `test_word_tables.py`: Tests table parsing and extraction from dummy PDFs.
*   `test_dxf_export.py`: Tests `ezdxf` entity generation, hatch logic, and hole punching.
*   `test_templates.py`: Tests individual templates (e.g., Rectangular, Hexagonal) with various parameter combinations.

## 17. Complete Example Trace

**Input Data:**
```python
{
    "W": 30.0, "L": 40.0, "SW": 50.0, "SL": 60.0, "FW": 3.0
}
```
**Trace:**
1.  **Template Selected**: `RectangularPatchTemplate` (100% required coverage).
2.  **Verification**: No redundant parameter (like `FL`) is provided, so it remains UNVERIFIED (0 confirmed, 0 refuted).
3.  **Processing**: 
    *   Substrate is built: `50x60` at `0,0`.
    *   Patch offset calculated: `x0 = 10, y0 = 10`. Patch is built at `10, 10` to `40, 50`.
    *   Feed line is built from `y=0` to `y=10` with width `3.0`.
4.  **Geometry**: `Shape(substrate)`, `Shape(patch)`, `Shape(feed)`.
5.  **DXF**: Output to `antenna.dxf` with Polylines and Hatches on layers `SUBSTRATE`, `RADIATOR`, and `FEED`.
6.  **Diagnostics**: Appends an assumption that the patch is centered, and an underdetermined warning that the ground plane is omitted.

## 18. Information Available vs Missing

**Information the text extractor captures:**
*   Symbol-to-value mappings located in structured tables.
*   Values explicitly stated in prose (e.g., "W = 40 mm").
*   Basic frequency/dielectric parameters via physics extraction.

**Information the text extractor misses:**
*   Parameters defined solely as annotations in a figure.
*   Geometric relationships (e.g., "W is the width of the inner slot" vs "W is the patch width").
*   Topological features (e.g., "there is a circular cutout here") if they lack named dimensions in the text.

## 19. Information Lost by Text-Only Processing

The text-only pipeline is completely blind to:
1.  **Topology identification**: It relies entirely on pre-defined templates. If a paper designs a novel fractal antenna, the pipeline has no template to match it and will fail.
2.  **Visual Symbol Grounding**: It cannot verify if the extracted symbol `W` actually corresponds to the patch width in the diagram, it blindly assumes the template's definition of `W`.
3.  **Unmentioned Features**: Any chamfer, notch, or slot shown in a figure but not dimensioned in text is permanently lost.

## 20. Current Pipeline Limitations

1.  It is fundamentally restricted to a small vocabulary of predefined templates.
2.  It fails loudly if a required parameter is missing from the text (which happens frequently if the paper only annotates it on a figure).
3.  It resolves ambiguities arbitrarily (if a text has two `L` values, it picks the first one it parses).

## 21. Potential Extension Point for Visual Evidence

The ideal insertion point for a visual-analysis (VLM) component is **immediately after Text Extraction and before Template Selection/Processing**, specifically intercepting the process in `template_pipeline.py`.

```text
Current stage:
Input: PDF File -> Text Extractor
Output: Dict[str, float] (Incomplete)

--- PROPOSED VISUAL COMPONENT INSERTION ---
Input: PDF Figures + Incomplete Dict[str, float] + Template Definitions
Task: VLM analyzes figures to (1) identify the correct topology/template, (2) extract missing parameters directly from the image, and (3) verify that text-extracted symbols match their visual representations.
Output: Augmented Dict[str, float] + Forced Template Name
-------------------------------------------

Next stage:
Input: Augmented Dict[str, float] + Forced Template Name
Output: Geometry Builder -> DXF
```

This location is optimal because it allows the visual system to satisfy the rigid constraints of the existing `Template.build()` contract without having to rewrite the complex, downstream geometry calculation and DXF generation code.

## 22. Important Files and Functions Reference

*   `src/antenna_reconstruction/cli.py` - Standard CLI entry point.
*   `src/antenna_reconstruction/template_pipeline.py` - Orchestrates the flow (`TemplatePipeline`).
*   `src/antenna_reconstruction/templates/base.py` - `Template` and `Shape` base classes.
*   `src/antenna_reconstruction/templates/__init__.py` - `rank_templates()` scoring logic.
*   `src/antenna_reconstruction/binding/verifier.py` - `verify()` mathematical redundancy checker.
*   `src/antenna_reconstruction/cad_builder/exporters/dxf.py` - `DXFExporter.export()` with hatching logic.
*   `src/antenna_reconstruction/geometry_extraction/ingestion/pdf.py` - `extract_pdf()` and `merged_parameters()`.
