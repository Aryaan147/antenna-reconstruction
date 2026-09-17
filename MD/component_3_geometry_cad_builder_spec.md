# Component 3 — Geometry / CAD Builder

## 1. Purpose

Component 3 is the final deterministic geometry-construction layer of the core antenna reconstruction pipeline.

Its job is to take the **Resolved Geometry** produced by Component 2 and construct an explicit geometric/CAD representation that can be consumed by downstream tools.

The fundamental responsibility boundary is:

> **Component 1 understands. Component 2 calculates. Component 3 builds.**

Component 3 does not determine what the antenna geometry should be.

It receives already-resolved geometry and converts it into:

- points;
- line segments;
- rectangles;
- polygons;
- circles;
- arcs;
- geometric regions;
- holes/cutouts;
- Boolean combinations;
- topology;
- layered CAD geometry;
- exportable CAD representations.

The component may export formats such as:

```text
DXF
STEP
SVG
JSON
```

depending on the capabilities required by the project.

The first implementation should prioritize **2D geometry and DXF-compatible output**.

---

# 2. Position in the Pipeline

```text
                       PAPER
                         |
                         v
             +------------------------+
             | COMPONENT 1            |
             | Geometry Understanding |
             +------------------------+
                         |
                         v
                  Geometry IR
                         |
                         v
             +------------------------+
             | COMPONENT 2            |
             | Constraint & Coordinate|
             | Engine                 |
             +------------------------+
                         |
                         v
                Resolved Geometry
                         |
                         v
             +------------------------+
             | COMPONENT 3            |
             | Geometry / CAD Builder |
             +------------------------+
                         |
              +----------+----------+
              |          |          |
              v          v          v
             DXF        STEP       JSON
```

Component 3 is the first component that is allowed to construct actual CAD geometry.

---

# 3. Core Design Principle

Component 3 must be a **dumb, deterministic geometry builder**.

It should not reason about the antenna.

For example, if Component 2 provides:

```text
patch:
BL = (18.7, 14.45)
BR = (58.1, 14.45)
TR = (58.1, 43.35)
TL = (18.7, 43.35)
```

Component 3 simply constructs that rectangle.

It must not ask:

```text
Should this patch be centered?
Should I change its width?
Does this look like a patch antenna?
Should I modify the shape?
```

Those decisions have already been made upstream.

---

# 4. Responsibilities

## 4.1 Component 3 MUST

Component 3 must:

- validate resolved geometry;
- create geometric primitives;
- create topology;
- construct regions;
- perform explicitly requested Boolean operations;
- preserve entity IDs;
- preserve layer/material/component metadata;
- maintain deterministic geometry;
- validate geometric integrity;
- export supported CAD formats;
- provide export diagnostics;
- preserve provenance references from upstream geometry.

## 4.2 Component 3 MUST NOT

Component 3 must not:

- read research papers;
- perform OCR;
- interpret figures;
- extract dimensions;
- solve geometric constraints;
- guess coordinates;
- modify dimensions;
- center objects automatically;
- infer missing geometry;
- use an LLM;
- perform electromagnetic optimization;
- decide antenna topology;
- silently repair invalid geometry.

---

# 5. Input Contract

Component 3 receives the output of Component 2:

```python
resolved_geometry = component2.solve(geometry_ir)

cad_model = component3.build(resolved_geometry)
```

Only successfully resolved geometry should normally be passed to the builder.

Recommended rule:

```text
SOLVED -> build allowed
UNDERDETERMINED -> build rejected
INCONSISTENT -> build rejected
NUMERICALLY_UNRESOLVED -> build rejected
INVALID_INPUT -> build rejected
```

A future explicit partial-geometry mode may be added, but it must not be silently enabled.

---

# 6. Resolved Geometry Example

Input:

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

Component 3 converts this into an internal CAD model.

---

# 7. Internal CAD Model

The internal model should remain independent of a specific CAD library.

Conceptually:

```text
Resolved Geometry
        |
        v
  Internal CAD Model
        |
        +---- DXF adapter
        |
        +---- STEP adapter
        |
        +---- SVG adapter
        |
        +---- JSON adapter
```

This prevents the core geometry representation from being tightly coupled to one exporter.

---

# 8. Geometry Primitives

The initial implementation should support:

```text
Point
LineSegment
Rectangle
Polygon
Circle
Arc
```

Later versions may add:

```text
Polyline
Ellipse
Spline
3D Box
Cylinder
Extrusion
```

---

# 9. Point

A point is:

```text
P = (x, y)
```

Example:

```json
{
  "id": "patch_bl",
  "type": "point",
  "x": 18.7,
  "y": 14.45,
  "unit": "mm"
}
```

A point should have:

- stable ID;
- x;
- y;
- unit;
- metadata/provenance where applicable.

---

# 10. Line Segment

A line segment contains:

```text
start
end
```

Example:

```json
{
  "id": "patch_bottom",
  "type": "line",
  "start": "patch_bl",
  "end": "patch_br"
}
```

The line should reference points where practical rather than duplicating coordinates.

---

# 11. Rectangle

A rectangle should be represented using four ordered vertices:

```text
BL
BR
TR
TL
```

and four edges:

```text
BL -> BR
BR -> TR
TR -> TL
TL -> BL
```

This provides explicit topology.

Example:

```text
Rectangle
  |
  +-- vertices
  |     BL
  |     BR
  |     TR
  |     TL
  |
  +-- edges
        bottom
        right
        top
        left
```

---

# 12. Polygon

A polygon contains an ordered list of vertices.

Example:

```text
P0 -> P1 -> P2 -> P3 -> P0
```

The ordering must be preserved.

The builder must not reorder vertices unless explicitly required by a deterministic normalization operation.

---

# 13. Circle

A circle contains:

```text
center
radius
```

Example:

```json
{
  "id": "via_1",
  "type": "circle",
  "center": [30, 25],
  "radius": 0.5,
  "unit": "mm"
}
```

The radius must be positive.

---

# 14. Arc

An arc should contain:

```text
center
radius
start_angle
end_angle
```

Angles must use a single documented convention.

Initial convention:

```text
degrees
counter-clockwise positive
```

Example:

```text
center = (20, 20)
radius = 5
start_angle = 0°
end_angle = 90°
```

---

# 15. Coordinate System

Component 3 must use the coordinate system supplied by Component 2.

Initial convention:

```text
2D Cartesian
X -> right
Y -> up
unit -> mm
```

The builder must not transform coordinates unless an explicit export adapter requires a documented transformation.

If an exporter requires a coordinate transformation, the transformation must be deterministic and recorded.

---

# 16. Geometry Identity

Every geometry entity must have a stable identifier.

Examples:

```text
substrate
ground_plane
patch
slot_1
slot_2
feed
via_1
via_2
```

The ID must survive:

```text
Component 2
    ->
Component 3
    ->
CAD model
    ->
export
```

where the target format supports metadata.

---

# 17. Metadata

Each entity may carry:

```text
id
name
type
layer
role
material
source_entity_id
provenance
```

Example:

```json
{
  "id": "patch",
  "type": "rectangle",
  "role": "radiating_element",
  "layer": "metal_top",
  "material": "copper"
}
```

Component 3 must not infer `role`, `layer`, or `material`.

These must come from upstream metadata or explicit configuration.

---

# 18. Layers

A CAD model should support named layers.

Example:

```text
substrate
metal_top
metal_bottom
vias
slots
feed
annotations
```

Layer assignment must be explicit.

Example:

```json
{
  "entity": "patch",
  "layer": "metal_top"
}
```

Component 3 must not decide that a component belongs to `metal_top` simply because it is named `patch`.

---

# 19. Material Metadata

Where required, geometry can contain material metadata.

Example:

```text
patch -> copper
ground -> copper
substrate -> FR4
```

However, Component 3 only stores this metadata.

It does not calculate:

```text
permittivity
loss tangent
conductivity
resonance
```

Material metadata belongs to the model representation, not electromagnetic reasoning.

---

# 20. Topology

Topology describes how geometry entities connect.

For a rectangle:

```text
vertices:
  v1
  v2
  v3
  v4

edges:
  e1: v1 -> v2
  e2: v2 -> v3
  e3: v3 -> v4
  e4: v4 -> v1

face:
  f1: e1,e2,e3,e4
```

Explicit topology makes downstream CAD construction more reliable.

---

# 21. Shared Vertices

If two geometry entities share the exact same point, the internal model should preferably reference the same point object.

Example:

```text
patch edge
      |
      v
shared point
      ^
      |
slot edge
```

This avoids tiny coordinate mismatches.

However, shared topology must only be created when the coordinates are actually identical within the configured tolerance.

The builder must not merge nearby points automatically.

---

# 22. Geometric Tolerance

A centralized geometric tolerance must be used.

Example:

```python
GEOMETRY_TOLERANCE = 1e-9
```

The actual value should be configurable.

It must be used consistently for:

- equality checks;
- duplicate-point detection;
- zero-length detection;
- topology checks;
- Boolean preparation;
- export validation.

Do not scatter independent tolerances across modules.

---

# 23. Validation Before Construction

Before building CAD entities, validate:

```text
status == SOLVED
coordinate system exists
units are valid
entity IDs are unique
coordinates are finite
dimensions are positive where required
polygon vertices are valid
circles have positive radius
```

Invalid input must stop construction.

---

# 24. Rectangle Validation

For a rectangle:

```text
width > 0
height > 0
```

For the initial axis-aligned representation:

```text
x_left < x_right
y_bottom < y_top
```

The builder should reject:

```text
x_left == x_right
```

or:

```text
y_bottom == y_top
```

unless a zero-dimensional entity is explicitly supported.

---

# 25. Polygon Validation

A polygon must have enough vertices.

Minimum:

```text
3 vertices
```

The polygon must not contain:

```text
NaN
infinite values
invalid references
```

Self-intersection should be detected where the target geometry operation requires a simple polygon.

Invalid polygons must not silently be repaired.

---

# 26. Circle Validation

Required:

```text
radius > 0
finite center
finite radius
```

A zero-radius circle is invalid for the initial implementation.

---

# 27. Line Validation

A line segment must have:

```text
start != end
```

within the configured tolerance.

A zero-length line should be rejected.

---

# 28. Boolean Operations

Component 3 may support explicit Boolean operations:

```text
UNION
SUBTRACT
INTERSECT
```

Example:

```text
patch
   -
slot
   =
patch_with_slot
```

Boolean operations must be explicitly represented in the input.

Component 3 must never decide that two overlapping shapes should be subtracted.

---

# 29. Boolean Subtraction Example

Suppose:

```text
patch = rectangle
slot = rectangle
```

Input operation:

```text
SUBTRACT(patch, slot)
```

The builder constructs:

```text
patch_region - slot_region
```

Output:

```text
patch_with_slot
```

The resulting topology must remain valid.

---

# 30. Boolean Union Example

Input:

```text
UNION(feed_trace, feed_pad)
```

The builder performs exactly that operation.

It must not automatically union all touching metal entities.

---

# 31. Boolean Intersection

Input:

```text
INTERSECT(A, B)
```

The builder returns the common region.

If the intersection is empty, the result must explicitly report:

```text
EMPTY_RESULT
```

rather than inventing geometry.

---

# 32. Boolean Operation Provenance

A Boolean result should record:

```text
operation
operands
```

Example:

```json
{
  "id": "patch_with_slot",
  "operation": "SUBTRACT",
  "operands": [
    "patch",
    "slot_1"
  ]
}
```

This makes the final geometry traceable.

---

# 33. Geometry Normalization

Before export, the model may perform deterministic normalization.

Allowed examples:

```text
remove exact duplicate vertices
normalize polygon closure
normalize entity ordering
normalize layer ordering
```

Normalization must not alter the intended geometry.

The original geometry and normalized geometry should be distinguishable in diagnostics when necessary.

---

# 34. No Automatic Repair

This is a mandatory rule.

If the input says:

```text
polygon is self-intersecting
```

Component 3 must not silently:

```text
reorder points
remove points
move points
snap points
```

to make it valid.

It must report the problem.

An explicit repair/cleanup mode may be introduced later, but it must be separately specified and opt-in.

---

# 35. CAD Abstraction Layer

The core should define an abstract CAD interface.

Conceptually:

```python
class CADBackend:
    def add_point(...)
    def add_line(...)
    def add_rectangle(...)
    def add_polygon(...)
    def add_circle(...)
    def add_arc(...)
    def boolean_union(...)
    def boolean_subtract(...)
    def boolean_intersect(...)
    def export(...)
```

Concrete backends may implement this interface.

Examples:

```text
DXFBackend
STEPBackend
SVGBackend
```

The core builder should not depend on one file format.

---

# 36. Recommended Libraries

For the first implementation:

```text
Python 3.12+
Shapely
ezdxf
NumPy
```

Potential future 3D/CAD libraries:

```text
CadQuery
pythonocc-core / OpenCascade bindings
```

Library selection is an implementation detail and must not change the responsibility boundaries.

---

# 37. Recommended Project Structure

```text
component3/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── point.py
│   ├── line.py
│   ├── rectangle.py
│   ├── polygon.py
│   ├── circle.py
│   ├── arc.py
│   ├── topology.py
│   └── cad_model.py
│
├── primitives/
│   ├── __init__.py
│   ├── point_factory.py
│   ├── line_factory.py
│   ├── rectangle_factory.py
│   ├── polygon_factory.py
│   ├── circle_factory.py
│   └── arc_factory.py
│
├── boolean/
│   ├── __init__.py
│   ├── union.py
│   ├── subtract.py
│   └── intersect.py
│
├── topology/
│   ├── __init__.py
│   ├── builder.py
│   └── validator.py
│
├── validation/
│   ├── __init__.py
│   ├── input_validator.py
│   └── geometry_validator.py
│
├── exporters/
│   ├── __init__.py
│   ├── dxf.py
│   ├── svg.py
│   └── step.py
│
├── adapters/
│   └── ...
│
└── builder.py
```

---

# 38. Builder API

The main interface should be simple.

Example:

```python
from component3.builder import GeometryBuilder

builder = GeometryBuilder()

result = builder.build(resolved_geometry)
```

The result should contain:

```python
result.status
result.cad_model
result.validation
result.diagnostics
```

Export should be a separate operation:

```python
builder.export(
    result.cad_model,
    format="dxf",
    path="output/antenna.dxf"
)
```

Construction and export should remain separate responsibilities.

---

# 39. Why Construction and Export Are Separate

The builder creates:

```text
CAD Model
```

The exporter creates:

```text
file
```

This allows:

```text
same geometry
   |
   +---- DXF
   +---- SVG
   +---- STEP
   +---- JSON
```

without reconstructing the geometry each time.

---

# 40. Example — Basic Patch

Resolved geometry:

```text
substrate:
BL = (0,0)
BR = (76.8,0)
TR = (76.8,57.8)
TL = (0,57.8)

patch:
BL = (18.7,14.45)
BR = (58.1,14.45)
TR = (58.1,43.35)
TL = (18.7,43.35)
```

Component 3 creates:

```text
Point objects
    |
    +-- substrate corners
    +-- patch corners

Line objects
    |
    +-- substrate edges
    +-- patch edges

Face/region objects
    |
    +-- substrate
    +-- patch
```

The result can then be exported to DXF.

---

# 41. Example — Patch With Slot

Resolved geometry:

```text
patch:
rectangle

slot:
rectangle
```

Boolean instruction:

```text
SUBTRACT(
    patch,
    slot
)
```

Component 3 creates:

```text
patch region
     |
     | subtract
     v
slot region
     |
     v
final patch region
```

The builder does not determine whether the slot should exist.

---

# 42. Example — Circular Via

Input:

```text
via_1:
center = (30,25)
radius = 0.5
```

Component 3 creates:

```text
Circle(
    center=(30,25),
    radius=0.5
)
```

It does not decide whether the via should connect layers.

Layer connectivity, if needed, must already be represented in the input model or handled by a later dedicated layer/connectivity component.

---

# 43. Layered Geometry

For antenna structures, geometry may eventually be organized as:

```text
Layer 0:
substrate

Layer 1:
bottom ground

Layer 2:
top metal

Layer 3:
vias
```

The builder should support a layer model:

```text
CADModel
    |
    +-- Layer
          |
          +-- entities
```

Layer ordering must be explicit.

---

# 44. 2D vs 3D

The first version should remain 2D.

This is intentional.

The immediate objective is:

```text
paper dimensions
        ->
mathematical geometry
        ->
correct 2D CAD
```

3D construction can be added after 2D reconstruction is reliable.

---

# 45. Future 3D Representation

A later version may construct:

```text
substrate thickness
metal thickness
vias
vertical connections
3D solids
```

Example:

```text
2D substrate
     |
     | extrusion
     v
3D substrate solid
```

This should be implemented as a separate extension rather than complicating the first version.

---

# 46. Coordinate Transformations

Component 3 may need transformations for CAD/export.

Supported deterministic transformations may include:

```text
translation
rotation
reflection
scaling
```

However:

```text
scaling
```

must only be used for explicit unit/export conversion.

Component 3 must never scale an antenna to "make it fit."

---

# 47. Unit Handling

Internal geometry should remain in:

```text
mm
```

Exporters may need format-specific unit metadata.

Example:

```text
internal:
76.8 mm

DXF:
unit metadata = millimeters
```

The numeric coordinates must not be changed unless a documented unit conversion is required by the target format.

---

# 48. Export Validation

Before writing an output file, validate:

```text
model is structurally valid
all coordinates are finite
all entities are supported
all references resolve
all polygons are valid
all Boolean results are valid
```

Export should fail with a structured diagnostic if validation fails.

---

# 49. DXF Export

The initial target exporter should be DXF.

The exporter should map internal geometry to appropriate DXF entities.

Example mapping:

```text
Point        -> POINT
LineSegment  -> LINE
Polyline     -> LWPOLYLINE/POLYLINE
Circle       -> CIRCLE
Arc          -> ARC
```

For regions/Boolean results, the exporter should use the appropriate closed boundaries supported by the chosen implementation.

The exporter must preserve:

- coordinates;
- layer;
- entity identity where possible through supported metadata or mapping;
- units.

---

# 50. DXF Output Goal

Given:

```text
substrate
patch
slot
feed
```

the exported DXF should contain the exact resolved geometry.

The DXF must not contain geometry that was:

```text
guessed
centered automatically
rescaled arbitrarily
redrawn from the image
```

---

# 51. SVG Export

SVG may be used as a convenient visual debugging format.

Example:

```text
Resolved Geometry
       |
       v
      SVG
       |
       v
Browser visualization
```

This is useful for checking whether Component 3 constructed the geometry correctly.

SVG should not be used to determine geometry.

---

# 52. JSON Geometry Export

A JSON exporter should preserve the complete internal model.

Example:

```json
{
  "unit": "mm",
  "entities": [
    {
      "id": "patch",
      "type": "rectangle",
      "vertices": [
        [18.7, 14.45],
        [58.1, 14.45],
        [58.1, 43.35],
        [18.7, 43.35]
      ]
    }
  ]
}
```

This format is useful for debugging and regression tests.

---

# 53. STEP Export

STEP should be considered a later capability.

It becomes important when the pipeline needs:

```text
3D solids
mechanical CAD
manufacturing geometry
```

Do not make STEP a dependency for the first 2D implementation.

---

# 54. Geometry Comparison

Component 3 should provide a deterministic geometry comparison utility.

Example:

```python
compare(model_a, model_b)
```

It should report:

```text
same topology
same coordinates
same dimensions
same entity IDs
same layers
```

within configured tolerance.

This is useful for regression testing.

---

# 55. Round-Trip Testing

For supported formats, test:

```text
internal geometry
       |
       v
export
       |
       v
re-import
       |
       v
compare
```

The imported representation should preserve geometry within the documented tolerance.

Round-trip testing is especially useful for DXF.

---

# 56. Deterministic Entity Ordering

Exports should use deterministic ordering.

For example:

```text
sort by:
1. layer
2. entity type
3. entity ID
```

or another explicitly defined stable ordering.

The exact ordering should be centralized.

This prevents unnecessary differences between repeated exports.

---

# 57. No Randomness

Component 3 must contain no uncontrolled randomness.

Identical input must result in:

```text
identical internal geometry
identical topology
identical export geometry
```

where the target file format permits deterministic serialization.

---

# 58. Error Model

Example:

```json
{
  "code": "INVALID_POLYGON",
  "entity_id": "slot_1",
  "message": "Polygon contains self-intersection."
}
```

Possible error codes:

```text
INVALID_RESOLVED_GEOMETRY
UNKNOWN_ENTITY
DUPLICATE_ENTITY_ID
INVALID_POINT
INVALID_LINE
INVALID_RECTANGLE
INVALID_POLYGON
INVALID_CIRCLE
INVALID_ARC
INVALID_LAYER
INVALID_BOOLEAN_OPERATION
BOOLEAN_EMPTY_RESULT
TOPOLOGY_ERROR
UNSUPPORTED_GEOMETRY
EXPORT_ERROR
UNIT_ERROR
```

---

# 59. Build Result

A successful build may return:

```json
{
  "status": "BUILT",

  "model": {
    "entity_count": 12,
    "layers": [
      "substrate",
      "metal_top"
    ]
  },

  "validation": {
    "passed": true
  },

  "diagnostics": []
}
```

A failed build:

```json
{
  "status": "BUILD_FAILED",

  "validation": {
    "passed": false
  },

  "diagnostics": [
    {
      "code": "INVALID_POLYGON",
      "entity_id": "slot_1"
    }
  ]
}
```

---

# 60. Provenance

Component 3 should preserve upstream provenance.

Example:

```text
patch CAD entity
    |
    +-- source entity: patch
    +-- Component 2 derivation: coordinates
    +-- Component 1 source: paper page/figure
```

The CAD exporter may not support all provenance metadata.

Therefore, the system should maintain a separate model-level provenance mapping when required.

---

# 61. Important Distinction: Geometry vs CAD

Resolved Geometry:

```text
mathematical representation
```

CAD Model:

```text
constructed geometric representation
```

CAD File:

```text
serialized external representation
```

These are three different layers.

```text
Resolved Geometry
       |
       v
CAD Model
       |
       v
DXF / STEP / SVG
```

Keeping these layers separate makes debugging much easier.

---

# 62. Debug Visualization

Component 3 should provide a debug visualization option.

For example:

```text
substrate boundary
patch
slot
feed
vias
```

can be rendered to SVG or another simple visual representation.

This visualization is for:

```text
checking the output
```

not:

```text
determining the output
```

---

# 63. Test Strategy

Component 3 should initially use manually constructed Resolved Geometry fixtures.

Recommended structure:

```text
tests/
├── fixtures/
│   ├── rectangles/
│   ├── polygons/
│   ├── circles/
│   ├── booleans/
│   ├── layers/
│   └── antenna_examples/
│
├── test_points.py
├── test_lines.py
├── test_rectangles.py
├── test_polygons.py
├── test_circles.py
├── test_topology.py
├── test_booleans.py
├── test_validation.py
├── test_dxf.py
├── test_svg.py
└── test_roundtrip.py
```

---

# 64. Minimum Test Cases

## Test 1 — Point

Input:

```text
P = (10,20)
```

Expected:

```text
point exists at (10,20)
```

---

## Test 2 — Rectangle

Input:

```text
BL = (0,0)
BR = (100,0)
TR = (100,50)
TL = (0,50)
```

Expected:

```text
4 vertices
4 edges
1 closed region
```

---

## Test 3 — Polygon

Input:

```text
(0,0)
(50,0)
(40,20)
(0,30)
```

Expected:

```text
valid polygon
```

---

## Test 4 — Circle

Input:

```text
center = (20,20)
radius = 5
```

Expected:

```text
valid circle
```

---

## Test 5 — Boolean subtraction

Input:

```text
outer rectangle
inner rectangle
SUBTRACT
```

Expected:

```text
region with hole
```

---

## Test 6 — Invalid rectangle

Input:

```text
BL = (0,0)
BR = (0,0)
```

Expected:

```text
BUILD_FAILED
```

---

## Test 7 — Duplicate IDs

Input:

```text
entity_1
entity_1
```

Expected:

```text
BUILD_FAILED
```

---

## Test 8 — DXF

Build a simple rectangle and export it.

Expected:

```text
DXF file exists
geometry is preserved
```

---

# 65. Integration Test With Component 2

The first full core integration test should be:

```text
Geometry IR
      |
      v
Component 2
      |
      v
Resolved Geometry
      |
      v
Component 3
      |
      v
CAD Model
      |
      v
DXF
```

For the simple centered patch:

```text
substrate = 76.8 × 57.8
patch = 39.4 × 28.9
centered
```

Component 2 calculates:

```text
patch BL = (18.7,14.45)
patch BR = (58.1,14.45)
patch TR = (58.1,43.35)
patch TL = (18.7,43.35)
```

Component 3 must reproduce those exact coordinates in the CAD model.

---

# 66. First Implementation Scope

Version 1 should support only:

```text
2D
mm
points
line segments
axis-aligned rectangles
polygons
circles
basic topology
explicit Boolean subtraction
explicit Boolean union
basic validation
DXF export
JSON export
SVG debug export
```

Do not implement:

```text
3D solids
complex splines
advanced CAD constraints
automatic healing
automatic geometry optimization
EM simulation
```

until the 2D system is stable.

---

# 67. Development Sequence

Follow this order.

## Phase 1 — Internal Models

Implement:

```text
Point
LineSegment
Rectangle
Polygon
Circle
Arc
```

## Phase 2 — CAD Model

Implement:

```text
CADModel
Layer
Entity registry
Metadata
```

## Phase 3 — Validation

Implement:

```text
input validation
primitive validation
topology validation
```

## Phase 4 — Primitive Builder

Implement:

```text
point factory
line factory
rectangle factory
polygon factory
circle factory
```

## Phase 5 — Topology

Implement:

```text
vertices
edges
faces
shared references
```

## Phase 6 — Boolean Operations

Implement:

```text
SUBTRACT
UNION
INTERSECT
```

only as explicitly requested.

## Phase 7 — Export

Implement:

```text
JSON
SVG
DXF
```

in that order.

## Phase 8 — Regression Tests

Compare:

```text
expected geometry
vs
constructed geometry
```

## Phase 9 — Component 2 Integration

Use real `Resolved Geometry` output.

## Phase 10 — Antenna Fixtures

Use simple antenna structures:

```text
substrate
ground
patch
slot
feed
via
```

---

# 68. First Antenna Fixture

The first antenna-specific fixture should remain extremely simple.

Input:

```text
substrate:
76.8 × 57.8 mm

patch:
39.4 × 28.9 mm

patch:
centered
```

Component 2 produces:

```text
substrate rectangle
patch rectangle
```

Component 3 produces:

```text
CAD model
```

Expected:

```text
two valid rectangles
```

No slot, feed, Boolean operations, or 3D should be introduced in the first integration test.

---

# 69. Second Antenna Fixture

After the first fixture works:

```text
substrate
patch
rectangular slot
```

Component 2 resolves all coordinates.

Component 3 receives:

```text
patch
slot
```

and an explicit:

```text
SUBTRACT(patch, slot)
```

operation.

Expected result:

```text
patch with slot
```

---

# 70. Third Antenna Fixture

Then add:

```text
feed line
```

Example:

```text
patch
    |
    +---- feed line
```

The feed line should be built from its resolved coordinates.

Component 3 must not decide where the feed goes.

---

# 71. Fourth Antenna Fixture

Then add:

```text
via
```

represented initially as a circle in the 2D model.

Later, if layer connectivity is required, extend the model to represent:

```text
via geometry
+
layer span
+
connectivity
```

Do not introduce full 3D merely to represent the first via test.

---

# 72. Component 3 and Images

Component 3 must not use the original paper figure to construct geometry.

The image can be used externally for:

```text
visual comparison
```

Example:

```text
paper figure
      |
      | visual comparison only
      v
generated SVG
```

The generated geometry must originate from:

```text
Component 2
```

not from image tracing.

---

# 73. Visual Verification

A useful validation workflow is:

```text
Paper figure
     |
     | reference only
     v
Generated geometry visualization
```

A human can visually inspect:

```text
shape
relative placement
number of components
```

but the geometry itself must remain mathematically generated.

Visual mismatch should lead to investigation of:

```text
Component 1 extraction
or
Component 2 constraints/solution
or
Component 3 construction
```

not immediate manual editing of the CAD output.

---

# 74. No Manual Coordinate Editing

Once Component 2 has produced resolved geometry, Component 3 must not have a manual correction step such as:

```text
move patch 2 mm left
```

unless that change is represented upstream as a new explicit constraint.

Otherwise the pipeline loses mathematical traceability.

---

# 75. Debugging a Wrong Geometry

If the generated CAD looks wrong:

### Step 1

Inspect Component 1:

```text
Did the paper information become correct Geometry IR?
```

### Step 2

Inspect Component 2:

```text
Did the constraints produce correct coordinates?
```

### Step 3

Inspect Component 3:

```text
Did the coordinates get constructed correctly?
```

Do not immediately modify Component 3.

---

# 76. Failure Isolation

The architecture should make it possible to classify failures.

Example:

```text
Wrong dimension
    -> Component 1

Correct dimension, wrong coordinate
    -> Component 2

Correct coordinate, wrong CAD shape
    -> Component 3

Correct CAD, wrong DXF
    -> Exporter
```

This is one of the main reasons the components must remain separate.

---

# 77. Deterministic Build Contract

For identical:

```text
Resolved Geometry
configuration
backend version
```

Component 3 must produce the same:

```text
internal CAD model
topology
geometry
```

and, where supported by the file format:

```text
deterministic export
```

---

# 78. Acceptance Criteria

Component 3 is considered complete for Version 1 when:

- Resolved Geometry is validated before construction.
- Stable entity IDs are preserved.
- Points are constructed correctly.
- Lines are constructed correctly.
- Rectangles are constructed correctly.
- Polygons are constructed correctly.
- Circles are constructed correctly.
- Basic topology is maintained.
- Explicit Boolean operations work.
- Invalid geometry is rejected.
- No automatic geometry repair occurs.
- No coordinates are guessed.
- No dimensions are changed.
- No LLM is used.
- No paper/image processing is used.
- JSON export works.
- SVG debug export works.
- DXF export works.
- Exported coordinates match resolved coordinates within tolerance.
- Geometry comparison tests pass.
- Component 2 integration works.
- A simple antenna geometry can be reconstructed end-to-end.

---

# 79. Full Core Responsibility Boundary

```text
                 PAPER
                   |
                   v
        +----------------------+
        | COMPONENT 1          |
        |                      |
        | Understand paper     |
        | Extract geometry     |
        | Create Geometry IR   |
        +----------+-----------+
                   |
                   v
             GEOMETRY IR
                   |
                   v
        +----------------------+
        | COMPONENT 2          |
        |                      |
        | Variables            |
        | Constraints          |
        | Equations            |
        | Solve                |
        | Validate             |
        | Derive coordinates   |
        +----------+-----------+
                   |
                   v
           RESOLVED GEOMETRY
                   |
                   v
        +----------------------+
        | COMPONENT 3          |
        |                      |
        | Build primitives     |
        | Build topology       |
        | Boolean operations   |
        | Build CAD model      |
        | Export               |
        +----------+-----------+
                   |
          +--------+--------+
          |        |        |
          v        v        v
         DXF      SVG      STEP
```

---

# 80. Final Rules

## Rule 1

**Component 3 builds what Component 2 gives it.**

## Rule 2

**Component 3 must never guess coordinates.**

## Rule 3

**Component 3 must never change dimensions.**

## Rule 4

**Component 3 must never interpret the paper.**

## Rule 5

**Component 3 must never trace the image to generate geometry.**

## Rule 6

**Boolean operations must be explicitly requested.**

## Rule 7

**Invalid geometry must be reported, not silently repaired.**

## Rule 8

**Construction and export must remain separate layers.**

## Rule 9

**Entity IDs and provenance must be preserved.**

## Rule 10

**The generated CAD must be mathematically traceable back to Component 2.**

---

# 81. Final Architecture

The complete reconstruction core is:

```text
                    RESEARCH PAPER
                          |
                          v
             ┌─────────────────────────┐
             │ COMPONENT 1             │
             │ Geometry Understanding  │
             │                         │
             │ "What does the paper    │
             │  state?"                │
             └────────────┬────────────┘
                          |
                          v
                    Geometry IR
                          |
                          v
             ┌─────────────────────────┐
             │ COMPONENT 2             │
             │ Constraint & Coordinate │
             │ Engine                  │
             │                         │
             │ "What coordinates do    │
             │  those facts imply?"    │
             └────────────┬────────────┘
                          |
                          v
                  Resolved Geometry
                          |
                          v
             ┌─────────────────────────┐
             │ COMPONENT 3             │
             │ Geometry / CAD Builder  │
             │                         │
             │ "How do we construct    │
             │  those coordinates as   │
             │  geometry?"             │
             └────────────┬────────────┘
                          |
                          v
                 CAD / Geometry Files
```

The core architecture therefore remains:

> **UNDERSTAND → CALCULATE → BUILD**

Component 3 is the final stage of the mathematical reconstruction core, not the stage where engineering decisions are made.
