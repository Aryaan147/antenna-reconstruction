# Visual-Guided Parameter Resolution & Reconstruction Integration

## 1. Purpose

Extend the existing antenna reconstruction pipeline so visual evidence identifies antenna features and provides geometric constraints, while the existing base-pipeline parameter generation and reconstruction logic remains responsible for numerical parameters.

**Do not create a second independent Parameter Engine.**

Reuse and extend:

- `src/antenna_reconstruction/visual_completion/geometry/constructor.py`
- `src/antenna_reconstruction/visual_completion/geometry/rules.py`
- `src/antenna_reconstruction/derived/physics.py`

Target flow:

```text
VLM identification
        ↓
Figure geometry / dimension evidence
        ↓
Existing constructor + rules
        ↓
Resolved parameters
        ↓
Existing templates
        ↓
DXF
```

---

## 2. Problem

The visual reconciliation layer can correctly detect features missing from text.

Example:

```text
Text:   feed = center
Figure: feed = inset
```

The system correctly identifies the inset feed, but its dimensions may be inaccurate when the VLM is responsible for predicting them.

The VLM must therefore stop being the source of final numerical predictions.

The existing parameter-generation system should receive better visual evidence instead.

---

## 3. Responsibility Split

### VLM

Responsible for:

- feature identification
- topology identification
- feed type
- slot/hole/cutout/taper identification
- visible dimension labels
- association of labels with features
- qualitative geometric relationships

It must **not invent numerical dimensions**.

### Figure Geometry Evidence

Responsible for:

- pixel coordinates
- line positions
- bounding boxes
- measured distances
- ratios
- dimension-line endpoints
- geometric relationships

### Existing Parameter Engine

Use:

```text
visual_completion/geometry/constructor.py
visual_completion/geometry/rules.py
derived/physics.py
```

for deterministic numerical resolution.

---

## 4. Target Architecture

```text
              PAPER
                │
       ┌────────┴────────┐
       │                 │
   TEXT/TABLE          FIGURE
       │                 │
       │                VLM
       │                 │
       │       feature/topology
       │       + explicit labels
       │                 │
       └────────┬────────┘
                ▼
       Evidence Reconciliation
                │
                ▼
      Figure Geometry Evidence
                │
                ▼
 Existing Constructor + Rules
                │
                ▼
       Resolved Parameters
                │
                ▼
       Existing Templates
                │
                ▼
               DXF
```

---

## 5. Existing Components to Reuse

### Physics

`derived/physics.py`

Continue using existing deterministic physics derivations such as wavelength and guided wavelength.

### Geometry Constructor

`visual_completion/geometry/constructor.py`

This remains the central numerical resolution component.

It already supports:

- explicit visible dimensions
- proportional estimates
- current parameter values
- deterministic rules
- resolved parameters
- derivation metadata
- unresolved parameters

Extend it rather than creating another engine.

### Rules

`visual_completion/geometry/rules.py`

Continue using existing rules such as:

```text
FL = (SL - L) / 2 + FI
```

and proportional derivations.

Do not add arbitrary antenna formulas merely to make a reconstruction fit.

### Templates

Continue using:

```text
template_pipeline.py
templates/
```

Resolved parameters must flow into the existing template system.

---

## 6. VLM Contract

The VLM output should contain visual evidence, not predicted final dimensions.

Allowed:

```json
{
  "features": [
    {
      "feature_type": "inset_feed",
      "status": "CONFIRMED",
      "confidence": 0.96
    }
  ],
  "dimension_annotations": [
    {
      "label": "FI",
      "text": "3.2",
      "feature": "inset_feed"
    }
  ]
}
```

The `3.2` value is acceptable only when it is actually visible/readable in the figure.

Forbidden:

```json
{
  "FI": 2.8
}
```

when 2.8 is merely a VLM estimate.

---

## 7. Evidence Provenance

Numerical values must retain provenance:

```text
EXPLICIT_TEXT
EXPLICIT_TABLE
EXPLICIT_FIGURE_DIMENSION
FIGURE_MEASURED
GEOMETRICALLY_ESTIMATED
ENGINEERING_INFERRED
CONFLICTING
UNKNOWN
```

Examples:

```text
FI = 3.2
source = EXPLICIT_FIGURE_DIMENSION
```

versus:

```text
FI = 3.18
source = FIGURE_MEASURED
```

Do not silently convert one evidence type into another.

---

## 8. Topology Must Be Independent From Dimensions

Valid state:

```text
feed.type = inset
FI = UNKNOWN
FG = UNKNOWN
FW = UNKNOWN
```

This means:

> The feature is known, but its numerical parameters are unresolved.

It must never mean that the feature disappears.

Therefore:

```text
feature presence
```

and:

```text
parameter resolution
```

must remain separate.

---

## 9. Center-vs-Inset Regression Case

Input:

```text
TEXT:
feed = center

FIGURE:
visible inset feed
```

Expected reconciliation:

```text
feed.type
status = CONFLICTING
text = center
figure = inset
```

The visual topology must survive reconciliation.

If the figure explicitly gives:

```text
FI
FG
FW
```

those values enter the constructor as explicit figure evidence.

If they are missing, the constructor receives the visual constraints and attempts deterministic resolution.

The system must not silently fall back to center/edge feed.

---

## 10. Figure Geometry Evidence

Implement the smallest reliable layer necessary to turn figure information into constraints for the existing constructor.

It should convert:

```text
figure pixels
        ↓
geometric evidence
```

not:

```text
figure pixels
        ↓
complete antenna parameter set
```

Possible evidence:

```json
{
  "measurements": [
    {
      "parameter": "FI",
      "pixel_value": 84,
      "reference": "inset_depth"
    }
  ],
  "ratios": [
    {
      "parameter": "FG",
      "relative_to": "FW",
      "ratio": 0.48
    }
  ]
}
```

---

## 11. Explicit Figure Dimensions

If a label is visible:

```text
FI = 3 mm
```

store:

```text
parameter = FI
value = 3.0
source = EXPLICIT_FIGURE_DIMENSION
```

Do not route explicit labels through a prediction/estimation path.

---

## 12. Figure Measurements

If no physical value is labelled but geometry is measurable:

```text
inset depth = 84 px
patch length = 420 px
```

derive:

```text
FI / L = 84 / 420
```

If:

```text
L = 40 mm
```

then:

```text
FI = 40 × (84 / 420)
   = 8 mm
```

Mark this as geometrically estimated.

Never treat raw pixels as millimetres without a physical reference.

---

## 13. Constructor Integration

Extend the existing constructor minimally.

Conceptually:

```python
construct_geometry(
    request,
    visual_constraints=...
)
```

The constructor receives:

```text
current parameters
+
missing parameters
+
explicit figure dimensions
+
geometric measurements
+
proportional constraints
+
resolved topology
```

It then applies existing rules.

Example:

```text
SL = 40
L = 30
FI = 5

FL = (SL - L)/2 + FI
   = 10
```

This calculation belongs to the existing constructor/rules system, not the VLM.

---

## 14. Numerical Resolution Order

Use this conceptual order:

```text
1. Explicit text/table parameters
2. Explicit figure dimensions
3. Deterministic figure measurements
4. Existing proportional rules
5. Existing physics-derived rules
6. Geometric fitting/optimization if necessary
7. Unresolved
```

This is a numerical evidence order.

It is **not** a universal topology authority hierarchy.

For example:

```text
text = center
figure = inset
```

must preserve the topology conflict rather than blindly selecting text.

---

## 15. No Unsupported Engineering Guessing

Do not introduce arbitrary rules such as:

```text
FI = 0.25 × L
```

unless supported by:

- an existing project rule,
- measured figure geometry,
- a documented design relationship,
- or controlled optimization.

---

## 16. Optimization Fallback

If deterministic rules cannot fully resolve missing parameters but the figure provides sufficient geometry, add a fitting stage.

Conceptual flow:

```text
candidate parameters
        ↓
existing template
        ↓
generated geometry
        ↓
compare with figure evidence
        ↓
geometry error
        ↓
optimize parameters
```

Reuse the existing template system.

Do not create a second antenna geometry generator.

Optimization comes only after deterministic evidence and existing rules have been exhausted.

---

## 17. Reconstruction Boundary

Preserve:

```text
parameters
features
```

For example:

```python
ReconstructionInput(
    parameters={
        "W": 30.0,
        "L": 40.0,
        "FI": 5.0,
    },
    features=[
        VisualFeature(
            feature_type="inset_feed",
            status="CONFIRMED"
        )
    ]
)
```

A missing numerical parameter must never delete its associated feature.

---

## 18. Template Integration

Existing templates should receive both parameters and features:

```python
template.build(
    parameters,
    features=features
)
```

A confirmed topology with unresolved dimensions must not silently become another topology.

Example:

```text
inset feed confirmed
FI unknown
```

must not become:

```text
edge feed
```

---

## 19. Final Reconstruction Behavior

The pipeline should attempt the closest supported reconstruction.

Desired flow:

```text
Evidence
  ↓
deterministic derivation
  ↓
geometric constraints
  ↓
existing rules
  ↓
optional fitting
  ↓
template
  ↓
DXF
```

`UNKNOWN` remains a valid internal evidence state, but should not be the first response when usable geometric evidence exists.

---

## 20. Visual Validation

After reconstruction:

```text
DXF
 ↓
render
 ↓
compare with source figure
```

Compare:

- feed topology
- inset location
- patch boundary
- slot/hole/cutout positions
- relative dimensions
- orientation

Example diagnostics:

```text
feed topology: PASS
patch boundary: PASS
inset position: PASS
inset depth: 12% error
inset width: 8% error
```

---

## 21. Required Tests

### Test 1 — Figure identifies inset feed

Text says center; figure shows inset.

Expected:

```text
inset_feed
```

with no silent center-feed fallback.

### Test 2 — Explicit inset dimensions

Figure contains:

```text
FI = 5 mm
FG = 2 mm
FW = 3 mm
```

Expected values and provenance:

```text
EXPLICIT_FIGURE_DIMENSION
```

### Test 3 — Unlabelled measurable inset

Expected geometrically estimated value with appropriate provenance.

### Test 4 — Figure-only feature survives unknown parameters

```text
feature = inset_feed
FI = UNKNOWN
```

Feature must remain.

### Test 5 — Existing constructor derives dependent values

Verify:

```text
FL = (SL-L)/2 + FI
```

using the existing rule.

### Test 6 — Text/figure topology conflict

Preserve both sources and the conflict.

### Test 7 — Multiple dimension sets

Do not overwrite alternative figure dimension sets.

### Test 8 — VLM does not invent dimensions

Feature-only VLM output must not create fake FI/FG/FW.

### Test 9 — Explicit VLM label

A genuinely visible label may enter as `EXPLICIT_FIGURE_DIMENSION`.

### Test 10 — VLM failure

Visual evidence becomes unavailable and the existing text path continues safely.

### Test 11 — End-to-end inset reconstruction

Verify:

```text
paper/text
→ reconciliation
→ visual evidence
→ constructor
→ template
→ DXF
```

produces an inset feed and dimensions closer to the reference figure than the previous implementation.

---

## 22. Diagnostics

Every resolved parameter should expose:

```text
parameter
value
source
confidence
derivation
```

Example:

```text
FI
value: 5.2 mm
source: GEOMETRICALLY_ESTIMATED
derived_from:
    L = 40 mm
    measured FI/L = 0.13
confidence: 0.82
```

Conflicts should expose both sources:

```text
feed.type
text: center
figure: inset
status: CONFLICTING
```

---

## 23. Implementation Sequence

### Step 1

Inspect the actual current implementations of:

```text
visual_completion/pipeline.py
visual_completion/geometry/constructor.py
visual_completion/geometry/rules.py
template_pipeline.py
```

Do not assume the documentation matches the code.

### Step 2

Change the VLM contract to focus on:

```text
feature identification
topology
explicit visible dimension labels
dimension associations
```

### Step 3

Implement/extend figure geometry evidence.

### Step 4

Feed visual constraints into the existing constructor.

### Step 5

Extend `constructor.py` only where necessary.

### Step 6

Preserve parameter provenance.

### Step 7

Pass parameters and topology into existing templates.

### Step 8

Add regression tests.

### Step 9

Run the full test suite.

### Step 10

Run the real inset-feed paper/figure.

---

## 24. Implementation Constraints

Do not:

- create a second Parameter Engine;
- make the VLM predict missing numerical dimensions;
- overwrite figure-only features;
- encode topology as fake floats;
- silently resolve text/figure conflicts;
- invent unsupported antenna formulas;
- bypass the existing template system;
- bypass existing constructor/rules;
- delete provenance;
- silently change confirmed topology because a parameter is unknown.

Do:

- reuse the existing constructor;
- reuse existing rules;
- reuse existing physics derivation;
- reuse existing templates;
- preserve visual evidence;
- preserve provenance;
- add deterministic figure measurements;
- add geometric constraints;
- add optimization only when necessary;
- test the actual inset-feed failure.

---

## 25. Acceptance Criteria

The implementation is complete when:

1. VLM identifies visual topology correctly.
2. VLM does not invent missing dimensions.
3. Explicit figure dimensions are extracted when visible.
4. Figure geometry provides measurable constraints.
5. Existing `constructor.py` and `rules.py` resolve missing parameters where possible.
6. No second independent Parameter Engine exists.
7. Figure-only features survive missing parameters.
8. Text/figure conflicts remain visible.
9. Existing templates receive resolved parameters and topology.
10. The inset-feed regression case produces an inset feed.
11. Numerical dimensions come from evidence/rules/fitting rather than arbitrary VLM guesses.
12. The full existing test suite remains green.
13. The real-paper result is substantially closer to the source figure than the previous implementation.

---

## 26. Final Principle

> **The VLM identifies what is present. The figure provides geometric evidence. The existing parameter engine determines numerical values. The existing template system constructs the antenna.**
