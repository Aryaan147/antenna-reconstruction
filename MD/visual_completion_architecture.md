# Visual Completion Extension for the Base Antenna Reconstruction Pipeline

## 0. Purpose

Implement a **small visual-completion layer** on top of the existing
antenna reconstruction pipeline.

The existing pipeline is already implemented and must remain the main
reconstruction system.

The new layer has exactly two new responsibilities:

1.  **Multimodal LLM / VLM**
    -   Compare the supplied antenna figure against the structure
        produced by the existing text/table extractor.
    -   Identify information visible in the figure that is missing from
        the extracted structure.
    -   Describe the missing information briefly and precisely.
    -   Do not generate guessed dimensions or coordinates.
2.  **Mathematical Geometry Constructor**
    -   Take the extracted structure plus the VLM's missing-information
        description.
    -   Determine whether the missing dimensions/geometry can be derived
        from the available information and explicit geometric rules.
    -   If determinable, calculate the missing values/geometry.
    -   If not determinable, return `UNKNOWN` rather than inventing
        values.
    -   Add successfully resolved information to the structure consumed
        by the existing reconstruction pipeline.

After these two components, the **existing reconstruction pipeline
continues unchanged**.

The target architecture is:

``` text
Research Paper PDF
        │
        ├───────────────────────┐
        │                       │
        ↓                       ↓
Existing Text/Table         Supplied Correct
Extraction                  Antenna Figure
        │                       │
        ↓                       │
Extracted Structure             │
        │                       │
        └──────────┬────────────┘
                   ↓
            Multimodal VLM
                   │
                   ↓
       Missing visual information
                   │
                   ↓
      Mathematical Geometry
             Constructor
                   │
                   ↓
          Enriched Structure
                   │
                   ↓
          EXISTING PIPELINE
                   │
                   ├── rank_templates()
                   ├── Template.build()
                   ├── verification
                   ├── GeometryBuilder
                   └── DXFExporter
                   │
                   ↓
                  DXF
```

------------------------------------------------------------------------

# 1. Critical Scope

## 1.1 What is being implemented

Implement only:

``` text
Component 1: Visual Gap Detector (VLM)
Component 2: Mathematical Geometry Constructor
Integration between them and the existing pipeline
```

## 1.2 What is NOT being implemented

Do NOT implement:

-   automatic figure selection from the PDF
-   automatic identification of which figure is the antenna figure
-   PDF figure ranking
-   image-to-DXF direct reconstruction
-   replacement of the existing template system
-   replacement of `GeometryBuilder`
-   replacement of `DXFExporter`
-   a new general reconciliation framework
-   a large resolution planner
-   an LLM that directly generates coordinates
-   an LLM that guesses missing dimensions
-   a new CAD generation system
-   automatic engineering guesses unsupported by explicit rules

For the first implementation, the user will provide:

``` text
paper.pdf
correct_antenna_figure.png
```

The figure-selection problem is intentionally excluded.

------------------------------------------------------------------------

# 2. Existing Base Pipeline

The existing pipeline must be treated as the foundation.

Its documented flow is:

``` text
Research Paper PDF
        ↓
Text/Table Extraction
        ↓
Dict[str, float]
        ↓
rank_templates()
        ↓
Template.build()
        ↓
verification
        ↓
GeometryBuilder
        ↓
DXFExporter
        ↓
DXF
```

The important existing entry point is:

``` text
src/antenna_reconstruction/cli.py
```

which delegates to:

``` text
src/antenna_reconstruction/template_pipeline.py
```

The PDF path eventually goes through:

``` text
extract_pdf(...)
        ↓
PdfDocument
        ↓
merged_parameters()
        ↓
Dict[str, float]
```

The current parameter structure is approximately:

``` python
{
    "W": 40.0,
    "L": 30.0,
    "SW": 50.0,
    "SL": 50.0,
    "FI": 5.0
}
```

The existing pipeline then uses:

``` text
rank_templates(values)
get_template(best_name).build(values)
builder.build_from_template(built)
exporter.export(...)
```

The existing text extractor uses `pdfplumber`, regex/prose extraction,
table extraction, and physics-related extraction.

The existing pipeline is intentionally numerical and template-driven.
The text extractor does not understand complete antenna topology and
loses structural context when the document is flattened to
`Dict[str, float]`.

The existing pipeline already contains:

-   template selection
-   template parameter processing
-   mathematical verification
-   geometry primitives
-   `GeometryBuilder`
-   DXF generation
-   diagnostics
-   `underdetermined`
-   `assumptions`
-   `derivations`
-   `verification`
-   existing unit/integration tests

Do not replace these systems.

------------------------------------------------------------------------

# 3. Exact Integration Point

The new visual-completion stage must be inserted:

``` text
AFTER:
extract_pdf(...)
merged_parameters()

BEFORE:
rank_templates(...)
```

Therefore:

``` text
Current:

extract_pdf()
    ↓
merged_parameters()
    ↓
rank_templates()
    ↓
Template.build()
    ↓
GeometryBuilder
    ↓
DXF
```

becomes:

``` text
extract_pdf()
    ↓
merged_parameters()
    ↓
VISUAL COMPLETION
    ├── VLM
    └── Mathematical Geometry Constructor
    ↓
enriched parameters/structure
    ↓
rank_templates()
    ↓
Template.build()
    ↓
GeometryBuilder
    ↓
DXF
```

This preserves the existing downstream pipeline.

------------------------------------------------------------------------

# 4. Component 1 --- Multimodal VLM

## 4.1 Purpose

The VLM is a **visual gap detector**.

Its job is NOT to reconstruct the antenna.

Its job is:

> Given the original antenna figure and the structure extracted from the
> paper text/tables, identify relevant information visible in the figure
> that is absent, incomplete, or inconsistent in the extracted
> structure.

The VLM must compare two things:

``` text
1. Figure
2. Extracted structure
```

The VLM does NOT receive the generated DXF.

This is important.

The DXF is a final output used for later evaluation. It must not be used
by the VLM to decide what information was missing from the source.

------------------------------------------------------------------------

# 5. VLM Input

The VLM must receive:

### A. Antenna figure

For the first implementation:

``` text
figure_path
```

provided explicitly by the user.

The figure is assumed to be the correct antenna figure.

Do not implement figure selection.

### B. Extracted structure

Example:

``` python
{
    "W": 40.0,
    "L": 30.0,
    "FW": 3.0,
    "FL": 15.0,
    "GL": 20.0
}
```

### C. Context

Provide enough information for the VLM to understand that the dictionary
contains antenna geometry parameters extracted from the paper.

Do not unnecessarily send the entire paper to the VLM in the first
implementation.

The primary comparison is:

``` text
figure ↔ extracted structure
```

------------------------------------------------------------------------

# 6. VLM Model

Use the requested multimodal model:

``` text
Qwen 3.8 27B
```

The implementation must isolate the model configuration in one place so
it can be changed later without rewriting the pipeline.

For example:

``` python
VLM_MODEL = os.getenv(
    "ANTENNA_VLM_MODEL",
    "Qwen-3.8-27B"
)
```

Do not hard-code API credentials.

Use an environment variable for the API key.

The exact provider/API adapter should be implemented in a dedicated VLM
client module rather than inside `template_pipeline.py`.

If the repository already has a VLM client abstraction, reuse it instead
of creating a duplicate client.

------------------------------------------------------------------------

# 7. VLM Output

The VLM must return structured JSON.

Do not rely on free-form prose.

Use a schema conceptually like:

``` json
{
  "status": "COMPLETE | MISSING | UNCERTAIN",
  "missing_items": [
    {
      "type": "PARAMETER | GEOMETRY | TOPOLOGY",
      "feature": "tapered_base",
      "description": "Symmetric tapered polygonal geometry around the feed that is visible in the figure but not represented by the extracted structure.",
      "related_parameters": ["W", "FW", "GL"],
      "visible_dimensions": [],
      "confidence": 0.0
    }
  ]
}
```

The implementation may use equivalent Python models/dataclasses, but the
semantic fields above must exist.

------------------------------------------------------------------------

# 8. Meaning of VLM Output

## COMPLETE

Use when the VLM finds no relevant missing visual information.

Example:

``` json
{
  "status": "COMPLETE",
  "missing_items": []
}
```

The extracted structure must then pass directly to the existing
pipeline.

No mathematical completion should run.

------------------------------------------------------------------------

## MISSING

Use when the figure contains information that is not represented in the
extracted structure.

Example:

``` json
{
  "status": "MISSING",
  "missing_items": [
    {
      "type": "GEOMETRY",
      "feature": "tapered_base",
      "description": "A symmetric tapered polygonal base/feed structure is visible around the feed but is absent from the extracted structure.",
      "related_parameters": ["W", "FW", "GL"],
      "visible_dimensions": [],
      "confidence": 0.91
    }
  ]
}
```

------------------------------------------------------------------------

## UNCERTAIN

Use when the VLM cannot confidently determine whether something is
missing.

Do not turn uncertainty into a reconstruction decision.

Example:

``` json
{
  "status": "UNCERTAIN",
  "missing_items": [
    {
      "type": "GEOMETRY",
      "feature": "possible_slot",
      "description": "A possible slot-like feature appears in the figure, but its topology is unclear.",
      "related_parameters": [],
      "visible_dimensions": [],
      "confidence": 0.42
    }
  ]
}
```

The mathematical constructor must not treat uncertain visual
observations as confirmed facts.

------------------------------------------------------------------------

# 9. What the VLM Must Detect

The VLM must look for both:

## 9.1 Missing parameters

Example:

``` text
Figure:
FI = 5 mm

Extracted structure:
W, L, FW, FL
```

VLM:

``` text
Missing parameter:
FI

Description:
Inset depth is explicitly labelled in the figure.
```

------------------------------------------------------------------------

## 9.2 Missing geometry/topology

This is especially important.

Example:

``` text
Extracted structure:
W
L
FW
FL
GL
```

Figure visibly contains:

``` text
tapered polygonal base/feed geometry
```

The VLM must not say only:

``` text
"some dimensions are missing"
```

It must identify the geometry itself:

``` text
Feature:
tapered polygonal base

Geometry:
symmetric polygonal/tapered structure

Relationship:
connected to feed/base region
```

This allows the next component to know what must be constructed.

------------------------------------------------------------------------

# 10. VLM Rules

The VLM prompt must explicitly enforce these rules:

### Rule 1 --- Do not invent numerical values

If a dimension is not explicitly visible and cannot be derived from the
supplied structure, do not output a guessed value.

### Rule 2 --- Distinguish feature existence from dimensions

A feature may be visible even when its dimensions are unknown.

Example:

``` text
Feature exists: YES
Dimensions known: NO
```

### Rule 3 --- Do not use the generated DXF

The VLM only compares:

``` text
figure
+
extracted structure
```

### Rule 4 --- Do not assume that absence from text means absence from the antenna

The figure is the visual evidence.

### Rule 5 --- Do not claim a feature merely because it would be expected for a template

The VLM must base visual observations on the supplied figure.

### Rule 6 --- Keep descriptions short and construction-oriented

The output should tell the mathematical component:

``` text
what is missing
what type of geometry it is
what it is connected to
which known parameters may constrain it
which dimensions are explicitly visible
```

It should not provide a long natural-language explanation.

------------------------------------------------------------------------

# 11. Component 2 --- Mathematical Geometry Constructor

## 11.1 Purpose

This is a deterministic mathematical component.

It receives:

``` text
existing extracted structure
+
VLM missing-item descriptions
```

and tries to resolve the missing information.

Its job is NOT to visually inspect the figure.

Its job is NOT to use an LLM to guess numbers.

Its job is:

> Convert a recognized missing feature into mathematically justified
> parameter values or geometry using the available extracted parameters
> and explicit geometric rules.

------------------------------------------------------------------------

# 12. Constructor Input

Conceptually:

``` python
GeometryCompletionRequest(
    parameters={
        "W": 40.0,
        "L": 30.0,
        "FW": 3.0,
        "GL": 20.0
    },
    missing_items=[
        VisualMissingItem(
            type="GEOMETRY",
            feature="tapered_base",
            description="...",
            related_parameters=["W", "FW", "GL"]
        )
    ]
)
```

------------------------------------------------------------------------

# 13. Constructor Output

Conceptually:

``` python
GeometryCompletionResult(
    resolved_parameters={
        ...
    },
    derived_geometry={
        ...
    },
    unresolved=[],
    derivations=[...]
)
```

The final result must be mergeable into the structure consumed by the
existing pipeline.

For numerical parameters:

``` python
{
    "W": 40.0,
    "L": 30.0,
    "FW": 3.0,
    "GL": 20.0,
    "FI": 5.0
}
```

For geometry that cannot be represented by an existing scalar parameter,
do NOT create fake parameter names.

Instead, the component must use the existing geometry/template extension
mechanism if one already exists.

If the existing template cannot represent the geometry, mark it as
unresolved rather than silently converting it into an incorrect
approximation.

------------------------------------------------------------------------

# 14. Mathematical Constructor Decision Hierarchy

For every missing item:

``` text
1. Is the required value explicitly present in extracted data?
       ↓
      YES → use existing value

2. Is the value explicitly provided by the figure/VLM?
       ↓
      YES → use that evidence

3. Can it be calculated from existing dimensions and
   explicit geometric relationships?
       ↓
      YES → calculate it

4. Does an existing verified template/geometry rule
   already define how to derive it?
       ↓
      YES → use that rule

5. Is there insufficient information?
       ↓
      YES → UNKNOWN
```

There must be **no arbitrary guessing step**.

------------------------------------------------------------------------

# 15. Geometry Construction Rules

The mathematical constructor must use deterministic functions.

Examples:

``` python
construct_inset_feed(...)
construct_tapered_base(...)
construct_symmetric_polygon(...)
construct_rectangle(...)
construct_trapezoid(...)
construct_slot(...)
```

Only implement functions required by the actual test cases and existing
template vocabulary.

Do not create a giant generic geometry engine.

Prefer small, testable functions.

Each function should:

1.  Validate required inputs.
2.  Check constraints.
3.  Calculate coordinates/values.
4.  Return the result.
5.  Record the derivation.
6.  Return `UNKNOWN`/unresolved when inputs are insufficient.

------------------------------------------------------------------------

# 16. Example: Tapered Polygonal Base

Suppose the VLM reports:

``` text
feature = tapered_base

description =
"Symmetric tapered polygonal base around the feed."

related_parameters =
["W", "FW", "GL"]
```

and extracted data contains:

``` python
{
    "W": 40.0,
    "FW": 3.0,
    "GL": 15.0
}
```

The constructor should look for an explicit geometric definition for
this feature.

If the repository/template defines the geometry, calculate the vertices
deterministically.

For example, if the geometry is defined by:

``` text
center_x = W / 2
feed_left = center_x - FW/2
feed_right = center_x + FW/2
base_y = GL
```

then calculate the remaining vertices from the explicit taper rule.

Do NOT invent an angle or taper ratio unless such a rule is explicitly
defined.

The output should be actual mathematical geometry:

``` python
[
    (x1, y1),
    (x2, y2),
    ...
]
```

or the existing project's equivalent `Ring`/geometry representation.

------------------------------------------------------------------------

# 17. Example: Missing Dimension

VLM:

``` text
feature = inset_feed
missing parameter = FI
visible figure dimension = 5.0 mm
```

Constructor:

``` text
FI = 5.0
```

Merge:

``` python
{
    "W": 40.0,
    "L": 30.0,
    "FW": 3.0,
    "FI": 5.0
}
```

Then send this to the existing pipeline.

------------------------------------------------------------------------

# 18. Example: Underdetermined Geometry

VLM:

``` text
feature = custom_polygon
```

Extracted:

``` python
{
    "W": 40.0
}
```

There is not enough information to determine the polygon.

Correct result:

``` text
feature_detected = true
geometry_resolved = false
reason = insufficient_constraints
```

Do NOT output:

``` text
polygon_width = 20
```

Do NOT choose arbitrary coordinates.

------------------------------------------------------------------------

# 19. Provenance

Every value added by the new component must be distinguishable from
text-extracted values.

Do not destroy the existing numerical structure.

Maintain provenance in a separate completion/diagnostic structure.

For example:

``` python
completion_derivations = [
    {
        "parameter": "FI",
        "value": 5.0,
        "source": "FIGURE_EXPLICIT",
        "method": "explicit_figure_dimension"
    },
    {
        "parameter": "X1",
        "value": 12.5,
        "source": "MATHEMATICAL_DERIVATION",
        "method": "tapered_base_geometry"
    }
]
```

The final `Dict[str, float]` can remain compatible with the existing
pipeline.

Do not redesign the entire existing data model unless the actual code
makes this unavoidable.

------------------------------------------------------------------------

# 20. Merge Rules

The merge happens before:

``` text
rank_templates()
```

The rules are:

### Existing text value

Never overwrite a text-extracted value with an unsupported VLM guess.

### Explicit figure dimension

May fill a missing parameter.

### Mathematical derivation

May fill a missing parameter only when the derivation is deterministic
and sufficiently constrained.

### Unresolved value

Must not be added to the numerical dictionary.

### Existing parameter conflict

Do not silently replace an existing extracted value.

Record the conflict and preserve the existing pipeline's verification
behavior.

------------------------------------------------------------------------

# 21. Existing Pipeline Must Remain Unchanged

After visual completion, the existing flow should continue through:

``` text
rank_templates()
    ↓
get_template(...)
    ↓
Template.build(...)
    ↓
verify()
    ↓
GeometryBuilder
    ↓
DXFExporter
```

Do not duplicate any of this logic in the new components.

Do not create another DXF exporter.

Do not create another template selector.

Do not create another geometry builder.

------------------------------------------------------------------------

# 22. Pipeline Integration

Modify `TemplatePipeline` at the point immediately after:

``` python
doc = extract_pdf(...)
values = doc.merged_parameters()
```

Conceptually:

``` python
doc = extract_pdf(pdf_path)
values = doc.merged_parameters()

if figure_path is not None:
    completion = visual_completion.complete(
        figure_path=figure_path,
        parameters=values,
    )

    values = completion.enriched_parameters

return self.run_from_parameters(values)
```

The exact implementation must follow the existing code structure rather
than blindly copying this pseudocode.

The important requirement is the location and behavior.

------------------------------------------------------------------------

# 23. Figure Input

For the first implementation, add an explicit figure input.

CLI concept:

``` bash
python ... --pdf paper.pdf --figure antenna.png
```

Do not implement automatic figure extraction/selection yet.

The figure must be passed into the VLM.

The existing behavior when no figure is supplied must remain unchanged.

Therefore:

``` text
No figure:
PDF → existing pipeline exactly as before

Figure supplied:
PDF → text extraction → visual completion → existing pipeline
```

------------------------------------------------------------------------

# 24. VLM Client Architecture

Create a dedicated client module.

Suggested structure:

``` text
src/antenna_reconstruction/
    visual_completion/
        __init__.py
        models.py
        pipeline.py

        vlm/
            __init__.py
            client.py
            prompts.py
            parser.py

        geometry/
            __init__.py
            constructor.py
            rules.py
```

Do not copy the old large `visual_evidence_reconciliation` architecture.

This is intentionally a smaller replacement/extension.

------------------------------------------------------------------------

# 25. Suggested Module Responsibilities

## `visual_completion/models.py`

Define small typed models for:

-   `VisualMissingItem`
-   `VLMAnalysis`
-   `GeometryCompletionRequest`
-   `GeometryCompletionResult`
-   `CompletionDerivation`

No business logic.

------------------------------------------------------------------------

## `visual_completion/vlm/client.py`

Responsibilities:

-   load API key from environment
-   configure Qwen model
-   send figure + structured data
-   receive raw response
-   handle API errors
-   return raw model response

No geometry calculations.

------------------------------------------------------------------------

## `visual_completion/vlm/prompts.py`

Contains the complete VLM system/user prompts.

The prompt must explicitly say:

-   compare figure with extracted data
-   identify missing information
-   identify missing geometry/topology
-   identify explicit figure dimensions
-   do not invent numerical values
-   do not use DXF
-   return JSON only
-   distinguish complete/missing/uncertain

------------------------------------------------------------------------

## `visual_completion/vlm/parser.py`

Responsibilities:

-   parse JSON
-   validate schema
-   reject malformed output
-   reject unsupported fields
-   validate numerical evidence
-   normalize feature names where appropriate
-   return `VLMAnalysis`

No geometry calculations.

------------------------------------------------------------------------

## `visual_completion/geometry/constructor.py`

Responsibilities:

-   receive extracted parameters
-   receive VLM missing items
-   dispatch to deterministic geometry rules
-   calculate values/coordinates
-   record derivations
-   report unresolved items

No API calls.

No LLM.

------------------------------------------------------------------------

## `visual_completion/geometry/rules.py`

Contains small deterministic geometry functions.

Each rule should explicitly declare:

``` text
feature name
required inputs
formula/constraint
output
failure conditions
```

------------------------------------------------------------------------

## `visual_completion/pipeline.py`

Orchestrates:

``` text
figure + extracted parameters
        ↓
VLM
        ↓
parsed missing items
        ↓
mathematical constructor
        ↓
merge
        ↓
completion result
```

This should be the only component that coordinates the two new
components.

------------------------------------------------------------------------

# 26. Error Handling

## VLM failure

If the VLM API fails:

``` text
log diagnostic
keep original extracted values
continue with existing reconstruction
```

Do not crash the entire pipeline solely because visual completion
failed.

------------------------------------------------------------------------

## VLM malformed response

Same behavior:

``` text
diagnostic
visual completion skipped
existing extracted data continues
```

------------------------------------------------------------------------

## Constructor failure

If a specific feature cannot be constructed:

``` text
record unresolved item
do not invent a value
continue existing pipeline where possible
```

------------------------------------------------------------------------

## Insufficient information

Return:

``` text
UNKNOWN / unresolved
```

Do not guess.

------------------------------------------------------------------------

# 27. Diagnostics

Add diagnostics without breaking the existing `ReconstructionResult`.

The final result should make it possible to inspect:

``` text
Visual completion:
    figure supplied: yes

VLM:
    status: MISSING

Missing items:
    - tapered_base

Constructor:
    status: RESOLVED

Derived:
    - parameter X = ...
    - geometry vertices = ...

Unresolved:
    - ...
```

Use the existing diagnostic fields where appropriate:

``` text
diagnostics
underdetermined
assumptions
derivations
verification
```

Do not create redundant diagnostic systems.

------------------------------------------------------------------------

# 28. Critical Test Case

Create a test based on the failure mode that motivated this
architecture.

The test must contain:

``` text
Extracted structure:
    contains numerical dimensions
    does NOT contain the complete base/feed polygon topology

Figure:
    clearly shows the polygonal/tapered base geometry
```

Expected VLM result:

``` text
MISSING
```

with a missing geometry item describing the base.

Expected constructor result:

``` text
RESOLVED
```

only if the supplied dimensions/rules are sufficient.

Expected final pipeline behavior:

``` text
enriched structure
        ↓
existing template/reconstruction
        ↓
geometry includes the missing feature
```

Do not compare the VLM against the generated DXF during the VLM stage.

The DXF comparison belongs to the evaluation/test stage.

------------------------------------------------------------------------

# 29. Additional Tests

Implement tests for all of these.

## Test 1 --- Nothing missing

``` text
figure matches extracted structure
```

Expected:

``` text
VLM = COMPLETE
constructor not called
original parameters unchanged
existing pipeline runs
```

------------------------------------------------------------------------

## Test 2 --- Figure-only dimension

``` text
figure contains FI = 5 mm
text structure does not contain FI
```

Expected:

``` text
VLM identifies FI
constructor adds FI = 5
existing pipeline receives FI
```

------------------------------------------------------------------------

## Test 3 --- Figure-only geometry

``` text
figure contains a visible feature
text does not describe it
```

Expected:

``` text
VLM identifies feature
constructor attempts deterministic construction
```

------------------------------------------------------------------------

## Test 4 --- Underdetermined geometry

``` text
feature visible
insufficient dimensions
```

Expected:

``` text
feature detected
geometry unresolved
no invented values
```

------------------------------------------------------------------------

## Test 5 --- VLM failure

Expected:

``` text
visual completion skipped
original text-derived structure continues
existing pipeline behavior unchanged
```

------------------------------------------------------------------------

## Test 6 --- No figure supplied

Expected:

``` text
exactly the old behavior
```

This is a regression test.

------------------------------------------------------------------------

## Test 7 --- Existing text values preserved

If text extraction provides:

``` text
W = 40
```

the visual component must not silently replace it with:

``` text
W = 38
```

unless there is an explicit conflict-handling mechanism already
supported by the existing pipeline.

------------------------------------------------------------------------

# 30. Do Not Reintroduce the Previous Large Reconciliation System

There is an existing/previous visual-evidence reconciliation
implementation in the repository.

Do not expand it into another large architecture.

Do not add:

``` text
ReconciliationReport
ResolutionPlanner
multiple resolution methods
engineering-rule planner
figure-measurement planner
large evidence-status hierarchy
```

unless existing code makes a small reuse unavoidable.

The target implementation is intentionally:

``` text
VLM
  ↓
missing information
  ↓
Mathematical Geometry Constructor
  ↓
enriched structure
  ↓
existing pipeline
```

The goal is simplicity, debuggability, and clear responsibility.

------------------------------------------------------------------------

# 31. No Autonomous Architecture Decisions

The coding agent must not independently change the architecture.

If the existing repository differs from this documentation:

1.  Inspect the actual implementation.
2.  Adapt the implementation to preserve the specified behavior.
3.  Do not redesign the architecture.
4.  Do not introduce extra components.
5.  Do not replace existing components.
6.  Do not silently change the data contract.

If an unavoidable conflict exists between this document and the current
implementation, stop and report the exact conflict rather than inventing
a new architecture.

------------------------------------------------------------------------

# 32. Implementation Order

Implement in this exact order.

### Phase 1 --- Models

Create:

``` text
visual_completion/models.py
```

Add typed models.

Write unit tests.

------------------------------------------------------------------------

### Phase 2 --- VLM Client

Create:

``` text
visual_completion/vlm/client.py
visual_completion/vlm/prompts.py
visual_completion/vlm/parser.py
```

Implement mock VLM support first.

Do not require an API call for unit tests.

------------------------------------------------------------------------

### Phase 3 --- Mathematical Constructor

Create:

``` text
visual_completion/geometry/constructor.py
visual_completion/geometry/rules.py
```

Start with deterministic rules required by the first test antenna.

Do not build a universal antenna geometry engine.

------------------------------------------------------------------------

### Phase 4 --- Visual Completion Orchestrator

Create:

``` text
visual_completion/pipeline.py
```

Implement:

``` text
figure
+
parameters
    ↓
VLM
    ↓
missing items
    ↓
constructor
    ↓
enriched parameters
```

------------------------------------------------------------------------

### Phase 5 --- Existing Pipeline Integration

Modify:

``` text
template_pipeline.py
```

Add optional figure input.

The integration must occur after text extraction and before template
ranking.

------------------------------------------------------------------------

### Phase 6 --- CLI

Modify:

``` text
cli.py
```

Add explicit figure input.

------------------------------------------------------------------------

### Phase 7 --- Tests

Run:

``` bash
pytest
```

All existing tests must continue passing.

Add new visual-completion tests.

------------------------------------------------------------------------

# 33. Final Expected API

The exact names may follow existing repository conventions, but the
conceptual API must be:

``` python
completion = visual_completion.complete(
    figure_path=figure_path,
    parameters=extracted_parameters,
)

enriched_parameters = completion.enriched_parameters
```

Then:

``` python
result = existing_pipeline.run_from_parameters(
    enriched_parameters
)
```

The existing reconstruction code remains responsible for:

``` text
template selection
template building
verification
geometry building
DXF export
```

------------------------------------------------------------------------

# 34. Final End-to-End Example

Input:

``` text
paper.pdf
antenna_figure.png
```

### Step 1 --- Text extraction

Existing extractor produces:

``` python
{
    "W": 40.0,
    "L": 30.0,
    "FW": 3.0,
    "FL": 15.0,
    "GL": 20.0
}
```

### Step 2 --- VLM

Input:

``` text
antenna_figure.png
+
{
    "W": 40.0,
    "L": 30.0,
    "FW": 3.0,
    "FL": 15.0,
    "GL": 20.0
}
```

VLM detects:

``` text
Missing geometry:
symmetric tapered polygonal base/feed structure
```

### Step 3 --- Mathematical Constructor

Input:

``` text
known parameters
+
tapered_base description
```

It checks its deterministic geometry rules.

If sufficient:

``` text
calculate vertices
```

If insufficient:

``` text
UNKNOWN
```

### Step 4 --- Merge

Resolved information is added to the reconstruction input.

### Step 5 --- Existing pipeline

``` text
rank_templates()
    ↓
Template.build()
    ↓
verify()
    ↓
GeometryBuilder
    ↓
DXFExporter
```

### Step 6 --- Output

``` text
antenna.dxf
```

with the visual information incorporated when it could be mathematically
resolved.

------------------------------------------------------------------------

# 35. Definition of Done

The implementation is complete only when all of the following are true:

-   [ ] A PDF can still run through the old pipeline with no figure.
-   [ ] A PDF plus explicitly supplied antenna figure can run visual
    completion.
-   [ ] Text extraction remains unchanged.
-   [ ] VLM receives the figure and extracted structure.
-   [ ] VLM does not receive the generated DXF.
-   [ ] VLM identifies missing parameters.
-   [ ] VLM identifies missing geometry/topology.
-   [ ] VLM does not invent numerical values.
-   [ ] Mathematical constructor receives VLM output and extracted data.
-   [ ] Mathematical constructor uses deterministic rules.
-   [ ] Mathematical constructor can return `UNKNOWN`.
-   [ ] Successfully resolved values are merged into the existing
    structure.
-   [ ] Existing `rank_templates()` remains the downstream template
    selector.
-   [ ] Existing templates remain the reconstruction system.
-   [ ] Existing verification remains active.
-   [ ] Existing `GeometryBuilder` remains responsible for geometry
    generation.
-   [ ] Existing `DXFExporter` remains responsible for DXF output.
-   [ ] Visual completion failures do not unnecessarily break text-only
    reconstruction.
-   [ ] Provenance/derivations are recorded.
-   [ ] The motivating polygon/base-geometry case is covered by a test.
-   [ ] All existing tests continue to pass.
-   [ ] No unnecessary reconciliation/resolution framework is
    introduced.

# 36. Core Principle

The entire implementation should preserve this separation:

``` text
TEXT EXTRACTOR
"What does the paper explicitly provide?"

        ↓

VLM
"What relevant geometry/information is visibly present
in the figure but absent from the extracted structure?"

        ↓

MATHEMATICAL GEOMETRY CONSTRUCTOR
"Can that missing information be deterministically derived?
If yes, calculate it. If no, return UNKNOWN."

        ↓

EXISTING RECONSTRUCTION PIPELINE
"Build the antenna from the resulting structure."

        ↓

DXF
```

Do not blur these responsibilities.

The VLM observes.

The mathematical constructor derives.

The existing pipeline reconstructs.
