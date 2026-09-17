# Mathematical Antenna Reconstruction Core

## Engineering Specification for Components 1, 2, and 3

**Status:** Implementation specification
**Audience:** Coding agent / software engineer
**Primary objective:** Build a deterministic, traceable,
mathematics-first antenna geometry reconstruction core.

---

# 1. Non-Negotiable Engineering Rules

The coding agent must implement the architecture and decisions in this
document. It must **not make engineering or architectural decisions on
its own**.

If an implementation detail is not specified here:

1. Do not silently invent an engineering assumption.
2. Implement the smallest neutral abstraction possible.
3. Record the ambiguity in code/tests where appropriate.
4. Ask for clarification before changing the architecture.

The following principles are mandatory:

* Paper dimensions and explicit mathematical information are
  authoritative over pixel measurements.
* Images are evidence for topology, shape classification, labels, and
  relationships; they are not the default source of numerical
  dimensions.
* Component 1 interprets evidence.
* Component 2 performs mathematical constraint construction and
  solving.
* Component 3 constructs CAD geometry from already-resolved geometry.
* Component 2 must never use an LLM to invent coordinates.
* Component 3 must not reason about antenna meaning.
* No component may silently guess missing geometry.
* Every derived coordinate must be traceable to source constraints and
  equations.
* Underdetermined systems must be reported as underdetermined.
* Contradictory constraints must be reported rather than silently
  resolved.
* Units must be explicit.
* Internal geometry must use a single canonical coordinate/unit
  representation.
* Geometry generation must be deterministic.
* The core must be testable without an LLM and without a simulator.

---

# 2. Core Goal

The system converts research-paper information into exact mathematical
geometry.

The intended flow is:

```text
Research Paper
    |
    +--> Text
    +--> Tables
    +--> Equations
    +--> Figure(s)
             |
             v
Component 1: Geometry Understanding
             |
             v
Geometry IR
(objects + dimensions + relationships + evidence)
             |
             v
Component 2: Geometric Constraint Engine
             |
             v
Variables
    -> constraints
    -> equations
    -> dependency graph
    -> mathematical solve
    -> validation
             |
             v
Resolved Geometry
(exact coordinates + topology + provenance)
             |
             v
Component 3: Geometry/CAD Builder
             |
             v
CAD geometry / DXF / downstream adapters
```

---

# 3. Responsibility Boundaries

## Component 1 --- Geometry Understanding

### Purpose

Convert unstructured research evidence into a structured geometric
description.

### It answers

* What physical components exist?
* What geometric primitive represents each component?
* What dimensions are explicitly given?
* What relationships are explicitly stated or visually established?
* What source evidence supports each fact?

### It does not

* Calculate final coordinates.
* Guess missing dimensions.
* Generate DXF.
* Solve geometric equations.
* Perform antenna electromagnetic calculations.

### Implementation

Use a Python service/module containing:

* deterministic extraction utilities;
* an LLM adapter for semantic extraction;
* an optional vision adapter;
* schema validation;
* provenance handling.

The LLM is an **extractor**, not the geometry solver.

---

## Component 2 --- Geometric Constraint Engine

### Purpose

Convert structured geometric facts into equations and solve for
coordinates.

### It answers

> Given these dimensions and geometric constraints, what are the
> mathematically valid coordinates?

### It does

* establish a reference coordinate system;
* create coordinate variables;
* normalize constraints;
* map constraint types to deterministic mathematical rules;
* generate symbolic equations;
* construct dependencies;
* solve linear/nonlinear systems;
* detect underdetermined systems;
* detect contradictions;
* validate solutions;
* preserve derivations/provenance.

### It does not

* inspect the paper;
* interpret figures;
* decide what an antenna component means;
* invent missing relationships;
* use an LLM to choose coordinates;
* generate CAD files.

### Implementation

Deterministic Python.

Required technology:

* Python 3.12+
* SymPy for symbolic equations/solving
* NumPy for numerical operations
* Shapely for planar geometry validation/operations
* NetworkX for dependency graphs

Do not introduce an LLM into this component.

---

## Component 3 --- Geometry/CAD Builder

### Purpose

Convert resolved coordinates and primitive definitions into actual
geometry and CAD output.

### It answers

> Given exact geometry, how do we construct the corresponding CAD
> primitives?

### It does

* create points;
* create lines;
* create polygons;
* create circles;
* create arcs;
* apply Boolean operations;
* preserve topology;
* export CAD representations.

### It does not

* infer coordinates;
* interpret paper text;
* decide component locations;
* decide dimensions;
* repair mathematically invalid geometry;
* guess topology.

### Implementation

Deterministic Python using the selected CAD/geometry libraries and
isolated exporters.

---

# 4. Canonical Data Flow

Three representations must be maintained.

```text
Paper Evidence
      |
      v
Geometry IR
      |
      v
Mathematical Geometry
      |
      v
CAD Geometry
```

## 4.1 Geometry IR

Semantic representation.

Contains:

* entities;
* primitive types;
* dimensions;
* relationships;
* coordinate-system declaration;
* source evidence;
* confidence;
* unresolved items.

Example:

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
      "source_refs": ["page_3_table_1"]
    }
  ],
  "constraints": [
    {
      "id": "c001",
      "type": "center_x",
      "objects": ["patch", "substrate"],
      "source_refs": ["page_3_text_2"]
    }
  ]
}
```

---

# 5. Canonical Geometry Model

All internal geometry is 2D unless explicitly extended later.

Canonical unit: **millimetres (`mm`)**.

Canonical coordinate convention:

* X increases to the right.
* Y increases upward.
* origin is explicitly declared;
* no implicit origin may be introduced after parsing.

Do not mix units internally.

Input units must be normalized at ingestion.

Examples:

```text
1 m       -> 1000 mm
1 cm      -> 10 mm
1 um      -> 0.001 mm
1 inch    -> 25.4 mm
```

Unit conversion must be deterministic.

---

# 6. Component 1 Input Mode — MOCK DATA ONLY

For the current implementation, **Component 1 must not ingest or parse real research papers**.

Component 1 is being developed as a deterministic/structured mock-data adapter so that Components 2 and 3 can be implemented and tested independently of PDF extraction, OCR, vision, and LLM behavior.

This is an explicit implementation decision. The coding agent must not replace the mock input with PDF parsing, OCR, web retrieval, a vision model, or an LLM unless the specification is later changed.

## 6.1 Purpose of Mock Component 1

Component 1 currently acts as a **mock Geometry Understanding layer**. Its job is to provide correctly structured Geometry IR to Component 2.

It must simulate the output that a future paper-understanding system would produce, without implementing the future extraction system.

Therefore the current flow is:

```text
Mock Geometry Data
        |
        v
Component 1 Mock Adapter
        |
        v
Geometry IR
        |
        v
Component 2
```

The mock data must be authored explicitly. It must not be inferred from an image.

## 6.2 Current Input Format

Use JSON/YAML fixtures as the source of Component 1 input. JSON is the canonical interchange format for the implementation.

Example:

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
    },
    {
      "id": "feed",
      "semantic_type": "feed",
      "primitive": "rectangle"
    }
  ],
  "parameters": [
    {
      "id": "substrate_width",
      "entity": "substrate",
      "quantity": "width",
      "value": 76.8,
      "unit": "mm",
      "status": "explicit",
      "source_refs": ["mock_input"]
    },
    {
      "id": "substrate_height",
      "entity": "substrate",
      "quantity": "height",
      "value": 57.8,
      "unit": "mm",
      "status": "explicit",
      "source_refs": ["mock_input"]
    },
    {
      "id": "patch_width",
      "entity": "patch",
      "quantity": "width",
      "value": 39.4,
      "unit": "mm",
      "status": "explicit",
      "source_refs": ["mock_input"]
    },
    {
      "id": "patch_height",
      "entity": "patch",
      "quantity": "height",
      "value": 28.9,
      "unit": "mm",
      "status": "explicit",
      "source_refs": ["mock_input"]
    }
  ],
  "constraints": [
    {
      "id": "c001",
      "type": "center_x",
      "objects": ["patch", "substrate"],
      "source_refs": ["mock_input"],
      "evidence_type": "mock"
    },
    {
      "id": "c002",
      "type": "center_y",
      "objects": ["patch", "substrate"],
      "source_refs": ["mock_input"],
      "evidence_type": "mock"
    }
  ]
}
```

## 6.3 Mock Input Responsibilities

The mock adapter must:

1. Load a fixture.
2. Validate it against the Geometry IR schema.
3. Normalize units into the canonical internal unit.
4. Construct the Geometry IR model.
5. Pass the model to Component 2.

It must not:

* derive coordinates;
* solve equations;
* infer missing constraints;
* inspect figures;
* estimate dimensions;
* invoke an LLM;
* invoke a vision model;
* generate CAD.

## 6.4 Mock Data Must Represent Extraction Output

Mock data must look like the **output of a future extraction component**, not like raw paper text.

Correct:

```text
WIDTH(patch, 39.4 mm)
CENTER_X(patch, substrate)
```

Incorrect:

```text
"The patch seems to be approximately centered."
```

The latter would require an interpretation layer, which is intentionally excluded from the current implementation.

## 6.5 Mock Fixtures

Create fixtures for at least:

```text
fixtures/
    basic_rectangle.json
    centered_patch.json
    feed_and_patch.json
    slot_and_patch.json
    polygon_geometry.json
    underdetermined_geometry.json
    contradictory_geometry.json
```

Each fixture must be small and targeted at one behavior.

## 6.6 Future Component 1 Boundary

The eventual paper-understanding implementation will replace only the mock adapter at the input boundary. The Geometry IR contract must remain unchanged.

Future:

```text
PDF/Text/Table/Figure
        |
        v
Future extraction system
        |
        v
Same Geometry IR
        |
        v
Component 2
```

This allows Component 2 and Component 3 to be developed and tested now without coupling them to future extraction technology.

---

# 7. Component 1 Current File Architecture

Because Component 1 currently uses mock data only, do not create unused PDF/OCR/LLM/vision implementation.

```text
component1/
|
+-- mock/
|   +-- loader.py
|   +-- adapter.py
|
+-- ir/
|   +-- models.py
|   +-- builder.py
|   +-- validator.py
|
+-- provenance/
|   +-- source.py
|   +-- evidence.py
|
+-- service.py
```

The previous paper-ingestion/extraction/LLM/vision directories are **future architecture**, not part of the current implementation.

Do not implement them at this stage.

## 7.1 Mock Loader

`mock/loader.py`:

Responsibilities:

* read JSON fixture;
* parse JSON;
* return raw structured dictionary;
* report malformed JSON.

It must not transform geometry semantics.

## 7.2 Mock Adapter

`mock/adapter.py`:

Responsibilities:

* convert validated mock data into Geometry IR objects;
* preserve IDs;
* preserve source references;
* preserve explicit/mock evidence metadata.

No coordinate calculations.

## 7.3 Component 1 Service

`service.py` provides:

```python
geometry_ir = component1.load_mock(fixture_path)
```

The returned object is the exact input contract for Component 2.

---

# 8. Component 1 Output Validation\n

Before sending Geometry IR to Component 2, validate:

* every referenced entity exists;
* every dimension has a unit;
* every constraint references valid entities;
* primitive names are valid;
* source references exist;
* no malformed numerical values;
* no duplicate IDs.

Do not solve anything.

---

# 10. Component 2 Detailed Architecture

```text
component_2/
|
+-- model/
|   +-- geometry.py
|   +-- variables.py
|   +-- parameters.py
|
+-- reference/
|   +-- coordinate_system.py
|   +-- frames.py
|
+-- constraints/
|   +-- base.py
|   +-- dimension.py
|   +-- position.py
|   +-- alignment.py
|   +-- symmetry.py
|   +-- topology.py
|   +-- transformation.py
|
+-- rules/
|   +-- registry.py
|   +-- dimension_rules.py
|   +-- position_rules.py
|   +-- alignment_rules.py
|   +-- symmetry_rules.py
|   +-- distance_rules.py
|   +-- transformation_rules.py
|
+-- equations/
|   +-- symbolic.py
|   +-- generator.py
|
+-- graph/
|   +-- dependency_graph.py
|   +-- ordering.py
|
+-- solver/
|   +-- linear_solver.py
|   +-- nonlinear_solver.py
|   +-- symbolic_solver.py
|   +-- solution.py
|
+-- validation/
|   +-- constraints.py
|   +-- topology.py
|   +-- dimensions.py
|   +-- geometry.py
|
+-- provenance/
|   +-- derivation.py
|
+-- engine.py
```

---

# 11. Component 2 Core Data Model

## Point

```python
Point2D(
    x: SymbolOrValue,
    y: SymbolOrValue
)
```

Coordinates may initially be symbolic.

---

## Line

```python
Line2D(
    start: Point2D,
    end: Point2D
)
```

---

## Rectangle

Internally represent using four boundary variables or an origin +
width + height, but provide deterministic conversion to four points.

Recommended canonical mathematical representation:

```text
x_left
y_bottom
width
height
```

Derived:

```text
x_right  = x_left + width
y_top    = y_bottom + height
```

---

## Circle

```text
center_x
center_y
radius
```

---

## Polygon

```text
vertices = [Point2D, Point2D, ...]
```

---

# 12. Variables

Variables must be uniquely namespaced.

Examples:

```text
substrate.x_left
substrate.y_bottom
substrate.width
substrate.height

patch.x_left
patch.y_bottom
patch.width
patch.height
```

Symbol names used by SymPy may be:

```text
substrate__x_left
substrate__y_bottom
patch__x_left
patch__y_bottom
```

Never use ambiguous names such as `x1`, `x2` globally.

---

# 13. Constraint Representation

Base class:

```python
class Constraint:
    id: str
    type: str
    objects: list[str]
    source_refs: list[str]
    evidence_type: str
```

Every constraint must have a deterministic rule mapping.

Example:

```python
CenterXConstraint(
    id="c001",
    object_a="patch",
    object_b="substrate"
)
```

---

# 14. Geometric Rule Engine

The rule engine is the component that knows **which equation corresponds
to which geometric constraint**.

It must be implemented as deterministic code.

## Rule registry

```python
RULES = {
    "width": WidthRule(),
    "height": HeightRule(),
    "center_x": CenterXRule(),
    "center_y": CenterYRule(),
    "offset_x": OffsetXRule(),
    "offset_y": OffsetYRule(),
    "distance": DistanceRule(),
    "horizontal": HorizontalRule(),
    "vertical": VerticalRule(),
    "parallel": ParallelRule(),
    "perpendicular": PerpendicularRule(),
    "symmetric_x": SymmetricXRule(),
    "symmetric_y": SymmetricYRule(),
}
```

The rule registry is deterministic.

---

# 15. Required Mathematical Rules

## Width

Input:

```text
WIDTH(A, W)
```

Equation:

\(x\_{right}(A)-x\_{left}(A)=W\)

---

## Height

Input:

```text
HEIGHT(A, H)
```

Equation:

\(y\_{top}(A)-y\_{bottom}(A)=H\)

---

## Center X

Input:

```text
CENTER_X(A,B)
```

Equation:

$$`\frac{x_{left}(A)+x_{right}(A)}{2}`{=tex} =
`\frac{x_{left}(B)+x_{right}(B)}{2}`{=tex} \]

------------------------------------------------------------------------

## Center Y

\[ `\frac{y_{bottom}(A)+y_{top}(A)}{2}`{=tex} =
`\frac{y_{bottom}(B)+y_{top}(B)}{2}`{=tex} \]

------------------------------------------------------------------------

## Offset X

``` text
OFFSET_X(A,B,d)
```

\[ x_c(A)=x_c(B)+d \]

------------------------------------------------------------------------

## Offset Y

``` text
OFFSET_Y(A,B,d)
```

\[ y_c(A)=y_c(B)+d \]

------------------------------------------------------------------------

## Horizontal line

For line endpoints (P_1,P_2):

\[ y_1=y_2 \]

------------------------------------------------------------------------

## Vertical line

\[ x_1=x_2 \]

------------------------------------------------------------------------

## Distance

\[ (x_2-x_1)^2+(y_2-y_1)^2=d\^2 \]

Use the squared form to avoid an unnecessary square root.

------------------------------------------------------------------------

## Parallel lines

For direction vectors:

\[ v_1=(x_2-x_1,y_2-y_1) \]

\[ v_2=(x_4-x_3,y_4-y_3) \]

parallelism:

\[ v\_{1x}v\_{2y}-v\_{1y}v\_{2x}=0 \]

------------------------------------------------------------------------

## Perpendicular lines

\[ v_1`\cdot `{=tex}v_2=0 \]

therefore:

\[ v\_{1x}v\_{2x}+v\_{1y}v\_{2y}=0 \]

------------------------------------------------------------------------

## Symmetry

For vertical symmetry around (x=x_c):

\[ x_1+x_2=2x_c \]

For horizontal symmetry around (y=y_c):

\[ y_1+y_2=2y_c \]

------------------------------------------------------------------------

# 16. Reference Frame Manager

The solver must establish a coordinate frame before solving.

Example:

``` text
origin = substrate.bottom_left
```

Then:

\[ substrate.x\_{left}=0 \]

\[ substrate.y\_{bottom}=0 \]

If:

\[ W_s=76.8 \]

\[ H_s=57.8 \]

then:

\[ x\_{right}=76.8 \]

\[ y\_{top}=57.8 \]

The reference frame itself must be explicit in Geometry IR.

------------------------------------------------------------------------

# 17. Equation Generation Pipeline

``` text
Constraint
    |
    v
Constraint Registry
    |
    v
Matching Rule
    |
    v
Rule.expand()
    |
    v
Symbolic equations
    |
    v
Equation set
```

Example:

``` python
constraint = CenterXConstraint("patch", "substrate")

equations = CenterXRule().expand(
    constraint,
    geometry_model
)
```

Output:

``` python
Eq(
    (patch_x_left + patch_x_right) / 2,
    (substrate_x_left + substrate_x_right) / 2
)
```

------------------------------------------------------------------------

# 18. Dependency Graph

Build a directed graph.

Nodes:

``` text
variables
parameters
derived quantities
entities
```

Edges:

``` text
A depends on B
```

Example:

``` text
substrate.width
       |
       v
substrate.x_right
       |
       v
substrate.center_x
       |
       v
patch.center_x
       |
       v
patch.x_left
patch.x_right
```

Use NetworkX.

Detect:

-   cycles;
-   disconnected variable groups;
-   independent components;
-   dependency ordering.

A cycle is not automatically invalid, but must be identified because it
may represent mutually constraining equations.

------------------------------------------------------------------------

# 19. Solving Strategy

Use the following deterministic order.

## Stage A --- Symbolic simplification

Use SymPy:

``` text
simplify
expand
factor
cancel
```

------------------------------------------------------------------------

## Stage B --- Linear solve

If equations are linear:

\[ Ax=b \]

use symbolic linear solving / matrix methods.

------------------------------------------------------------------------

## Stage C --- Nonlinear solve

If nonlinear constraints remain:

\[ F(x)=0 \]

use the configured nonlinear solver.

Do not randomly choose an initial guess.

If an initial value is required and is not supplied by the geometry
specification, return an unresolved/solver-required status rather than
inventing one.

------------------------------------------------------------------------

# 20. Solution States

The solver must return one of:

``` text
SOLVED
UNDERDETERMINED
INCONSISTENT
NUMERICALLY_UNRESOLVED
INVALID_INPUT
```

## SOLVED

Unique valid coordinate solution.

## UNDERDETERMINED

Multiple valid solutions remain.

## INCONSISTENT

No solution satisfies all constraints.

## NUMERICALLY_UNRESOLVED

Mathematical formulation exists but configured numerical solving failed.

## INVALID_INPUT

Geometry IR is malformed.

------------------------------------------------------------------------

# 21. Example: Centered Patch

Input:

``` text
substrate width = 76.8
substrate height = 57.8

patch width = 39.4
patch height = 28.9

patch.center_x = substrate.center_x
patch.center_y = substrate.center_y
```

Reference:

\[ substrate=(0,0) \]

Equations:

\[ x\_{sr}=76.8 \]

\[ y\_{st}=57.8 \]

\[ x\_{pr}-x\_{pl}=39.4 \]

\[ y\_{pt}-y\_{pb}=28.9 \]

\[ `\frac{x_{pl}+x_{pr}}{2}`{=tex}=38.4 \]

\[ `\frac{y_{pb}+y_{pt}}{2}`{=tex}=28.9 \]

Solution:

\[ x\_{pl}=18.7 \]

\[ x\_{pr}=58.1 \]

\[ y\_{pb}=14.45 \]

\[ y\_{pt}=43.35 \]

Resolved corners:

``` text
P1 = (18.7, 14.45)
P2 = (58.1, 14.45)
P3 = (58.1, 43.35)
P4 = (18.7, 43.35)
```

Roof line:

``` text
Line(
    start=(18.7, 43.35),
    end=(58.1, 43.35)
)
```

------------------------------------------------------------------------

# 22. Missing Information Policy

Example:

``` text
patch.width = 39.4
patch.height = 28.9
```

No placement constraint.

The solver can determine:

\[ x_r-x_l=39.4 \]

and:

\[ y_t-y_b=28.9 \]

but cannot determine absolute location.

Return:

``` json
{
  "status": "UNDERDETERMINED",
  "unknowns": [
    "patch.x_left",
    "patch.y_bottom"
  ]
}
```

Never default to center.

Never copy a coordinate from a figure.

Never estimate coordinates from pixel proportions.

------------------------------------------------------------------------

# 23. Constraint Provenance

Every equation must retain:

``` text
equation ID
source constraint ID
source evidence
rule ID
variables
```

Example:

``` json
{
  "equation_id": "eq_031",
  "equation": "patch_x_right - patch_x_left = 39.4",
  "rule": "width",
  "constraint_id": "c_012",
  "source_refs": ["page_3_table_1"]
}
```

Every resolved variable must store its derivation.

Example:

``` json
{
  "variable": "patch.x_left",
  "value": 18.7,
  "derived_from": [
    "eq_031",
    "eq_034"
  ]
}
```

------------------------------------------------------------------------

# 24. Geometry Validation

Validation occurs after solving.

## Dimension validation

Verify every explicit dimension.

Example:

\[ x_r-x_l=39.4 \]

must evaluate within configured numerical tolerance.

------------------------------------------------------------------------

## Constraint validation

Verify every relation.

Example:

\[ center_x(patch)=center_x(substrate) \]

------------------------------------------------------------------------

## Primitive validation

Rectangle:

``` text
width > 0
height > 0
```

Circle:

``` text
radius > 0
```

Polygon:

``` text
minimum valid vertex count
no invalid self-intersection where prohibited
```

------------------------------------------------------------------------

## Topological validation

Examples:

``` text
INSIDE(slot, patch)
CONNECTED(feed, patch)
```

must be tested against resolved geometry.

------------------------------------------------------------------------

# 25. Numerical Tolerance

All numerical comparisons must use a centralized tolerance
configuration.

Example:

``` python
ToleranceConfig(
    absolute=1e-9,
    relative=1e-9
)
```

Do not hard-code tolerances in individual rules.

The tolerance must be configurable.

------------------------------------------------------------------------

# 26. Component 3 Detailed Architecture

``` text
component_3/
|
+-- primitives/
|   +-- point.py
|   +-- line.py
|   +-- rectangle.py
|   +-- polygon.py
|   +-- circle.py
|   +-- arc.py
|
+-- topology/
|   +-- connectivity.py
|   +-- relations.py
|
+-- boolean/
|   +-- union.py
|   +-- difference.py
|   +-- intersection.py
|
+-- model/
|   +-- cad_model.py
|   +-- layer.py
|
+-- exporters/
|   +-- dxf.py
|   +-- step.py
|   +-- svg.py
|
+-- adapters/
|   +-- hfss.py
|   +-- cst.py
|
+-- builder.py
```

------------------------------------------------------------------------

# 27. Primitive Builder

The builder receives resolved mathematical geometry.

Example:

``` python
builder.line(
    start=(18.7, 43.35),
    end=(58.1, 43.35)
)
```

It does not calculate those values.

------------------------------------------------------------------------

# 28. Primitive API

Required operations:

``` python
create_point(x, y)

create_line(start, end)

create_rectangle(x, y, width, height)

create_polygon(vertices)

create_circle(center, radius)

create_arc(center, radius, start_angle, end_angle)
```

All inputs must already be resolved.

------------------------------------------------------------------------

# 29. Boolean API

Required:

``` python
union(A, B)

difference(A, B)

intersection(A, B)
```

Example:

``` text
patch = rectangle(...)
slot = rectangle(...)

final_patch = difference(patch, slot)
```

The Boolean engine must not determine whether the slot should exist.
That decision comes from Geometry IR.

------------------------------------------------------------------------

# 30. Topology

Represent topology separately from coordinates.

Example:

``` json
{
  "relation": "connected",
  "objects": ["feed", "patch"]
}
```

The builder uses this to ensure the resulting CAD model preserves the
required relationship.

------------------------------------------------------------------------

# 31. CAD Export

The exporter receives the internal CAD model.

``` text
CAD Model
   |
   +--> DXF exporter
   +--> STEP exporter
   +--> SVG exporter
   +--> HFSS adapter
   +--> CST adapter
```

Exporters must not contain engineering logic.

They are serialization/adaptation layers.

------------------------------------------------------------------------

# 32. Complete Repository Structure

Use the following repository structure.

``` text
antenna-reconstruction/
|
+-- pyproject.toml
+-- README.md
+-- LICENSE
|
+-- src/
|   +-- antenna_reconstruction/
|       |
|       +-- core/
|       |   +-- units/
|       |   +-- identifiers/
|       |   +-- errors/
|       |   +-- provenance/
|       |
|       +-- component1/
|       |   +-- ingestion/
|       |   +-- extraction/
|       |   +-- llm/
|       |   +-- vision/
|       |   +-- ir/
|       |   +-- provenance/
|       |   +-- service.py
|       |
|       +-- component2/
|       |   +-- model/
|       |   +-- reference/
|       |   +-- constraints/
|       |   +-- rules/
|       |   +-- equations/
|       |   +-- graph/
|       |   +-- solver/
|       |   +-- validation/
|       |   +-- provenance/
|       |   +-- engine.py
|       |
|       +-- component3/
|           +-- primitives/
|           +-- topology/
|           +-- boolean/
|           +-- model/
|           +-- exporters/
|           +-- adapters/
|           +-- builder.py
|
+-- schemas/
|   +-- geometry_ir.schema.json
|   +-- resolved_geometry.schema.json
|   +-- cad_geometry.schema.json
|
+-- rules/
|   +-- geometry_rules.yaml
|
+-- tests/
|   |
|   +-- unit/
|   |   +-- component1/
|   |   +-- component2/
|   |   +-- component3/
|   |
|   +-- integration/
|   |
|   +-- fixtures/
|       +-- simple_rectangle/
|       +-- centered_patch/
|       +-- slot_patch/
|       +-- underdetermined/
|       +-- contradictory/
|
+-- examples/
|   +-- basic_patch/
|
+-- docs/
|   +-- architecture.md
|   +-- data_model.md
|   +-- constraint_system.md
|   +-- rule_reference.md
|   +-- provenance.md
|
+-- scripts/
|   +-- validate_ir.py
|   +-- solve_geometry.py
|   +-- export_geometry.py
```

------------------------------------------------------------------------

# 33. Dependency Direction

Dependencies must flow one way:

``` text
component1
    ↓
component2
    ↓
component3
```

Component 2 must not import Component 1's LLM implementation.

Component 3 must not import Component 1 or Component 2's solver
internals.

Shared models belong in `core` or explicit schema packages.

------------------------------------------------------------------------

# 34. Interfaces Between Components

## Component 1 → Component 2

``` python
GeometryIR
```

No free-form text.

No raw LLM response.

No image.

------------------------------------------------------------------------

## Component 2 → Component 3

``` python
ResolvedGeometry
```

It must contain:

-   resolved coordinates;
-   primitive types;
-   topology;
-   units;
-   coordinate frame;
-   provenance;
-   validation status.

------------------------------------------------------------------------

# 35. Resolved Geometry Schema

Example:

``` json
{
  "schema_version": "1.0",
  "status": "SOLVED",
  "coordinate_system": {
    "dimension": 2,
    "unit": "mm",
    "origin": [0, 0]
  },
  "objects": [
    {
      "id": "patch",
      "primitive": "polygon",
      "vertices": [
        [18.7, 14.45],
        [58.1, 14.45],
        [58.1, 43.35],
        [18.7, 43.35]
      ]
    }
  ],
  "topology": [],
  "derivations": []
}
```

------------------------------------------------------------------------

# 36. Error Handling

Use typed exceptions/statuses.

Required categories:

``` text
InvalidGeometryIR
UnknownConstraint
UnsupportedPrimitive
MissingParameter
UnderdeterminedSystem
InconsistentConstraints
SolverFailure
GeometryValidationError
ExportError
UnitError
```

Do not catch all exceptions and continue.

Do not silently produce partial geometry unless explicitly configured.

------------------------------------------------------------------------

# 37. Logging

Use structured logs.

Every pipeline run gets a:

``` text
run_id
```

Log:

``` text
component
operation
entity_id
constraint_id
equation_id
source_refs
status
```

Do not log sensitive API keys or raw secrets.

------------------------------------------------------------------------

# 38. Testing Strategy

The mathematical core must be tested independently of the LLM.

## Unit tests

### Width

Input:

``` text
x_left = 5
width = 10
```

Expected:

``` text
x_right = 15
```

### Centering

Input:

``` text
substrate = 100
patch = 40
centered
```

Expected:

``` text
patch_left = 30
patch_right = 70
```

### Offset

``` text
center = 50
offset = 10
```

Expected:

``` text
new_center = 60
```

### Distance

Verify Euclidean distance.

### Rotation

Verify transformation matrix.

### Symmetry

Verify mirrored coordinates.

------------------------------------------------------------------------

# 39. Integration Tests

Required integration fixtures:

## Fixture 1 --- Simple rectangle

``` text
substrate
patch
centered patch
```

Expected exact coordinates.

## Fixture 2 --- Feed

``` text
patch
feed
feed width
feed length
feed alignment
```

## Fixture 3 --- Slot

``` text
patch
slot
slot dimensions
slot offset
difference operation
```

## Fixture 4 --- Underdetermined

Missing position.

Expected:

``` text
UNDERDETERMINED
```

## Fixture 5 --- Contradictory

Two conflicting dimensions.

Expected:

``` text
INCONSISTENT
```

------------------------------------------------------------------------

# 40. Determinism Requirement

Running the same Geometry IR multiple times must produce identical
mathematical output.

Test:

``` python
result_a = solve(ir)
result_b = solve(ir)

assert result_a == result_b
```

No randomness in Component 2 or 3.

------------------------------------------------------------------------

# 41. LLM Boundary

The LLM is permitted only in Component 1.

Allowed:

``` text
paper text
    ↓
LLM
    ↓
structured geometry facts
```

Not allowed:

``` text
constraints
    ↓
LLM
    ↓
coordinates
```

Not allowed:

``` text
coordinates
    ↓
LLM
    ↓
DXF
```

The mathematical and CAD stages must remain deterministic.

------------------------------------------------------------------------

# 42. Important Distinction: Dimension Calculation vs Geometry Reconstruction

Do not mix these.

A paper may contain antenna design equations:

\[ W = `\frac{c}{2f}`{=tex}`\sqrt{\frac{2}{\epsilon_r+1}}`{=tex} \]

That equation may be relevant to calculating an antenna dimension.

But the current core's Component 2 is primarily a **geometric coordinate
solver**.

Therefore:

``` text
Antenna Physics Calculator
```

must remain a separate future component.

Component 2 may consume a dimension that was already provided/calculated
upstream, but must not independently redesign the antenna.

Example:

``` text
Physics Design Layer
        ↓
patch_width = W
        ↓
Geometry IR
        ↓
Coordinate Solver
```

Do not put electromagnetic design equations into the geometric rule
engine unless they are explicitly defined as part of the separate
physics-design layer.

------------------------------------------------------------------------

# 43. Example End-to-End Execution

Input evidence:

``` text
Substrate: 76.8 × 57.8 mm
Patch: 39.4 × 28.9 mm
Patch centered on substrate
```

## Component 1

Produces:

``` text
Entity(substrate, rectangle)
Entity(patch, rectangle)

WIDTH(substrate, 76.8)
HEIGHT(substrate, 57.8)

WIDTH(patch, 39.4)
HEIGHT(patch, 28.9)

CENTER(patch, substrate)
```

## Component 2

Creates:

``` text
substrate.x_left
substrate.x_right
substrate.y_bottom
substrate.y_top

patch.x_left
patch.x_right
patch.y_bottom
patch.y_top
```

Generates equations.

Solves equations.

Returns:

``` text
patch:
P1 = (18.7,14.45)
P2 = (58.1,14.45)
P3 = (58.1,43.35)
P4 = (18.7,43.35)
```

## Component 3

Receives:

``` text
patch polygon vertices
```

Creates CAD geometry.

Exports:

``` text
antenna.dxf
```

------------------------------------------------------------------------

# 44. Coding Agent Implementation Order

The coding agent must implement in this order.

## Phase 1

Build:

``` text
core units
core models
Geometry IR
ResolvedGeometry
```

No LLM.

No CAD.

------------------------------------------------------------------------

## Phase 2

Build Component 2:

``` text
geometry model
coordinate frame
variables
constraint classes
rule registry
equation generator
SymPy solver
validation
provenance
```

Test entirely with manually written Geometry IR fixtures.

------------------------------------------------------------------------

## Phase 3

Build Component 3:

``` text
point
line
rectangle
polygon
circle
arc
Boolean operations
topology
DXF exporter
```

Test using manually created ResolvedGeometry.

------------------------------------------------------------------------

## Phase 4

Build Component 1:

``` text
paper ingestion
text extraction
table extraction
LLM extraction
structured output
figure analysis
IR validation
```

Only after Components 2 and 3 are stable.

------------------------------------------------------------------------

## Phase 5

Connect:

``` text
Component 1 → Component 2 → Component 3
```

Add integration tests.

------------------------------------------------------------------------

# 45. What the Coding Agent Must Not Do

The coding agent must not decide:

-   whether image measurement should replace paper dimensions;
-   which antenna equations should be used;
-   whether an antenna is physically correct;
-   whether an unstated component is probably centered;
-   whether a missing coordinate should be guessed;
-   which solver strategy is more appropriate than the specified
    strategy;
-   whether a visual approximation is acceptable;
-   whether a conflicting dimension should be preferred;
-   whether an electromagnetic design assumption is valid;
-   whether geometry should be altered to make a DXF valid.

Those decisions belong to the system specification or the human
engineer.

The agent's role is:

> **Implement the specified architecture exactly, write the code, write
> tests, and report implementation errors/ambiguities.**

------------------------------------------------------------------------

# 46. Final Core Architecture

``` text
                         ┌───────────────────┐
                         │   RESEARCH PAPER  │
                         └─────────┬─────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
                  TEXT           TABLES         FIGURES
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                                   ▼
              ╔════════════════════════════════════╗
              ║ COMPONENT 1                        ║
              ║ GEOMETRY UNDERSTANDING             ║
              ║                                    ║
              ║ LLM + extraction + optional vision ║
              ║                                    ║
              ║ entities                           ║
              ║ primitives                         ║
              ║ dimensions                         ║
              ║ relationships                      ║
              ║ evidence/provenance                ║
              ╚══════════════════╤═════════════════╝
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   GEOMETRY IR   │
                        └────────┬────────┘
                                 │
                                 ▼
              ╔════════════════════════════════════╗
              ║ COMPONENT 2                        ║
              ║ GEOMETRIC CONSTRAINT ENGINE       ║
              ║                                    ║
              ║ Reference Frame                    ║
              ║       ↓                            ║
              ║ Variable Generator                ║
              ║       ↓                            ║
              ║ Constraint Normalizer             ║
              ║       ↓                            ║
              ║ Geometric Rule Engine              ║
              ║       ↓                            ║
              ║ Equation Generator                ║
              ║       ↓                            ║
              ║ Dependency Graph                  ║
              ║       ↓                            ║
              ║ SymPy Solver                      ║
              ║       ↓                            ║
              ║ Solution Resolver                 ║
              ║       ↓                            ║
              ║ Geometry Validator                ║
              ║       ↓                            ║
              ║ Provenance                         ║
              ╚══════════════════╤═════════════════╝
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │ RESOLVED GEOMETRY    │
                     │                      │
                     │ Exact coordinates    │
                     │ Primitive types      │
                     │ Topology             │
                     │ Derivations          │
                     └──────────┬───────────┘
                                │
                                ▼
              ╔════════════════════════════════════╗
              ║ COMPONENT 3                        ║
              ║ GEOMETRY / CAD BUILDER             ║
              ║                                    ║
              ║ Primitive Factory                 ║
              ║       ↓                            ║
              ║ Lines / Polygons / Circles / Arcs ║
              ║       ↓                            ║
              ║ Boolean Geometry                   ║
              ║       ↓                            ║
              ║ Topology                           ║
              ║       ↓                            ║
              ║ CAD Model                          ║
              ║       ↓                            ║
              ║ Exporters                          ║
              ╚══════════════════╤═════════════════╝
                                 │
                                 ▼
                         DXF / STEP / CAD
```

------------------------------------------------------------------------

# 47. Core Principle

The implementation must preserve this chain:

\[ `\boxed{
\text{Evidence}
\rightarrow
\text{Geometric Facts}
\rightarrow
\text{Constraints}
\rightarrow
\text{Equations}
\rightarrow
\text{Coordinates}
\rightarrow
\text{Geometry}
}`{=tex} \]

Every coordinate must have a mathematical derivation.

Every mathematical equation must come from a defined geometric rule.

Every geometric rule must correspond to a defined constraint.

Every constraint must be traceable to structured evidence or an
explicitly supplied design constraint.

No pixel-derived coordinate may silently enter the mathematical solver.

No LLM-generated coordinate may silently enter the CAD builder.

No missing engineering information may be silently guessed.
$$
