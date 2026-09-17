# Component 2 — Geometric Constraint & Coordinate Engine

## 1. Purpose

Component 2 is the mathematical core of the antenna reconstruction pipeline.

Its job is to take the **Geometry Intermediate Representation (Geometry IR)** produced by Component 1 and convert the extracted geometric information into a mathematically resolved geometry.

The component must:

1. Read entities, parameters, and geometric constraints from Geometry IR.
2. Create mathematical variables for unknown geometric quantities.
3. Translate each supported constraint into equations.
4. Build dependencies between entities and parameters.
5. Solve the resulting system symbolically and/or numerically.
6. Detect underdetermined, inconsistent, or numerically unresolved systems.
7. Validate the resulting geometry against all supplied constraints.
8. Preserve the derivation/provenance of every calculated value.
9. Produce a deterministic `Resolved Geometry` representation for Component 3.

The fundamental responsibility boundary is:

> **Component 1 understands. Component 2 calculates. Component 3 builds.**

Component 2 must not interpret research papers, inspect figures, infer antenna intent, or generate CAD.

---

# 2. Position in the Pipeline

```text
                    PAPER
                      |
                      v
        +-----------------------------+
        | COMPONENT 1                 |
        | Geometry Understanding      |
        +-----------------------------+
                      |
                      v
              Geometry IR
                      |
                      v
        +-----------------------------+
        | COMPONENT 2                 |
        | Constraint & Coordinate     |
        | Engine                      |
        +-----------------------------+
                      |
                      v
             Resolved Geometry
                      |
                      v
        +-----------------------------+
        | COMPONENT 3                 |
        | Geometry / CAD Builder      |
        +-----------------------------+
                      |
                      v
                 DXF / STEP
```

Component 2 must only depend on the structured output of Component 1.

It must not directly depend on:

- PDF files
- OCR
- image processing
- LLMs
- CAD files
- antenna simulators
- paper figures

---

# 3. Core Design Principle

The system must reconstruct geometry from **mathematical relationships**, not by tracing pixels.

For example, if Component 1 extracts:

```text
Substrate:
width = 76.8 mm
height = 57.8 mm

Patch:
width = 39.4 mm
height = 28.9 mm

Relationship:
patch centered in substrate
```

Component 2 must construct equations such as:

```text
substrate.x_right - substrate.x_left = 76.8

substrate.y_top - substrate.y_bottom = 57.8

patch.x_right - patch.x_left = 39.4

patch.y_top - patch.y_bottom = 28.9

center_x(patch) = center_x(substrate)

center_y(patch) = center_y(substrate)
```

It then solves those equations.

For an origin at the substrate bottom-left:

```text
substrate:
(0, 0) -> (76.8, 57.8)

patch:
(18.7, 14.45) -> (58.1, 43.35)
```

The important point is that these coordinates are **calculated**, not extracted from the image.

---

# 4. Responsibilities

## 4.1 Component 2 MUST

Component 2 must:

- create coordinate variables;
- normalize units;
- translate constraints into equations;
- resolve parameter dependencies;
- solve known dimensions;
- calculate coordinates;
- handle geometric relationships;
- validate solutions;
- detect contradictions;
- detect insufficient information;
- preserve mathematical derivations;
- provide deterministic output;
- provide useful diagnostic errors.

## 4.2 Component 2 MUST NOT

Component 2 must not:

- read PDFs;
- perform OCR;
- interpret figures;
- identify antenna components from images;
- guess missing dimensions;
- guess missing positions;
- choose an arbitrary coordinate system silently;
- invent dimensions;
- invent geometric relationships;
- modify Geometry IR to make it solvable;
- decide what geometry an antenna "should" have;
- optimize antenna performance;
- perform electromagnetic simulation;
- generate DXF directly;
- use an LLM to solve geometry.

---

# 5. Input Contract

Component 2 receives a validated Geometry IR.

Conceptually:

```python
resolved_geometry = component2.solve(geometry_ir)
```

The Geometry IR should contain information such as:

```json
{
  "coordinate_system": {
    "dimension": 2,
    "x_direction": "right",
    "y_direction": "up",
    "unit": "mm",
    "origin": {
      "type": "substrate_bottom_left"
    }
  },

  "entities": [
    {
      "id": "substrate",
      "type": "rectangle"
    },
    {
      "id": "patch",
      "type": "rectangle"
    }
  ],

  "parameters": [
    {
      "id": "substrate_width",
      "value": 76.8,
      "unit": "mm"
    },
    {
      "id": "substrate_height",
      "value": 57.8,
      "unit": "mm"
    },
    {
      "id": "patch_width",
      "value": 39.4,
      "unit": "mm"
    },
    {
      "id": "patch_height",
      "value": 28.9,
      "unit": "mm"
    }
  ],

  "constraints": [
    {
      "type": "WIDTH",
      "entity": "substrate",
      "parameter": "substrate_width"
    },
    {
      "type": "HEIGHT",
      "entity": "substrate",
      "parameter": "substrate_height"
    },
    {
      "type": "WIDTH",
      "entity": "patch",
      "parameter": "patch_width"
    },
    {
      "type": "HEIGHT",
      "entity": "patch",
      "parameter": "patch_height"
    },
    {
      "type": "CENTER_X",
      "entity_a": "patch",
      "entity_b": "substrate"
    },
    {
      "type": "CENTER_Y",
      "entity_a": "patch",
      "entity_b": "substrate"
    }
  ]
}
```

The exact schema must match the Component 1 specification.

---

# 6. Coordinate Convention

The initial implementation uses a 2D Cartesian coordinate system.

## 6.1 Axes

```text
          +Y
           ^
           |
           |
           |
           +----------> +X
         origin
```

- +X = right
- +Y = up

## 6.2 Canonical Unit

The internal canonical unit is:

```text
millimeter (mm)
```

All calculations must be performed in canonical units.

Input values may originate in:

- mm
- cm
- m
- μm
- inch

but must be normalized before solving.

## 6.3 Origin

The origin must be explicitly defined by Geometry IR.

Example:

```text
origin = substrate_bottom_left
```

Then:

```text
substrate.bottom_left = (0, 0)
```

Component 2 must never silently choose an origin.

If Geometry IR does not contain enough information to establish the requested coordinate frame, the result must report the appropriate unresolved/invalid status.

---

# 7. Geometry Representation

The initial engine should support a small deterministic set of geometric primitives.

## 7.1 Point

```text
P = (x, y)
```

## 7.2 Rectangle

Represent a rectangle using four named corners:

```text
bottom_left
bottom_right
top_right
top_left
```

with:

```text
BL = (x_l, y_b)
BR = (x_r, y_b)
TR = (x_r, y_t)
TL = (x_l, y_t)
```

For the initial version, rectangles are axis-aligned unless rotation is explicitly supported by a later specification.

## 7.3 Circle

```text
center = (cx, cy)
radius = r
```

## 7.4 Polygon

A polygon is represented by an ordered list of points:

```text
P0, P1, P2, ..., Pn
```

## 7.5 Line Segment

```text
start = P1
end   = P2
```

## 7.6 Arc

An arc may later be represented using:

```text
center
radius
start_angle
end_angle
```

Arc solving is not required for the first minimal implementation unless required by the test fixtures.

---

# 8. Mathematical Variable Model

Every unresolved coordinate must be represented by a mathematical variable.

For a rectangle:

```text
x_left
x_right
y_bottom
y_top
```

Example:

```text
patch_x_left
patch_x_right
patch_y_bottom
patch_y_top
```

SymPy symbols should be used internally.

Example conceptual representation:

```python
x_left = Symbol("patch_x_left")
x_right = Symbol("patch_x_right")
y_bottom = Symbol("patch_y_bottom")
y_top = Symbol("patch_y_top")
```

The solver must never substitute a guessed numeric value merely because a variable is unresolved.

---

# 9. Parameter Dependency System

Some dimensions are explicitly supplied.

Others may be equations involving other parameters.

Example:

```text
substrate_width = 76.8 mm
patch_width = substrate_width / 2
```

The engine should resolve:

```text
patch_width = 38.4 mm
```

The dependency chain must be preserved.

Example:

```text
patch_width
    |
    v
substrate_width / 2
    |
    v
76.8 / 2
    |
    v
38.4 mm
```

Each derived value must retain a derivation record.

---

# 10. Constraint Rule Library

Constraint translation must be deterministic.

Each constraint type maps to a known mathematical rule.

The initial rule library must include the following.

---

## 10.1 WIDTH

For rectangle `A`:

```text
x_right(A) - x_left(A) = W
```

Example:

```text
patch_width = 39.4
```

becomes:

```text
patch_x_right - patch_x_left = 39.4
```

---

## 10.2 HEIGHT

For rectangle `A`:

```text
y_top(A) - y_bottom(A) = H
```

Example:

```text
patch_height = 28.9
```

becomes:

```text
patch_y_top - patch_y_bottom = 28.9
```

---

# 11. Center Constraints

## 11.1 CENTER_X

The x-center of an axis-aligned rectangle is:

```text
center_x(A) = (x_left(A) + x_right(A)) / 2
```

Constraint:

```text
center_x(A) = center_x(B)
```

Therefore:

```text
(x_left(A) + x_right(A)) / 2
=
(x_left(B) + x_right(B)) / 2
```

---

## 11.2 CENTER_Y

Similarly:

```text
center_y(A) = (y_bottom(A) + y_top(A)) / 2
```

Constraint:

```text
center_y(A) = center_y(B)
```

---

# 12. Offset Constraints

## 12.1 OFFSET_X

If:

```text
center_x(A) = center_x(B) + d
```

then:

```text
(x_left(A) + x_right(A))/2
-
(x_left(B) + x_right(B))/2
=
d
```

---

## 12.2 OFFSET_Y

Similarly:

```text
center_y(A) = center_y(B) + d
```

---

# 13. Edge Alignment

## 13.1 LEFT_ALIGN

```text
x_left(A) = x_left(B)
```

## 13.2 RIGHT_ALIGN

```text
x_right(A) = x_right(B)
```

## 13.3 TOP_ALIGN

```text
y_top(A) = y_top(B)
```

## 13.4 BOTTOM_ALIGN

```text
y_bottom(A) = y_bottom(B)
```

---

# 14. Horizontal and Vertical Relationships

## 14.1 HORIZONTAL

For two points:

```text
y1 = y2
```

## 14.2 VERTICAL

For two points:

```text
x1 = x2
```

These constraints may be applied to:

- points;
- line endpoints;
- rectangle edges;
- polygon vertices.

---

# 15. Distance Constraint

For points:

```text
P1 = (x1, y1)
P2 = (x2, y2)
```

distance:

```text
sqrt((x2-x1)^2 + (y2-y1)^2) = d
```

To avoid unnecessary square roots, the solver may use:

```text
(x2-x1)^2 + (y2-y1)^2 = d^2
```

Example:

```text
distance(feed, patch_left_edge) = 5
```

must become a deterministic equation according to the supported point/edge representation.

The engine must not interpret what "feed distance" means unless Component 1 has represented it as an explicit geometric relationship.

---

# 16. Parallel Constraint

For vectors:

```text
v1 = (x1, y1)
v2 = (x2, y2)
```

parallelism in 2D can be represented as:

```text
x1*y2 - y1*x2 = 0
```

The engine must preserve the distinction between:

- parallel;
- coincident;
- overlapping;
- same direction;
- opposite direction.

A parallel constraint alone does not determine position.

---

# 17. Perpendicular Constraint

For vectors:

```text
v1 = (x1, y1)
v2 = (x2, y2)
```

perpendicularity:

```text
x1*x2 + y1*y2 = 0
```

Again, this is a relationship, not a complete positional definition.

---

# 18. Symmetry

For symmetry around a vertical axis:

```text
x_symmetry = c
```

and points:

```text
P1 = (x1, y1)
P2 = (x2, y2)
```

must satisfy:

```text
(x1 + x2) / 2 = c
```

with:

```text
y1 = y2
```

For symmetry around a horizontal axis:

```text
(y1 + y2) / 2 = c
```

with:

```text
x1 = x2
```

The specific symmetry axis must be explicitly represented in Geometry IR.

---

# 19. Containment

For a rectangle `A` inside rectangle `B`:

```text
x_left(B) <= x_left(A)
x_right(A) <= x_right(B)

y_bottom(B) <= y_bottom(A)
y_top(A) <= y_top(B)
```

Containment should normally be treated as a validation/geometric inequality constraint rather than an equation.

The system must not convert containment into a centered placement.

For example:

```text
inside substrate
```

does NOT mean:

```text
centered in substrate
```

---

# 20. Touching / Contact

If two axis-aligned rectangles explicitly touch at a vertical edge:

```text
x_right(A) = x_left(B)
```

If they touch at a horizontal edge:

```text
y_top(A) = y_bottom(B)
```

The contact direction must come from the Geometry IR.

The solver must not infer touching merely because two dimensions happen to permit it.

---

# 21. Explicit Coordinates

If Component 1 extracts an explicit coordinate from a source:

```text
feed center = (20, 15) mm
```

Component 2 should create:

```text
feed_x = 20
feed_y = 15
```

These are source constraints.

Explicit source coordinates must not be overridden by derived values without reporting a contradiction.

---

# 22. Coordinate System Translation

If the source uses a different coordinate frame, Component 1 should describe that frame explicitly.

Component 2 may support deterministic coordinate transformations such as:

```text
translation
reflection
rotation
```

only when the transformation is explicitly specified.

Example:

```text
source origin = substrate center
internal origin = substrate bottom-left
```

For a substrate of width `W` and height `H`:

```text
x_internal = x_source + W/2
y_internal = y_source + H/2
```

The transformation itself must be represented and recorded.

The engine must not silently reinterpret coordinates.

---

# 23. Constraint Graph

Component 2 should build a dependency graph.

Example:

```text
substrate
    |
    +---- width
    |
    +---- height
    |
    v
patch
    |
    +---- width
    +---- height
    |
    v
center constraints
    |
    v
patch coordinates
```

A graph representation allows the system to determine:

- what depends on what;
- which variables are unresolved;
- which equations are connected;
- where contradictions originate.

NetworkX may be used for the dependency graph.

The mathematical equation system remains the authoritative representation.

---

# 24. Solving Strategy

The initial implementation must use deterministic solving.

Recommended libraries:

```text
Python 3.12+
SymPy
NumPy
NetworkX
Shapely
```

## 24.1 Preferred order

The engine should attempt:

1. symbolic parameter resolution;
2. symbolic equation solving;
3. deterministic numerical solving when symbolic solving is insufficient;
4. geometric validation.

The system must not randomly switch algorithms.

The selected solver and method must be recorded in diagnostics.

---

# 25. Linear vs Nonlinear Systems

The engine must distinguish between:

### Linear

Example:

```text
x2 - x1 = 39.4
x1 + x2 = 76.8
```

### Nonlinear

Example:

```text
(x2-x1)^2 + (y2-y1)^2 = 25
```

Nonlinear systems may have:

- zero solutions;
- one solution;
- multiple solutions;
- infinitely many solutions.

The engine must not arbitrarily select a solution when multiple valid solutions exist unless the Geometry IR contains an explicit disambiguating constraint.

---

# 26. Underdetermined Systems

An underdetermined system contains insufficient information to uniquely resolve geometry.

Example:

```text
patch width = 39.4
patch height = 28.9
substrate = 76.8 × 57.8
```

but no patch position.

The system knows the size but not the position.

It must return:

```text
UNDERDETERMINED
```

It must NOT automatically center the patch.

Correct behavior:

```text
patch_width  = 39.4
patch_height = 28.9

patch_x_left  = unknown
patch_y_bottom = unknown
```

unless additional constraints define them.

---

# 27. Inconsistent Systems

Example:

```text
substrate width = 76.8
substrate left = 0
substrate right = 70
```

These constraints conflict because:

```text
70 - 0 != 76.8
```

Result:

```text
INCONSISTENT
```

The engine must report:

- conflicting constraints;
- involved entities;
- equations;
- source provenance where available.

It must not silently prioritize one source.

---

# 28. Multiple Solutions

Example:

```text
distance(P, origin) = 10
```

alone produces a circle of possible positions.

If another constraint still permits two valid points, the solver must report multiple solutions rather than arbitrarily choosing one.

Possible result:

```text
MULTIPLE_SOLUTIONS
```

This status may be included in the result model even if the initial implementation primarily exposes it through diagnostics.

---

# 29. Numerical Tolerance

Floating-point calculations require tolerance.

A configurable tolerance must be used for numerical validation.

Example:

```python
DEFAULT_ABSOLUTE_TOLERANCE = 1e-9
```

The exact tolerance must be defined centrally in configuration.

Do not scatter numerical thresholds throughout the codebase.

Validation should distinguish:

```text
exact symbolic equality
```

from:

```text
numerical approximate equality
```

Example:

```text
abs(calculated - expected) <= tolerance
```

---

# 30. Geometry Validation

After solving, every supplied constraint must be checked again against the resolved geometry.

Example:

Input:

```text
patch width = 39.4
```

Resolved:

```text
patch_x_left = 18.7
patch_x_right = 58.1
```

Validation:

```text
58.1 - 18.7 = 39.4
```

If a constraint fails, the result must not be marked `SOLVED`.

---

# 31. Topological Validation

Component 2 should perform basic geometric validity checks where possible.

Examples:

- rectangle has positive width;
- rectangle has positive height;
- polygon has sufficient vertices;
- polygon is not self-intersecting when required;
- circle radius > 0;
- contained components actually satisfy containment;
- explicitly touching objects actually touch;
- explicitly separated objects do not overlap when separation is required.

Complex CAD topology remains Component 3's responsibility.

---

# 32. Result Statuses

The engine must use explicit statuses.

Minimum required statuses:

```text
SOLVED
UNDERDETERMINED
INCONSISTENT
NUMERICALLY_UNRESOLVED
INVALID_INPUT
```

Optional:

```text
MULTIPLE_SOLUTIONS
VALIDATION_FAILED
```

## 32.1 SOLVED

All required variables have unique valid values and all constraints pass validation.

## 32.2 UNDERDETERMINED

The available constraints do not uniquely determine all required geometry.

## 32.3 INCONSISTENT

The constraints cannot all be true simultaneously.

## 32.4 NUMERICALLY_UNRESOLVED

The mathematical problem is valid but the selected numerical method could not reliably resolve it.

## 32.5 INVALID_INPUT

The Geometry IR itself violates the Component 2 input contract.

---

# 33. Resolved Geometry Output

The output should contain:

```text
status
coordinate_system
resolved entities
resolved parameters
constraints
derivations
validation report
diagnostics
```

Example:

```json
{
  "status": "SOLVED",

  "coordinate_system": {
    "dimension": 2,
    "unit": "mm",
    "x_direction": "right",
    "y_direction": "up",
    "origin": "substrate_bottom_left"
  },

  "entities": [
    {
      "id": "substrate",
      "type": "rectangle",
      "geometry": {
        "bottom_left": [0, 0],
        "bottom_right": [76.8, 0],
        "top_right": [76.8, 57.8],
        "top_left": [0, 57.8]
      }
    },
    {
      "id": "patch",
      "type": "rectangle",
      "geometry": {
        "bottom_left": [18.7, 14.45],
        "bottom_right": [58.1, 14.45],
        "top_right": [58.1, 43.35],
        "top_left": [18.7, 43.35]
      }
    }
  ]
}
```

---

# 34. Derivation Records

Every calculated quantity should be traceable.

Example:

```json
{
  "target": "patch_x_left",
  "value": 18.7,
  "unit": "mm",

  "derivation": {
    "operation": "center_minus_half_width",
    "inputs": [
      "substrate_center_x",
      "patch_width"
    ],
    "equation": "38.4 - 39.4/2"
  }
}
```

This allows later debugging.

The system should make it possible to answer:

> "Why is this coordinate 18.7 mm?"

Answer:

```text
substrate center = 38.4 mm
patch width = 39.4 mm

patch left = 38.4 - 39.4/2
            = 18.7 mm
```

---

# 35. Provenance Preservation

Component 1 provenance must survive Component 2.

For example:

```text
patch_width
    |
    +-- source: paper page 4
    +-- figure: Fig. 3
    +-- evidence: explicit dimension
```

Then:

```text
patch_x_left
    |
    +-- derived from patch_width
    +-- derived from substrate_center_x
    +-- source dependencies preserved
```

Component 2 must not discard source provenance when producing derived geometry.

---

# 36. Assumptions

Component 2 must distinguish:

```text
source-derived fact
```

from:

```text
system-defined convention
```

Example:

```text
origin = substrate_bottom_left
```

may be a system-defined coordinate convention.

It must not be represented as if the research paper explicitly stated it.

Likewise, Component 2 must not introduce assumptions such as:

```text
patch is centered
```

unless that relationship exists in Geometry IR.

---

# 37. Example — Complete Simple Reconstruction

Input:

```text
Substrate:
76.8 × 57.8 mm

Patch:
39.4 × 28.9 mm

Patch:
centered on substrate
```

## Step 1 — Substrate coordinates

Origin:

```text
(0, 0)
```

Width:

```text
76.8
```

Height:

```text
57.8
```

Therefore:

```text
BL = (0, 0)
BR = (76.8, 0)
TR = (76.8, 57.8)
TL = (0, 57.8)
```

## Step 2 — Substrate center

```text
center_x = 76.8 / 2
         = 38.4

center_y = 57.8 / 2
         = 28.9
```

## Step 3 — Patch half dimensions

```text
half_width = 39.4 / 2
           = 19.7

half_height = 28.9 / 2
            = 14.45
```

## Step 4 — Patch coordinates

```text
left   = 38.4 - 19.7
       = 18.7

right  = 38.4 + 19.7
       = 58.1

bottom = 28.9 - 14.45
       = 14.45

top    = 28.9 + 14.45
       = 43.35
```

## Final

```text
patch:
BL = (18.7, 14.45)
BR = (58.1, 14.45)
TR = (58.1, 43.35)
TL = (18.7, 43.35)
```

No image tracing is involved.

---

# 38. Example — Offset Patch

Input:

```text
substrate = 100 × 80 mm
patch = 40 × 20 mm

patch center:
30 mm from substrate left edge
25 mm from substrate bottom edge
```

Equations:

```text
substrate:
x_left = 0
y_bottom = 0

substrate width:
x_right - x_left = 100

substrate height:
y_top - y_bottom = 80

patch width:
patch_x_right - patch_x_left = 40

patch height:
patch_y_top - patch_y_bottom = 20

patch center:
(patch_x_left + patch_x_right)/2 = 30

(patch_y_bottom + patch_y_top)/2 = 25
```

Solution:

```text
patch_x_left  = 10
patch_x_right = 50

patch_y_bottom = 15
patch_y_top    = 35
```

---

# 39. Example — Underdetermined Geometry

Input:

```text
substrate = 100 × 80
patch = 40 × 20
```

No placement relationship.

Known:

```text
patch width = 40
patch height = 20
```

Unknown:

```text
patch_x_left
patch_x_right
patch_y_bottom
patch_y_top
```

The engine must return:

```text
UNDERDETERMINED
```

It must not produce:

```text
patch = centered
```

---

# 40. Example — Contradiction

Input:

```text
substrate width = 100
substrate left = 0
substrate right = 90
```

Equations:

```text
x_right - x_left = 100
x_left = 0
x_right = 90
```

Therefore:

```text
90 - 0 != 100
```

Result:

```text
INCONSISTENT
```

Diagnostic:

```text
Conflicting constraints:
- substrate width = 100 mm
- substrate left = 0 mm
- substrate right = 90 mm
```

---

# 41. No Guessing Policy

This is a mandatory rule.

Component 2 must never do the following:

```text
missing coordinate -> guess
missing dimension -> guess
missing relation -> guess
multiple solutions -> choose one arbitrarily
conflicting dimensions -> choose one silently
```

Instead:

```text
missing information -> unresolved
conflict -> inconsistent
multiple valid solutions -> multiple solutions
```

Any future heuristic must be explicitly specified as part of the system design and must never be silently introduced.

---

# 42. Solver Architecture

Recommended internal architecture:

```text
Geometry IR
    |
    v
Input Validator
    |
    v
Unit Normalizer
    |
    v
Parameter Resolver
    |
    v
Variable Registry
    |
    v
Constraint Compiler
    |
    v
Equation System
    |
    +------------------+
    |                  |
    v                  v
Symbolic Solver    Numeric Solver
    |                  |
    +--------+---------+
             |
             v
       Solution Resolver
             |
             v
       Geometry Builder
             |
             v
       Constraint Validator
             |
             v
       Resolved Geometry
```

---

# 43. Module Responsibilities

Suggested project structure:

```text
component2/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── variables.py
│   ├── equations.py
│   ├── solution.py
│   └── diagnostics.py
│
├── validation/
│   ├── __init__.py
│   ├── input_validator.py
│   └── geometry_validator.py
│
├── units/
│   ├── __init__.py
│   └── converter.py
│
├── parameters/
│   ├── __init__.py
│   └── resolver.py
│
├── constraints/
│   ├── __init__.py
│   ├── base.py
│   ├── dimensions.py
│   ├── alignment.py
│   ├── center.py
│   ├── distance.py
│   ├── orientation.py
│   └── symmetry.py
│
├── solver/
│   ├── __init__.py
│   ├── symbolic.py
│   ├── numerical.py
│   └── dispatcher.py
│
├── graph/
│   ├── __init__.py
│   └── dependency_graph.py
│
├── derivation/
│   ├── __init__.py
│   └── tracker.py
│
└── engine.py
```

The exact project structure can be changed only if the architectural responsibilities remain equivalent.

---

# 44. Constraint Compiler

The constraint compiler is responsible for converting Geometry IR constraints into mathematical expressions.

Conceptually:

```python
equations = compiler.compile(geometry_ir)
```

Example:

```text
WIDTH(patch, 39.4)
```

becomes:

```python
patch_x_right - patch_x_left - 39.4
```

which represents:

```text
patch_x_right - patch_x_left = 39.4
```

The compiler must be deterministic.

The same Geometry IR must produce the same equations.

---

# 45. Variable Registry

The variable registry maintains the relationship between:

```text
Geometry IR entity
```

and:

```text
mathematical variable
```

Example:

```text
patch.x_left
    -> Symbol("patch_x_left")

patch.x_right
    -> Symbol("patch_x_right")

patch.y_bottom
    -> Symbol("patch_y_bottom")

patch.y_top
    -> Symbol("patch_y_top")
```

It must prevent duplicate or ambiguous variable names.

---

# 46. Parameter Resolver

The parameter resolver handles:

```text
explicit values
```

and:

```text
derived expressions
```

Example:

```text
patch_width = substrate_width / 2
```

must first resolve:

```text
substrate_width = 76.8
```

then:

```text
patch_width = 38.4
```

Circular dependencies must be detected.

Example:

```text
A = B / 2
B = A / 2
```

must not enter an infinite loop.

---

# 47. Equation System

Internally, the engine should maintain a formal equation system:

```text
Variables:
x1, x2, y1, y2, ...

Equations:
e1 = 0
e2 = 0
e3 = 0
...
```

Example:

```text
x_right - x_left - 39.4 = 0

y_top - y_bottom - 28.9 = 0

x_left + x_right - 76.8 = 0

y_bottom + y_top - 57.8 = 0
```

The equation system is the mathematical source of truth for Component 2.

---

# 48. Solver Result Classification

After solving, classify the system.

Conceptually:

```text
             Equation System
                    |
          +---------+---------+
          |         |         |
          v         v         v
        zero     one      multiple/
       solutions solution  infinite
          |         |         |
          v         v         v
    INCONSISTENT  SOLVED   UNRESOLVED/
                            MULTIPLE
```

For a single unique solution:

```text
SOLVED
```

For insufficient constraints:

```text
UNDERDETERMINED
```

For contradictory equations:

```text
INCONSISTENT
```

---

# 49. Constraint Validation Report

The output should include something similar to:

```json
{
  "constraints_checked": 6,
  "constraints_passed": 6,
  "constraints_failed": 0,
  "tolerance": 1e-9
}
```

For failures:

```json
{
  "constraint_id": "c_004",
  "expected": 39.4,
  "actual": 40.0,
  "residual": 0.6,
  "status": "FAILED"
}
```

A residual should be available wherever meaningful.

---

# 50. Residuals

For an equation:

```text
f(x) = 0
```

after substitution of the solution:

```text
residual = f(solution)
```

For an ideal exact solution:

```text
residual = 0
```

For numerical solutions:

```text
abs(residual) <= tolerance
```

is acceptable.

Residuals should be preserved for diagnostics.

---

# 51. Determinism

Given identical:

```text
Geometry IR
configuration
solver version
```

the component should produce the same result.

The component must not contain:

- random coordinate generation;
- random initialization unless explicitly controlled;
- LLM calls;
- probabilistic geometry selection;
- image-based guessing.

---

# 52. Logging

The engine should log major processing stages.

Example:

```text
[INFO] Geometry IR validated
[INFO] Units normalized to mm
[INFO] Registered 8 coordinate variables
[INFO] Compiled 6 constraints
[INFO] Equation system classified as linear
[INFO] Symbolic solution found
[INFO] 6/6 constraints validated
[INFO] Geometry solved successfully
```

Errors should identify the affected entity/constraint whenever possible.

---

# 53. Error Handling

Errors must be structured.

Example:

```json
{
  "code": "CONSTRAINT_REFERENCE_ERROR",
  "message": "Constraint references unknown entity 'feed_3'.",
  "constraint_id": "c_17"
}
```

Potential error categories:

```text
INVALID_GEOMETRY_IR
UNKNOWN_ENTITY
UNKNOWN_PARAMETER
UNKNOWN_CONSTRAINT
UNIT_ERROR
VARIABLE_ERROR
CONSTRAINT_COMPILATION_ERROR
SOLVER_ERROR
VALIDATION_ERROR
INCONSISTENT_CONSTRAINTS
UNDERDETERMINED_GEOMETRY
```

---

# 54. API

The primary public interface should be simple.

Example:

```python
from component2.engine import GeometryConstraintEngine

engine = GeometryConstraintEngine()

result = engine.solve(geometry_ir)
```

The result must contain:

```python
result.status
result.geometry
result.parameters
result.derivations
result.validation
result.diagnostics
```

The public interface must not expose internal SymPy implementation details unnecessarily.

---

# 55. Testing Strategy

Component 2 must be developed independently before integration with Component 1.

Tests should use manually prepared Geometry IR fixtures.

Recommended structure:

```text
tests/
├── fixtures/
│   ├── simple/
│   │   ├── centered_patch.json
│   │   ├── offset_patch.json
│   │   └── explicit_coordinates.json
│   │
│   ├── underdetermined/
│   │   ├── missing_position.json
│   │   └── missing_dimension.json
│   │
│   ├── inconsistent/
│   │   ├── conflicting_width.json
│   │   └── conflicting_position.json
│   │
│   └── nonlinear/
│       └── distance_constraint.json
│
├── test_dimensions.py
├── test_center.py
├── test_alignment.py
├── test_distance.py
├── test_parameters.py
├── test_solver.py
├── test_validation.py
└── test_diagnostics.py
```

---

# 56. Minimum Test Cases

The first implementation must pass at least these cases.

## Test 1 — Rectangle dimensions

Input:

```text
width = 100
height = 50
```

Expected:

```text
width = 100
height = 50
```

---

## Test 2 — Centered rectangle

Input:

```text
substrate = 100 × 80
patch = 40 × 20
centered
```

Expected:

```text
patch:
BL = (30, 30)
BR = (70, 30)
TR = (70, 50)
TL = (30, 50)
```

---

## Test 3 — Offset rectangle

Input:

```text
substrate = 100 × 80
patch = 40 × 20
center_x = 30
center_y = 25
```

Expected:

```text
BL = (10, 15)
BR = (50, 15)
TR = (50, 35)
TL = (10, 35)
```

---

## Test 4 — Explicit coordinates

Input:

```text
BL = (10, 20)
width = 40
height = 30
```

Expected:

```text
BR = (50, 20)
TR = (50, 50)
TL = (10, 50)
```

---

## Test 5 — Underdetermined

Input:

```text
width = 40
height = 20
```

No placement.

Expected:

```text
UNDERDETERMINED
```

---

## Test 6 — Contradiction

Input:

```text
width = 40
left = 0
right = 50
```

Expected:

```text
INCONSISTENT
```

---

## Test 7 — Unit conversion

Input:

```text
width = 10 cm
```

Expected canonical value:

```text
100 mm
```

---

## Test 8 — Parameter dependency

Input:

```text
substrate_width = 80 mm
patch_width = substrate_width / 2
```

Expected:

```text
patch_width = 40 mm
```

---

# 57. Property-Based Testing

Where practical, use property-based tests.

Example for centered rectangles:

For random valid:

```text
substrate width W
substrate height H
patch width w
patch height h
```

the solver should produce:

```text
patch center_x = W/2
patch center_y = H/2
```

and:

```text
patch width = w
patch height = h
```

This helps detect algebraic implementation errors.

---

# 58. Integration Test with Component 1

After Component 1 is stable:

```text
mock text
    |
    v
Component 1
    |
    v
Geometry IR
    |
    v
Component 2
    |
    v
Resolved Geometry
```

The expected Geometry IR from Component 1 should be compared against the expected resolved geometry.

The test must verify that Component 2 does not depend on how Component 1 internally extracted the information.

---

# 59. Component 2 Does Not Need Real Papers Yet

During initial development, Component 2 should use:

```text
manually created Geometry IR
```

not:

```text
PDF
OCR
LLM
vision
```

This isolates mathematical errors from extraction errors.

Development order:

```text
manual Geometry IR
        |
        v
Component 2
        |
        v
correct mathematical result
```

Only after this works:

```text
real paper
    |
    v
Component 1
    |
    v
Geometry IR
    |
    v
Component 2
```

---

# 60. No CAD in Component 2

Component 2 may produce:

```text
points
edges
rectangles
polygons
circles
```

as resolved mathematical geometry.

It must not produce:

```text
DXF
STEP
STL
FreeCAD document
OpenSCAD file
```

Those belong to Component 3.

For example:

```text
Component 2:

patch corners:
[(18.7,14.45),
 (58.1,14.45),
 (58.1,43.35),
 (18.7,43.35)]
```

Component 3 converts this mathematical representation into CAD entities.

---

# 61. No Electromagnetic Reasoning

Component 2 must not calculate:

```text
resonant frequency
gain
S11
bandwidth
impedance
radiation pattern
efficiency
```

unless such calculations are explicitly part of a separate mathematical geometry constraint and not an EM design task.

Those belong to later antenna-design/simulation components.

Component 2 answers:

> "Where is this geometric entity and what are its dimensions?"

It does not answer:

> "Is this a good antenna?"

---

# 62. Future Extension — 3D Geometry

The first implementation is 2D.

Future versions may introduce:

```text
x
y
z
```

and primitives such as:

```text
box
cylinder
sphere
3D polygon
extrusion
```

This must not complicate the first implementation unnecessarily.

The 2D engine should be completed and tested first.

---

# 63. Future Extension — Rotation

Initial rectangles are axis-aligned.

Future support may introduce:

```text
center
width
height
rotation_angle
```

and transform local coordinates into global coordinates.

Rotation must only be introduced after the axis-aligned system is stable.

---

# 64. Future Extension — Advanced Constraints

Potential later constraints include:

```text
ANGLE
TANGENT
COLLINEAR
CONCENTRIC
EQUAL_LENGTH
EQUAL_RADIUS
EQUAL_DISTANCE
MIDPOINT
POLYGON_AREA
SYMMETRY
ROTATION
REFLECTION
```

Each must have:

1. explicit Geometry IR representation;
2. deterministic mathematical rule;
3. unit tests;
4. validation logic;
5. provenance support.

No constraint should be added merely because a particular paper requires it without defining its mathematical semantics.

---

# 65. Debugging Mode

The engine should provide a debug mode that exposes:

```text
variables
equations
substitutions
solver method
solution
residuals
constraint validation
derivations
```

Example:

```text
VARIABLES
---------
substrate_x_left = 0
substrate_x_right = 76.8
patch_x_left = ?
patch_x_right = ?

EQUATIONS
---------
patch_x_right - patch_x_left = 39.4
patch_x_left + patch_x_right = 76.8

SOLUTION
--------
patch_x_left = 18.7
patch_x_right = 58.1

VALIDATION
----------
WIDTH: PASS
CENTER_X: PASS
```

This is especially important during early development.

---

# 66. Intermediate Artifacts

For debugging, Component 2 may optionally output:

```text
equations.json
variables.json
dependency_graph.json
solution.json
validation.json
derivations.json
```

These artifacts are for debugging and inspection.

The canonical output remains the `Resolved Geometry` object.

---

# 67. Acceptance Criteria

Component 2 is considered complete for the first version when:

- Geometry IR can be validated.
- Units are normalized to mm.
- Coordinate variables are created deterministically.
- Rectangle width/height constraints work.
- Center constraints work.
- Offset constraints work.
- Edge alignment works.
- Explicit coordinates work.
- Basic distance constraints work.
- Parameter dependencies work.
- Symbolic solving works for supported systems.
- Numerical solving is available where explicitly required.
- Underdetermined systems are detected.
- Inconsistent systems are detected.
- Multiple-solution cases are not silently guessed.
- Every solved coordinate can be traced to its inputs.
- Every input constraint is validated after solving.
- No LLM is required.
- No image is required.
- No CAD library is required for the solver itself.
- Tests cover normal, missing, conflicting, and derived cases.
- The same input produces deterministic output.

---

# 68. First Implementation Scope

Do NOT implement the entire theoretical system immediately.

Version 1 should support only:

```text
2D
axis-aligned rectangles
points
mm
explicit dimensions
explicit coordinates
CENTER_X
CENTER_Y
OFFSET_X
OFFSET_Y
LEFT_ALIGN
RIGHT_ALIGN
TOP_ALIGN
BOTTOM_ALIGN
WIDTH
HEIGHT
basic containment
symbolic solving
basic validation
derivation tracking
```

After this works, add:

```text
distance
horizontal
vertical
parallel
perpendicular
symmetry
circles
polygons
nonlinear solving
```

Then expand only when real antenna examples require it.

---

# 69. Development Sequence

Follow this exact sequence.

### Phase 1 — Data Models

Implement:

```text
Variable
Parameter
Equation
Constraint
ResolvedEntity
SolutionResult
Diagnostic
ValidationResult
Derivation
```

### Phase 2 — Input Validation

Implement:

```text
Geometry IR validation
entity validation
parameter validation
constraint reference validation
unit validation
```

### Phase 3 — Variable Registry

Implement deterministic variable creation.

### Phase 4 — Unit Normalization

Convert all supported input units to mm.

### Phase 5 — Constraint Compiler

Implement:

```text
WIDTH
HEIGHT
CENTER_X
CENTER_Y
OFFSET_X
OFFSET_Y
LEFT_ALIGN
RIGHT_ALIGN
TOP_ALIGN
BOTTOM_ALIGN
```

### Phase 6 — Symbolic Solver

Use SymPy.

### Phase 7 — Geometry Reconstruction

Convert solved variables into:

```text
points
rectangles
```

### Phase 8 — Validation

Re-evaluate all constraints.

### Phase 9 — Derivation Tracking

Record how every resolved quantity was obtained.

### Phase 10 — Diagnostics

Implement:

```text
SOLVED
UNDERDETERMINED
INCONSISTENT
NUMERICALLY_UNRESOLVED
INVALID_INPUT
```

### Phase 11 — Tests

Run the complete fixture suite.

Only after all of these work should Component 2 be connected to Component 1.

---

# 70. Example End-to-End Code Contract

Conceptually:

```python
geometry_ir = load_geometry_ir("centered_patch.json")

engine = GeometryConstraintEngine()

result = engine.solve(geometry_ir)

if result.status == "SOLVED":
    print(result.geometry)

elif result.status == "UNDERDETERMINED":
    print(result.diagnostics)

elif result.status == "INCONSISTENT":
    print(result.diagnostics)
```

Expected successful output:

```text
SOLVED

substrate:
  BL = (0, 0)
  BR = (76.8, 0)
  TR = (76.8, 57.8)
  TL = (0, 57.8)

patch:
  BL = (18.7, 14.45)
  BR = (58.1, 14.45)
  TR = (58.1, 43.35)
  TL = (18.7, 43.35)
```

---

# 71. Relationship to Component 1

Component 1 produces:

```text
"The patch is centered on the substrate."
```

Component 1 converts that into:

```text
CENTER_X(patch, substrate)
CENTER_Y(patch, substrate)
```

Component 2 converts those constraints into:

```text
(patch_x_left + patch_x_right)/2
=
(substrate_x_left + substrate_x_right)/2

(patch_y_bottom + patch_y_top)/2
=
(substrate_y_bottom + substrate_y_top)/2
```

Component 2 solves them.

This separation is critical.

Component 1 says:

```text
WHAT THE PAPER STATES
```

Component 2 says:

```text
WHAT THOSE STATEMENTS MATHEMATICALLY IMPLY
```

Component 3 says:

```text
HOW TO REPRESENT THE RESULT AS GEOMETRY/CAD
```

---

# 72. Critical Rules

The following rules are mandatory.

## Rule 1

**Never guess missing geometry.**

## Rule 2

**Never infer a relationship that is not present in Geometry IR.**

## Rule 3

**Never silently resolve conflicting information.**

## Rule 4

**Never use image pixels as the primary coordinate source.**

## Rule 5

**Never use an LLM as the mathematical solver.**

## Rule 6

**Never silently choose between multiple mathematical solutions.**

## Rule 7

**Never discard provenance.**

## Rule 8

**Never generate CAD in Component 2.**

## Rule 9

**Every calculated coordinate must be reproducible from explicit equations and inputs.**

## Rule 10

**If the geometry cannot be uniquely determined, report that fact instead of inventing geometry.**

---

# 73. Final Responsibility Boundary

```text
                    COMPONENT 1
             Geometry Understanding
                       |
                       | Geometry IR
                       v
              +------------------+
              | COMPONENT 2      |
              |                  |
              | Variables        |
              | Parameters       |
              | Constraints      |
              | Equations        |
              | Solver           |
              | Validation       |
              | Derivations      |
              +------------------+
                       |
                       | Resolved Geometry
                       v
                    COMPONENT 3
                  Geometry / CAD
```

The core principle is:

> **Component 1 extracts facts and relationships.**
>
> **Component 2 mathematically resolves those facts and relationships.**
>
> **Component 3 constructs the resulting geometry.**

Component 2 is successful only when its output can be explained entirely through deterministic mathematical derivations from the Geometry IR.
