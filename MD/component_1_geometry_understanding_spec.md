# Component 1 — Geometry Understanding / Extraction Engine

## 1. Purpose

Component 1 converts **structured or semi-structured geometry information** into a validated **Geometry Intermediate Representation (Geometry IR)**.

For the first development phase, Component 1 MUST use **mock/manual input only**. It must not depend on real research-paper PDF extraction, OCR, figure processing, or computer vision.

The component's job is to answer:

- What geometry objects exist?
- What primitive represents each object?
- What dimensions/parameters are explicitly known?
- What geometric relationships are known?
- What units are used?
- Where did each fact come from?
- How certain/evidential is each fact?

Component 1 MUST NOT:

- calculate final coordinates;
- solve geometric equations;
- infer missing dimensions;
- assume an object is centered unless the input explicitly states that;
- copy pixel coordinates from an image;
- scale a figure into CAD coordinates;
- generate DXF/STEP;
- perform electromagnetic antenna design calculations;
- silently resolve contradictions;
- invent engineering values.

The core responsibility is:

```text
Input geometry information
        ↓
Interpretation / extraction
        ↓
Geometry IR
```

---

# 2. Architectural Position

The complete system is:

```text
                    ANTENNA RECONSTRUCTION
                           PIPELINE

 Input / Paper
      │
      ▼
┌─────────────────────────────────────────┐
│ COMPONENT 1                              │
│ Geometry Understanding / Extraction     │
│                                         │
│ Input → Geometry IR                     │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│ COMPONENT 2                              │
│ Geometric Constraint / Coordinate Engine│
│                                         │
│ Geometry IR → Equations → Coordinates   │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│ COMPONENT 3                              │
│ Geometry / CAD Builder                  │
│                                         │
│ Coordinates → CAD                       │
└─────────────────────────────────────────┘
```

Component 1 is therefore a **producer of structured geometric facts**, not a geometry solver.

---

# 3. Development Strategy

Component 1 will be developed in stages.

## Stage 1 — Manual mock Geometry Input

Start with Python dictionaries/JSON representing information that a human has already extracted.

Example:

```json
{
  "text": "The patch has dimensions 39.4 mm × 28.9 mm and is centered on the substrate."
}
```

or an already structured mock:

```json
{
  "entities": [...],
  "parameters": [...],
  "constraints": [...]
}
```

The first implementation should prioritize the **IR, validation, provenance, and deterministic behavior**.

## Stage 2 — Controlled text extraction

After the IR and validators work, add extraction from short controlled text examples.

Example:

```text
The patch has dimensions 39.4 mm × 28.9 mm.
The patch is centered on the substrate.
```

The extractor should produce structured facts.

## Stage 3 — Real paper extraction

Only after the previous stages are stable:

```text
PDF
 ↓
PDF text/table/equation/figure extraction
 ↓
Component 1
 ↓
Geometry IR
```

Real paper processing is deliberately postponed.

---

# 4. Design Principle

The most important principle is:

> The paper/evidence is the source of geometric facts. Component 1 records those facts; Component 2 calculates consequences from them.

For example:

Input:

```text
The patch is centered on the substrate.
```

Component 1 records:

```json
{
  "type": "center_x",
  "objects": ["patch", "substrate"]
}
```

and:

```json
{
  "type": "center_y",
  "objects": ["patch", "substrate"]
}
```

Component 1 does NOT calculate:

```text
patch.x_left = 18.7
```

That calculation belongs to Component 2.

---

# 5. Responsibilities

Component 1 owns:

1. Entity identification
2. Primitive classification
3. Dimension extraction
4. Unit extraction
5. Parameter extraction
6. Relationship extraction
7. Explicit coordinate extraction, if coordinates are directly stated
8. Equation extraction as evidence, without solving it
9. Topological relationship extraction
10. Evidence/provenance
11. Confidence/evidence classification
12. Geometry IR construction
13. IR schema validation
14. Input normalization

Component 1 does not own:

1. Coordinate solving
2. Constraint-to-equation translation
3. Numerical optimization
4. Geometric inference from missing information
5. CAD creation
6. DXF export
7. EM simulation
8. Antenna performance prediction

---

# 6. Input Contract — Phase 1

During mock-data development, the input format should be simple.

Use:

```python
MockGeometryInput
```

with:

```python
{
    "source_id": "mock_patch_001",
    "text": "...",
    "metadata": {...}
}
```

Example:

```python
mock_input = {
    "source_id": "mock_patch_001",
    "text": (
        "The substrate has dimensions 76.8 mm × 57.8 mm. "
        "The patch has dimensions 39.4 mm × 28.9 mm. "
        "The patch is centered on the substrate."
    ),
    "metadata": {
        "source_type": "mock_text"
    }
}
```

The input may later become:

```text
Paper
├── text
├── tables
├── equations
├── figures
└── captions
```

but those interfaces are not required in Stage 1.

---

# 7. Geometry Intermediate Representation

Geometry IR is the central contract between Component 1 and Component 2.

Minimum top-level structure:

```json
{
  "schema_version": "1.0",
  "coordinate_system": {},
  "entities": [],
  "parameters": [],
  "constraints": [],
  "equations": [],
  "evidence": [],
  "diagnostics": []
}
```

---

# 8. Coordinate System

Component 1 should record the coordinate-system information only when it is explicitly known or deliberately defined by the reconstruction specification.

For the reconstruction system, the canonical coordinate convention is:

```text
X → right
Y → up
unit → mm
```

A default reconstruction coordinate frame may be explicitly configured as:

```json
{
  "dimension": 2,
  "unit": "mm",
  "origin_definition": {
    "type": "substrate_corner",
    "corner": "bottom_left"
  }
}
```

Important:

A coordinate convention defined by the system is different from a coordinate fact extracted from the paper.

For example:

```text
System convention:
origin = substrate bottom-left
```

does not mean:

```text
The paper explicitly stated that its origin is the substrate bottom-left.
```

These must remain distinguishable through provenance/evidence metadata.

---

# 9. Entity Model

Every physical or geometric object gets a unique ID.

Example:

```json
{
  "id": "substrate",
  "semantic_type": "substrate",
  "primitive": "rectangle"
}
```

```json
{
  "id": "patch",
  "semantic_type": "radiator",
  "primitive": "rectangle"
}
```

Recommended fields:

```json
{
  "id": "patch",
  "semantic_type": "radiator",
  "primitive": "rectangle",
  "description": "rectangular patch",
  "source_refs": ["e001"]
}
```

## Semantic types

Initial vocabulary:

```text
substrate
radiator
patch
ground
feed
slot
via
stub
cutout
hole
connector
boundary
unknown
```

This list is extensible.

## Primitive types

Initial vocabulary:

```text
point
line
rectangle
circle
arc
polygon
```

Compound/complex geometry should not be represented as an arbitrary image contour.

Instead, Component 1 should decompose it into meaningful primitives and relationships where possible.

---

# 10. Parameter Model

A parameter represents a numerical fact extracted from the input.

Example:

```json
{
  "id": "patch_width",
  "value": 39.4,
  "unit": "mm",
  "parameter_type": "length",
  "source_refs": ["e002"],
  "evidence_type": "explicit"
}
```

Recommended fields:

```text
id
value
unit
parameter_type
source_refs
evidence_type
confidence
```

Parameter types:

```text
length
width
height
radius
diameter
angle
frequency
material_property
coordinate
other
```

Component 1 may extract frequency or material properties if they are relevant evidence, but Component 2 must only consume parameters appropriate to geometric solving.

---

# 11. Units

All extracted units must be normalized.

Canonical internal unit:

```text
mm
```

Examples:

```text
1 cm  → 10 mm
1 m   → 1000 mm
500 µm → 0.5 mm
```

The original unit should remain available in provenance when useful.

Example:

```json
{
  "value": 39.4,
  "unit": "mm",
  "original_value": 3.94,
  "original_unit": "cm"
}
```

Do not silently discard the original representation.

Unknown units must produce a diagnostic instead of an invented conversion.

---

# 12. Constraint Model

A constraint describes a geometric relationship.

Example:

```json
{
  "id": "c001",
  "type": "center_x",
  "objects": ["patch", "substrate"],
  "source_refs": ["e003"],
  "evidence_type": "explicit"
}
```

A constraint should contain:

```text
id
type
objects
parameters
source_refs
evidence_type
confidence
```

The initial controlled vocabulary is:

```text
CENTER
CENTER_X
CENTER_Y
OFFSET_X
OFFSET_Y
DISTANCE
WIDTH
HEIGHT
LENGTH
RADIUS
DIAMETER
HORIZONTAL
VERTICAL
PARALLEL
PERPENDICULAR
SYMMETRIC_X
SYMMETRIC_Y
CONNECTED
INSIDE
TOUCHING
INTERSECTS
MIRROR
ROTATE
TRANSLATE
```

Not every constraint necessarily becomes a mathematical equation immediately. Topological constraints such as `CONNECTED` may be consumed by later geometry/CAD logic.

---

# 13. Evidence Types

Every extracted fact should identify how it was obtained.

Initial evidence types:

```text
explicit
derived
visual
assumed
system_defined
```

Rules:

## explicit

The source directly states the fact.

Example:

```text
"The patch width is 39.4 mm."
```

## derived

The fact was mathematically derived from other explicit facts.

Component 1 should generally avoid producing derived geometry. Derived quantities belong primarily to Component 2.

## visual

The fact comes from visual interpretation.

Example:

```text
"The slot appears centered along the patch."
```

This is not equivalent to an explicit statement.

## assumed

An assumption has been introduced.

Component 1 should avoid assumptions by default.

If assumptions are allowed by a future configuration, they must be explicitly marked.

## system_defined

The reconstruction system defines the convention.

Example:

```text
canonical unit = mm
```

---

# 14. Provenance

Provenance is mandatory.

Every important fact should point back to evidence.

For mock input:

```json
{
  "id": "e001",
  "source_id": "mock_patch_001",
  "source_type": "mock_text",
  "location": {
    "type": "text",
    "offset_start": 0,
    "offset_end": 70
  },
  "content": "The substrate has dimensions 76.8 mm × 57.8 mm."
}
```

For future papers, provenance can become:

```json
{
  "source_id": "paper_001",
  "location": {
    "type": "pdf",
    "page": 3,
    "paragraph": 2
  }
}
```

For a table:

```json
{
  "location": {
    "type": "table",
    "page": 4,
    "table_id": "table_1",
    "row": 3,
    "column": 2
  }
}
```

For a figure:

```json
{
  "location": {
    "type": "figure",
    "page": 5,
    "figure_id": "fig_2",
    "region": "patch_body"
  }
}
```

Provenance must survive the entire pipeline.

---

# 15. Visual Evidence Policy

Images are secondary evidence.

When real papers are introduced later, figures may be used for:

- object identification;
- primitive classification;
- topology;
- connectivity;
- symmetry;
- relative placement;
- labels;
- identifying which dimension label belongs to which object.

Figures should NOT automatically be used to determine exact dimensions or coordinates.

For example:

```text
Figure visually shows patch centered.
```

may become:

```json
{
  "type": "center_x",
  "evidence_type": "visual"
}
```

but it should not automatically become:

```text
patch.x_left = 18.7
```

unless the relevant numerical information is explicitly available.

---

# 16. Extraction Pipeline

The internal Component 1 pipeline should be:

```text
Input
  ↓
Input Normalizer
  ↓
Entity Extraction
  ↓
Primitive Classification
  ↓
Dimension / Parameter Extraction
  ↓
Unit Normalization
  ↓
Relationship / Constraint Extraction
  ↓
Equation Evidence Extraction
  ↓
Provenance Attachment
  ↓
Geometry IR Builder
  ↓
IR Validator
  ↓
Geometry IR
```

Each stage should have a narrow responsibility.

---

# 17. Input Normalizer

File:

```text
component1/ingestion/normalizer.py
```

Purpose:

- normalize input representation;
- ensure required fields exist;
- normalize whitespace;
- preserve original source content;
- assign source IDs if required.

It must not interpret geometry.

Example interface:

```python
def normalize_input(raw_input) -> NormalizedInput:
    ...
```

---

# 18. Entity Extractor

File:

```text
component1/extraction/entity_extractor.py
```

Purpose:

Identify geometry-related entities.

Example:

Input:

```text
The antenna consists of a rectangular patch printed on a dielectric substrate.
```

Output:

```json
[
  {
    "id": "patch",
    "semantic_type": "radiator",
    "primitive": "rectangle"
  },
  {
    "id": "substrate",
    "semantic_type": "substrate",
    "primitive": "rectangle"
  }
]
```

Entity IDs must be deterministic where possible.

Do not create multiple entities for the same object unless evidence indicates that they are different objects.

---

# 19. Primitive Classifier

File:

```text
component1/extraction/primitive_classifier.py
```

Purpose:

Map semantic descriptions to geometric primitives.

Examples:

```text
rectangular patch → rectangle
circular patch → circle
straight feed line → line
circular slot → circle/arc depending on geometry
polygonal radiator → polygon
```

If the primitive cannot be determined confidently:

```text
primitive = unknown
```

Do not force a classification.

---

# 20. Dimension Extractor

File:

```text
component1/extraction/dimension_extractor.py
```

Purpose:

Extract explicit numerical dimensions.

Example:

```text
"The patch is 39.4 mm wide and 28.9 mm long."
```

Output:

```json
[
  {
    "id": "patch_width",
    "value": 39.4,
    "unit": "mm",
    "parameter_type": "width"
  },
  {
    "id": "patch_height",
    "value": 28.9,
    "unit": "mm",
    "parameter_type": "length"
  }
]
```

The extractor should preserve the relationship between the numerical value and the object.

Avoid producing an anonymous:

```text
39.4
```

Instead produce:

```text
patch_width = 39.4 mm
```

---

# 21. Relationship Extractor

File:

```text
component1/extraction/relationship_extractor.py
```

Purpose:

Convert language describing spatial relationships into controlled constraints.

Examples:

```text
"centered on"
→ CENTER_X + CENTER_Y

"5 mm to the right of"
→ OFFSET_X

"aligned vertically with"
→ CENTER_X or VERTICAL depending on semantic context

"parallel to"
→ PARALLEL

"perpendicular to"
→ PERPENDICULAR

"inside"
→ INSIDE

"connected to"
→ CONNECTED
```

The extractor should not generate the mathematical equation.

It produces:

```json
{
  "type": "CENTER_X",
  "objects": ["patch", "substrate"]
}
```

The rule-to-equation mapping belongs to Component 2.

---

# 22. Equation Extraction

File:

```text
component1/extraction/equation_extractor.py
```

Purpose:

Identify equations explicitly presented in the source.

Example:

```text
W = c / (2f0 sqrt((εr + 1)/2))
```

Component 1 may record the equation as source evidence:

```json
{
  "id": "eq001",
  "expression": "W = c / (2*f0*sqrt((eps_r+1)/2))",
  "source_refs": ["e010"],
  "evidence_type": "explicit"
}
```

Component 1 does not solve this equation.

Important separation:

```text
Equation extraction ≠ equation solving
```

If an equation describes antenna physics rather than pure geometric relationships, it should be marked appropriately so that a future physics/design component can consume it.

---

# 23. LLM Usage

An LLM may be used for semantic extraction when the input becomes complex.

Its role:

```text
unstructured language
        ↓
structured candidate facts
```

The LLM should NOT be trusted as the final authority.

Architecture:

```text
Input
  ↓
LLM extraction
  ↓
Structured candidate JSON
  ↓
Schema validation
  ↓
Deterministic normalization
  ↓
Geometry IR
```

The LLM must not:

- calculate missing coordinates;
- invent dimensions;
- fill unspecified values;
- silently resolve contradictions;
- modify explicit numerical values;
- replace deterministic validation.

---

# 24. LLM Output Schema

A candidate LLM response should use structured JSON.

Example:

```json
{
  "entities": [
    {
      "id": "substrate",
      "semantic_type": "substrate",
      "primitive": "rectangle"
    },
    {
      "id": "patch",
      "semantic_type": "radiator",
      "primitive": "rectangle"
    }
  ],
  "parameters": [
    {
      "id": "substrate_width",
      "value": 76.8,
      "unit": "mm",
      "parameter_type": "width"
    },
    {
      "id": "substrate_height",
      "value": 57.8,
      "unit": "mm",
      "parameter_type": "height"
    }
  ],
  "constraints": [
    {
      "type": "CENTER_X",
      "objects": ["patch", "substrate"]
    },
    {
      "type": "CENTER_Y",
      "objects": ["patch", "substrate"]
    }
  ]
}
```

The response parser must reject malformed structures.

---

# 25. Validation

File:

```text
component1/ir/validator.py
```

Validation should occur before Component 1 returns Geometry IR.

Minimum checks:

## Entity validation

- IDs are unique.
- Primitive types are valid.
- Semantic types are valid where specified.

## Parameter validation

- IDs are unique.
- Values are numeric.
- Units are known.
- Lengths are not negative.
- Required source references exist.

## Constraint validation

- Constraint type is recognized.
- Referenced entity IDs exist.
- Required number of objects is present.
- Required parameters are present.

## Provenance validation

- Every extracted numerical fact has a source reference.
- Every extracted constraint has a source reference.

## Coordinate-system validation

- Dimension is valid.
- Unit is valid.
- Origin definition is structurally valid.

---

# 26. Missing Information Policy

Component 1 must preserve missing information.

Example:

```text
The patch is 39.4 mm × 28.9 mm.
```

It does NOT say where the patch is located.

Component 1 outputs dimensions only.

It must NOT add:

```text
CENTER_X
CENTER_Y
```

because that would be an unsupported assumption.

Component 2 will later determine that the geometry is underdetermined.

---

# 27. Contradiction Policy

If input contains:

```text
The patch width is 39.4 mm.
```

and later:

```text
The patch width is 41 mm.
```

Component 1 must not choose one silently.

It should preserve both:

```json
[
  {
    "id": "patch_width_1",
    "value": 39.4,
    "source_refs": ["e001"]
  },
  {
    "id": "patch_width_2",
    "value": 41.0,
    "source_refs": ["e002"]
  }
]
```

and add a diagnostic:

```json
{
  "type": "CONFLICTING_PARAMETER_VALUES",
  "severity": "error",
  "objects": ["patch"],
  "parameters": ["width"]
}
```

The system must retain provenance so a later validation/review process can inspect the conflict.

---

# 28. Confidence

Confidence is useful for extraction but must not be treated as permission to invent facts.

Recommended values:

```text
high
medium
low
```

Example:

```json
{
  "type": "CENTER_X",
  "objects": ["slot", "patch"],
  "evidence_type": "visual",
  "confidence": "medium"
}
```

A low-confidence fact should remain visibly low-confidence.

Do not automatically convert:

```text
low confidence
```

into:

```text
accepted fact
```

---

# 29. Mock Dataset

Create:

```text
tests/fixtures/component1/
```

with several cases.

## Case 1 — Simple rectangle

```text
The substrate is a rectangle with width 76.8 mm and height 57.8 mm.
```

Expected:

```text
substrate
primitive = rectangle

substrate_width = 76.8 mm
substrate_height = 57.8 mm
```

No patch should be created.

---

## Case 2 — Patch dimensions

```text
The rectangular patch has a width of 39.4 mm and a height of 28.9 mm.
```

Expected:

```text
patch
primitive = rectangle

patch_width = 39.4 mm
patch_height = 28.9 mm
```

---

## Case 3 — Centered patch

```text
The rectangular patch is centered on the substrate.
```

Expected:

```text
CENTER_X(patch, substrate)
CENTER_Y(patch, substrate)
```

No coordinates should be calculated.

---

## Case 4 — Combined

```text
The substrate has dimensions 76.8 mm × 57.8 mm.
The rectangular patch has dimensions 39.4 mm × 28.9 mm.
The patch is centered on the substrate.
```

Expected IR should contain:

```text
Entities:
    substrate
    patch

Parameters:
    substrate_width
    substrate_height
    patch_width
    patch_height

Constraints:
    CENTER_X(patch, substrate)
    CENTER_Y(patch, substrate)
```

---

## Case 5 — Offset

```text
The patch is located 5 mm to the right of the substrate center.
```

Expected:

```text
OFFSET_X(patch, substrate, 5 mm)
```

Do not calculate coordinates.

---

## Case 6 — Underspecified geometry

```text
The patch has dimensions 40 mm × 30 mm.
```

Expected:

```text
patch_width = 40 mm
patch_height = 30 mm
```

No position constraint.

---

## Case 7 — Contradiction

```text
The patch width is 40 mm.
The patch width is 42 mm.
```

Expected:

```text
two preserved parameter facts
+
conflict diagnostic
```

---

# 30. Recommended Project Structure

```text
antenna-reconstruction/
│
├── pyproject.toml
├── README.md
│
├── src/
│   └── antenna_reconstruction/
│       └── component1/
│           ├── __init__.py
│           │
│           ├── ingestion/
│           │   ├── __init__.py
│           │   ├── models.py
│           │   └── normalizer.py
│           │
│           ├── extraction/
│           │   ├── __init__.py
│           │   ├── entity_extractor.py
│           │   ├── primitive_classifier.py
│           │   ├── dimension_extractor.py
│           │   ├── relationship_extractor.py
│           │   ├── equation_extractor.py
│           │   └── extractor.py
│           │
│           ├── llm/
│           │   ├── __init__.py
│           │   ├── client.py
│           │   ├── prompts.py
│           │   ├── schemas.py
│           │   └── parser.py
│           │
│           ├── vision/
│           │   ├── __init__.py
│           │   ├── figure_analyzer.py
│           │   ├── label_detector.py
│           │   └── topology_analyzer.py
│           │
│           ├── ir/
│           │   ├── __init__.py
│           │   ├── models.py
│           │   ├── builder.py
│           │   └── validator.py
│           │
│           ├── provenance/
│           │   ├── __init__.py
│           │   ├── models.py
│           │   └── manager.py
│           │
│           └── service.py
│
├── schemas/
│   └── geometry_ir.schema.json
│
├── tests/
│   ├── unit/
│   │   └── component1/
│   ├── integration/
│   └── fixtures/
│       └── component1/
│
└── examples/
    └── component1/
```

---

# 31. Core Python Data Models

Prefer typed models.

Pydantic is recommended for validation.

Conceptual model:

```python
class Entity(BaseModel):
    id: str
    semantic_type: str
    primitive: str
    description: str | None = None
    source_refs: list[str] = []


class Parameter(BaseModel):
    id: str
    value: float
    unit: str
    parameter_type: str
    source_refs: list[str]
    evidence_type: str
    confidence: str | None = None


class Constraint(BaseModel):
    id: str
    type: str
    objects: list[str]
    parameters: dict = {}
    source_refs: list[str]
    evidence_type: str
    confidence: str | None = None


class GeometryIR(BaseModel):
    schema_version: str
    coordinate_system: dict
    entities: list[Entity]
    parameters: list[Parameter]
    constraints: list[Constraint]
    equations: list[dict] = []
    evidence: list[dict] = []
    diagnostics: list[dict] = []
```

Use immutable or controlled mutation where practical.

---

# 32. Service Interface

The external interface of Component 1 should be simple.

```python
class GeometryUnderstandingService:

    def extract(self, input_data) -> GeometryIR:
        ...
```

For Stage 1:

```python
service = GeometryUnderstandingService()

geometry_ir = service.extract(mock_input)
```

The caller should not need to know how extraction happens internally.

---

# 33. Mock Mode

During development, include an explicit mock mode.

Example:

```python
service = GeometryUnderstandingService(mode="mock")
```

Possible modes:

```text
mock
controlled_text
paper
```

Only `mock` is required initially.

Do not build PDF/OCR infrastructure before the mock version is stable.

---

# 34. Determinism

For the same mock input, Component 1 should produce equivalent Geometry IR.

Tests should not depend on:

- random LLM output;
- current date;
- external network state;
- image pixel estimation.

If an LLM is eventually used, its output should be parsed and normalized into a deterministic schema.

---

# 35. Logging

Component 1 should provide useful structured logs.

Example:

```text
[INFO] Input normalized
[INFO] Extracted entity: substrate
[INFO] Extracted entity: patch
[INFO] Extracted parameter: patch_width=39.4 mm
[INFO] Extracted parameter: patch_height=28.9 mm
[INFO] Extracted constraint: CENTER_X(patch, substrate)
[INFO] Extracted constraint: CENTER_Y(patch, substrate)
[INFO] Geometry IR validated
```

Errors:

```text
[ERROR] Unknown unit: xyz
[ERROR] Constraint references unknown entity: slot_3
[ERROR] Conflicting parameter values detected
```

Do not log sensitive API keys or raw credentials.

---

# 36. Error Categories

Define explicit errors/diagnostics.

Initial categories:

```text
INVALID_INPUT
INVALID_SCHEMA
UNKNOWN_UNIT
INVALID_ENTITY
INVALID_PARAMETER
INVALID_CONSTRAINT
MISSING_SOURCE_REFERENCE
UNKNOWN_PRIMITIVE
UNKNOWN_RELATIONSHIP
CONFLICTING_PARAMETER_VALUES
EXTRACTION_FAILURE
```

The component should fail clearly rather than silently producing bad IR.

---

# 37. Testing Strategy

Tests must be written alongside implementation.

## Unit tests

Test individually:

```text
entity extraction
primitive classification
dimension extraction
unit normalization
relationship extraction
equation extraction
provenance
IR validation
```

## Integration tests

Test:

```text
mock input
 ↓
normalizer
 ↓
extractors
 ↓
IR builder
 ↓
validator
 ↓
Geometry IR
```

## Regression tests

Every bug discovered should become a test case.

Example:

If:

```text
39.4 mm × 28.9 mm
```

was incorrectly interpreted as:

```text
39.4 m × 28.9 m
```

add a regression test before fixing the implementation.

---

# 38. Acceptance Criteria

Component 1 is considered ready for Component 2 only when:

### Entities

- Correct entities are extracted from all mock cases.
- IDs are unique.
- Primitive types are correct or explicitly `unknown`.

### Parameters

- Numerical values are extracted correctly.
- Units are normalized.
- No values are invented.
- Object-to-parameter association is preserved.

### Constraints

- Relationships are converted to controlled constraint types.
- No equations are solved.
- No coordinates are invented.

### Provenance

- Every extracted fact has evidence.
- Source references are preserved.

### Validation

- Invalid IR is rejected.
- Unknown entities referenced by constraints are detected.
- Contradictions are preserved and reported.

### Determinism

- Repeated execution on identical mock input produces equivalent IR.

---

# 39. Example End-to-End Mock Run

Input:

```text
The substrate is 76.8 mm wide and 57.8 mm high.
The rectangular patch is 39.4 mm wide and 28.9 mm high.
The patch is centered on the substrate.
```

Component 1 should produce approximately:

```json
{
  "schema_version": "1.0",

  "coordinate_system": {
    "dimension": 2,
    "unit": "mm",
    "origin_definition": {
      "type": "substrate_corner",
      "corner": "bottom_left"
    }
  },

  "entities": [
    {
      "id": "substrate",
      "semantic_type": "substrate",
      "primitive": "rectangle"
    },
    {
      "id": "patch",
      "semantic_type": "radiator",
      "primitive": "rectangle"
    }
  ],

  "parameters": [
    {
      "id": "substrate_width",
      "value": 76.8,
      "unit": "mm",
      "parameter_type": "width"
    },
    {
      "id": "substrate_height",
      "value": 57.8,
      "unit": "mm",
      "parameter_type": "height"
    },
    {
      "id": "patch_width",
      "value": 39.4,
      "unit": "mm",
      "parameter_type": "width"
    },
    {
      "id": "patch_height",
      "value": 28.9,
      "unit": "mm",
      "parameter_type": "height"
    }
  ],

  "constraints": [
    {
      "id": "c001",
      "type": "CENTER_X",
      "objects": ["patch", "substrate"]
    },
    {
      "id": "c002",
      "type": "CENTER_Y",
      "objects": ["patch", "substrate"]
    }
  ]
}
```

Notice what is intentionally absent:

```text
patch.x_left
patch.x_right
patch.y_bottom
patch.y_top
```

Those are Component 2's responsibility.

---

# 40. What Component 1 Must NOT Do in This Example

It must NOT produce:

```text
patch.x_left = 18.7
patch.x_right = 58.1
patch.y_bottom = 14.45
patch.y_top = 43.35
```

Even though those values can be calculated.

The correct architecture is:

```text
Component 1:
39.4 × 28.9
+
centered on substrate

             ↓

Component 2:
convert constraints into equations
+
solve coordinates

             ↓

Component 3:
construct CAD from coordinates
```

This separation must be maintained.

---

# 41. Future Paper-Extraction Architecture

When Component 1 eventually supports real papers, expand the ingestion layer:

```text
                    RESEARCH PAPER
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
        Text            Tables           Figures
          │               │                │
          ▼               ▼                ▼
    Text Parser       Table Parser     Vision Parser
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                 Evidence Collection
                          │
                          ▼
                  Semantic Extraction
                          │
                          ▼
                     Geometry IR
```

The existing IR contract should remain unchanged as much as possible.

This is important because Component 2 should not need to know whether information came from:

```text
mock input
controlled text
PDF text
table
equation
figure
LLM
vision model
```

It should only receive valid Geometry IR.

---

# 42. Future Vision Integration

Vision is optional and comes later.

A future figure analyzer may determine:

```text
figure contains:
- rectangular substrate
- rectangular patch
- slot
- feed line
- patch appears symmetric
```

But visual evidence must be labeled:

```json
{
  "evidence_type": "visual"
}
```

Explicit paper text should generally remain distinct:

```json
{
  "evidence_type": "explicit"
}
```

This allows downstream systems to distinguish:

```text
What the paper explicitly says
```

from:

```text
What the figure appears to show
```

---

# 43. Future LLM + Deterministic Hybrid

The intended final architecture is:

```text
                 PAPER
                   │
                   ▼
          Evidence Extraction
                   │
                   ▼
              LLM / Rules
                   │
                   ▼
        Candidate Geometry Facts
                   │
                   ▼
        Deterministic Validation
                   │
                   ▼
             Geometry IR
```

The LLM provides semantic understanding.

The deterministic code provides:

- schema enforcement;
- unit normalization;
- validation;
- provenance;
- consistency checks.

This prevents the LLM from becoming the geometry authority.

---

# 44. Non-Goals for the First Implementation

Do NOT implement these during the first Component 1 milestone:

```text
PDF parsing
OCR
computer vision
image segmentation
DXF
STEP
HFSS
CST
SymPy coordinate solving
Shapely geometry
antenna EM equations
optimization
RAG
knowledge graphs
simulation
reinforcement learning
```

These are outside the first milestone.

The first milestone is:

```text
mock geometry information
        ↓
correct Geometry IR
```

---

# 45. First Implementation Milestone

Build only enough code to demonstrate:

```text
mock input
    ↓
entity extraction
    ↓
parameter extraction
    ↓
constraint extraction
    ↓
provenance
    ↓
validation
    ↓
Geometry IR
```

Then run the seven mock test cases.

Do not proceed to Component 2 until these tests pass and the resulting IR is understandable and correct.

---

# 46. Definition of Done

Component 1 Phase 1 is DONE when the following command can conceptually work:

```bash
python examples/component1/basic_patch.py
```

and produce:

```text
Geometry IR generated successfully

Entities:
  substrate → rectangle
  patch     → rectangle

Parameters:
  substrate_width  = 76.8 mm
  substrate_height = 57.8 mm
  patch_width      = 39.4 mm
  patch_height     = 28.9 mm

Constraints:
  CENTER_X(patch, substrate)
  CENTER_Y(patch, substrate)

Coordinates:
  NONE
```

The explicit `Coordinates: NONE` is intentional.

It demonstrates that Component 1 has correctly stopped at its boundary.

---

# 47. Architectural Rule to Preserve

The most important rule for future development is:

```text
COMPONENT 1 UNDERSTANDS.
COMPONENT 2 CALCULATES.
COMPONENT 3 BUILDS.
```

More specifically:

```text
Component 1
    Paper/evidence
        ↓
    Geometric facts
        ↓
    Geometry IR

Component 2
    Geometry IR
        ↓
    Geometric constraints
        ↓
    Equations
        ↓
    Coordinates

Component 3
    Coordinates
        ↓
    Geometric primitives
        ↓
    CAD
```

No component should silently take over another component's responsibility.
