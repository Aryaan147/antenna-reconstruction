# Base Pipeline & Parameter Engine Analysis

This document traces the existing base pipeline of the antenna reconstruction system to identify the components currently handling parameter extraction, calculation, inference, and geometric derivation. This analysis serves as the foundation for designing the new Parameter Engine.

## 1. Base Pipeline Overview

The pipeline from input (PDF/Image) to the final DXF output follows this flow:

1. **Input**: A PDF file and an optional Figure image. (e.g., in `main.py`).
2. **Extraction**:
   - **Module**: `src/antenna_reconstruction/geometry_extraction/ingestion/pdf.py`
   - **Function**: `extract_pdf(pdf_path)` -> `PdfDocument`
   - **Action**: Extracts text, raw tables, parameter tables, prose, and physics assumptions. Merges them into a raw parameter dictionary via `doc.merged_parameters()`.
3. **Parameter Processing & Visual Completion**:
   - **Module**: `src/antenna_reconstruction/visual_completion/pipeline.py`
   - **Function**: `complete(figure_path, parameters)`
   - **Action**: Sends the image and extracted parameters to a VLM (`analyze_figure`).
4. **Parameter Calculation/Inference**:
   - **Module**: `src/antenna_reconstruction/visual_completion/geometry/constructor.py`
   - **Function**: `construct_geometry(request)`
   - **Action**: Runs mathematical and proportional rules (from `rules.py`) to derive missing parameters (e.g., `FI`, `FG`, `tapered_base`).
5. **Geometry Construction (Template Matching & Validation)**:
   - **Module**: `src/antenna_reconstruction/template_pipeline.py` & `src/antenna_reconstruction/templates/`
   - **Class/Method**: `TemplatePipeline.run_from_parameters(...)` -> `Template.build(values)`
   - **Action**: Ranks templates, binds parameters, validates redundancy relations (via `verify`), handles defaults, and transforms dimensions into absolute 2D coordinate shapes.
6. **CAD Generation**:
   - **Module**: `src/antenna_reconstruction/cad_builder/builder.py`
   - **Class/Method**: `GeometryBuilder.build_from_template(built)`
   - **Action**: Translates 2D planar rings into CAD entities.
7. **DXF Export**:
   - **Module**: `src/antenna_reconstruction/cad_builder/exporters/dxf.py`
   - **Class/Method**: `DXFExporter.export(...)`

## 2. Parameter Generation / Calculation Components

### A. Physics Derivation Engine
- **File path**: `src/antenna_reconstruction/derived/physics.py`
- **Functions**: `extract_physics(text)`, `_derive(out)`
- **Purpose**: Infers implied quantities from stated facts (e.g., wavelength from frequency, patch spacing from wavelength).
- **Inputs**: Raw text extracted from the PDF.
- **Outputs**: `PhysicsExtraction` containing `DerivedQuantity` objects.
- **How it works internally**: Uses RegEx to find frequencies, dielectric constants, and phrases like "lambda/2". It calculates new parameter values (e.g., `LAMBDA0 = c / f`). It *calculates and infers* rather than transforming.

### B. Visual Geometry Constructor
- **File path**: `src/antenna_reconstruction/visual_completion/geometry/constructor.py` & `rules.py`
- **Functions**: `construct_geometry(request)`, `construct_inset_feed(...)`, `derive_parameter_from_estimation(...)`
- **Purpose**: Applies deterministic mathematical rules to derive missing parameters based on VLM analysis.
- **Inputs**: Missing items from VLM, explicit visible dimensions, proportional estimations, and the current parameter dictionary.
- **Outputs**: `GeometryCompletionResult` containing `resolved_parameters` and `derivations`.
- **How it works internally**: Matches feature names (e.g., "gap", "slot") to rules. It parses estimations like `{"relative_to": "FW", "ratio": 0.5}` and derives the missing parameter by multiplying `FW * 0.5`. It *calculates and infers*.

### C. Antenna Templates
- **File path**: `src/antenna_reconstruction/templates/base.py` & specific templates (e.g., `rectangular_patch.py`)
- **Class/Method**: `Template.build(values)`, `RectangularPatchTemplate.build(values)`
- **Purpose**: Validates relationships and converts scalar parameter dimensions into absolute XY geometry primitives (e.g., rectangles, microstrip lines).
- **Inputs**: A dictionary of parameter values (e.g., `{"W": 40.0, "L": 30.0, "SW": 60.0}`).
- **Outputs**: `TemplateResult` containing a list of `Shape` objects and diagnostics.
- **How it works internally**: Performs centering arithmetic (e.g., `x0 = (SW - W) / 2.0`). It conditionally executes geometry building if dependencies are met. It *validates and transforms*.

### D. Binding Verifier
- **File path**: `src/antenna_reconstruction/binding/verifier.py` (Referenced in templates)
- **Purpose**: Validates mathematical relationships stated in the template (e.g., `FL = (SL - L)/2 + FI`).
- **Inputs**: Parameter dictionary and a list of `Relation` models.
- **Outputs**: `VerificationReport`
- **How it works internally**: Compares the expected derived value of a redundant parameter against the value actually provided in the paper. It *validates*.

> **Which existing component is currently closest to what we are calling the "Parameter Engine"?**
> The closest existing components acting as a "Parameter Engine" are **`src/antenna_reconstruction/visual_completion/geometry/constructor.py`** (along with `rules.py`) and **`src/antenna_reconstruction/derived/physics.py`**. They are actively taking known parameters and estimations to calculate, infer, and derive new parameter values.

## 3. Parameter Data Flow

Example tracking the parameter `W` (Patch Width) and `FI` (Inset Depth):

1. **Appearance**: `W` appears in a table in the PDF.
2. **Extraction**: `geometry_extraction/ingestion/pdf.py` parses the table and stores `{"W": 40.0}` in a `ParameterTable` object.
3. **Merging**: `doc.merged_parameters()` yields a flat dictionary: `{"W": 40.0, ...}`.
4. **VLM Interception**: The `complete()` pipeline passes the dictionary to the VLM. The VLM notices `FI` is missing.
5. **Constructor Derivation**: `constructor.py` is invoked to resolve `FI`. `rules.py` derives `FI` from a proportional estimation (if applicable) and adds it to `resolved_parameters["FI"]`.
6. **Enrichment**: The pipeline merges derived parameters with the original ones, creating `enriched_parameters`.
7. **Template Matching**: `template_pipeline.py` sends the dictionary to `rank_templates`, which sees that `W` is present and satisfies `RectangularPatchTemplate`'s `required` list.
8. **Transformation**: `RectangularPatchTemplate.build(values)` extracts `W = values["W"]` and `FI = values.get("FI")`.
9. **Coordinate Generation**: The template calculates origin offsets: `x0 = (SW - W) / 2.0`. It creates the patch: `patch_ring = rectangle(x0, y0, x0 + W, y0 + L)`. If `FI` is present, it modifies the `patch_ring` using `apply_inset(..., FI)`.
10. **Final Geometry**: The parameters affect the `Shape(..., rings=[...])`, which is then passed to the CAD builder to draw lines.

## 4. Missing Parameter Handling

The current base pipeline explicitly handles missing parameters across different stages. **It never invents a missing number.**

- **Derived from Physics (`physics.py`)**: If inputs (like frequency) are missing or contradictory, the dependent variable (like wavelength) is simply **not derived**.
- **Visual Constructor Estimation (`constructor.py`)**: If the VLM flags a missing parameter (e.g., `FI`), the constructor attempts to calculate it using known rules (e.g., explicit dimension from figure, or proportional ratio against another parameter like `FW`). If it cannot resolve it, it appends the feature to `result.unresolved`.
- **Template Rejection (`base.py`)**: If a parameter in the `required` list of a template is missing, the template **fails** (`coverage < 1.0`). `missing_required()` flags it, and `TemplatePipeline` logs a diagnostic and halts CAD generation.
- **Conditional Omission (`rectangular_patch.py`)**: If an `optional` parameter is missing, the template uses logical branching to omit the dependent geometry.
  - *Example*: `has_substrate = "SW" in values and "SL" in values`. If `False`, it centers the patch at `(0.0, 0.0)` and appends to `underdetermined`: `"substrate: no substrate width/length symbols were found..."`
  - *Example*: `feed_width = values.get("FW")`. If `None`, it appends to `underdetermined` and **does not build the feed**.

## 5. Existing Mathematical / Geometric Logic

Here is the existing logic used to determine relationships, derive dimensions, or establish coordinates:

### Wavelength Calculation
- **Input**: `f_GHz` (Centre Frequency)
- **Algorithm**: `c / (f_GHz * 1e9)` (where c = 299,792,458 * 1000 mm/s)
- **Output**: `LAMBDA0`
- **Where output is used**: Exported as a derived parameter, occasionally used as a substitute in relations.

### Guided Wavelength (Lower Bound)
- **Input**: `LAMBDA0`, `eps_r` (Dielectric Constant)
- **Algorithm**: `LAMBDA0 / sqrt(eps_r)`
- **Output**: `LAMBDA_G_MIN`
- **Where output is used**: Exported as an assumption; not used directly as a dimension.

### Array Patch Spacing
- **Input**: `LAMBDA0`, `spacing_divisor` (e.g., 2 for "lambda/2")
- **Algorithm**: `LAMBDA0 / spacing_divisor`
- **Output**: `DX`, `DY`
- **Where output is used**: Exported as derived parameters for patch array spacing.

### Proportional Parameter Derivation
- **Input**: A known parameter (e.g., `FW = 2.0`), a ratio (`ratio = 0.5`), and the target relative string (`relative_to = "FW"`).
- **Algorithm**: `val = parameters[relative_to] * ratio`
- **Output**: Missing parameter value (e.g., `FG = 1.0`).
- **Where output is used**: Injected back into the main parameter dictionary in `visual_completion/pipeline.py`.

### Rectangular Patch Coordinate Centering
- **Input**: `SW` (Substrate Width), `W` (Patch Width), `SL` (Substrate Length), `L` (Patch Length)
- **Algorithm**: `x0 = (SW - W) / 2.0` and `y0 = (SL - L) / 2.0`
- **Output**: `x0`, `y0` coordinates.
- **Where output is used**: Anchoring the bottom-left corner of the patch geometry on the substrate.

### Inset Feed Length Relationship
- **Input**: `SL` (Substrate Length), `L` (Patch Length), `FI` (Inset depth)
- **Algorithm**: `FL = (SL - L)/2 + FI`
- **Output**: The expected total feed line length.
- **Where output is used**: In the `Verifier` as a `Relation` to ensure the dimensions provided by the paper are consistent.
