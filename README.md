# Antenna Reconstruction

Reconstructs exact antenna geometry from research papers, deterministically and
traceably. Dimensions come from what the paper states; coordinates come from
solving equations; anything the paper does not determine is **reported as
undetermined rather than guessed**.

## Two pipelines

**`template_pipeline.TemplatePipeline`** — the path that works on real papers.

```text
PDF --> tables + prose --> template match --> BINDING VERIFICATION --> geometry --> DXF
                                                      |
                                                 refuted? stop.
```

Dimensions are read from parameter tables where they exist and from running
text where they do not. Tables outrank prose: a table is an explicit structured
statement, prose is recovered by pattern matching over text a PDF extractor may
have mangled.

**`pipeline.AntennaReconstructionPipeline`** — the original sentence-level path
(Components 1-3: regex extraction, SymPy constraint solving, CAD build). It
works on structured sentences and is kept for the constraint-solving core.

## The central idea: propose, then verify

Deciding what a symbol *means* ("is `S1` the outer hexagon edge?") is the hard
part, and any proposer — a heuristic, a human, an LLM — can get it wrong.

Antenna papers over-specify their geometry, so a correct binding satisfies
arithmetic identities that an incorrect one violates. Every template declares
those identities and they are checked against the paper's own numbers before any
geometry is built. For `data/raw/papers/hexagonal_ring_antenna.pdf`:

| relation | predicted | Table 1 | |
|---|---|---|---|
| `W1 = W/2 − FW/2 − G1` | 9.1000 | 9.1 | CONFIRMED |
| `S2 = S1` inset by `H1` | 5.3453 | 5.3 | CONFIRMED |
| `S3 = S4` inset by `H2` | 4.1826 | 4.2 | CONFIRMED |

These prove the feed is centred and both hexagons are regular — facts nothing in
the text states. Tolerance is derived from how precisely each value was printed
(`5.3` implies ±0.05; `4.76` implies ±0.005), not hard-coded.

A build that no relation could test is reported as `verified=False`:
**unverified is not the same as verified.**

## Quick start

```bash
pip install -e ".[dev,viz]"
```

```bash
python extract.py
```

```bash
python examples/reconstruct_papers.py
```

```bash
python examples/render_reconstruction.py
```

## Current results

| paper | source | template | built | verified |
|---|---|---|---|---|
| hexagonal_ring_antenna | table (14 symbols) | hexagonal_ring_cpw_monopole | yes | **yes** (3/3) |
| microstrip_patch_antenna | prose | rectangular_patch | yes | no (no redundancy) |
| rectangular_patch_array | table headers | rectangular_patch | yes | no (no redundancy) |
| square_patch_antenna | prose | — | no | contested symbols |
| synthetic_antenna | — | — | no | no planar geometry stated |

The two failures are honest. `square_patch_antenna` describes three design
variants and assigns `L` five different values, so its symbols are dropped
rather than guessed; `synthetic_antenna` states only a substrate thickness.
Per-paper outcomes are pinned in `tests/test_papers_end_to_end.py` so a
regression in coverage fails the suite.

Even for the paper that succeeds, the **tapered ground plane is not emitted**:
`GL`, `G1` and `W1` fix its height and inner edge, but nothing in Table 1 gives
the taper's slope or apex. That gap is reported.

## Shape vocabulary

| template | symbols | verified by |
|---|---|---|
| `hexagonal_ring_cpw_monopole` | `L W S1..S4 H1 H2 F1 FW FL G1 GL W1` | 3 relations |
| `rectangular_patch` | `W L` + optional `SW SL` | none available |
| `circular_patch` | `R` + optional `D` | `D = 2R` |
| `annular_ring` | `RO RI` + optional `WR` | `WR = RO - RI` |
| `triangular_patch` | `ST` + optional `HT` | `HT = ST*sqrt(3)/2` |
| `rectangular_patch_array` | `W L NX NY DX DY` | spacing clears the element |

Curves are emitted as 180-segment polylines (chord error under ~0.02% of the
radius), giving CAD and EM consumers one uniform representation.

```bash
python examples/render_shape_gallery.py
```

## Layout

```text
src/antenna_reconstruction/
  geometry_extraction/     Component 1 - evidence -> GeometryIR
    ingestion/pdf.py         structure-preserving PDF + table extraction
    ingestion/prose.py       dimensions stated in running text
  coordinate_engine/       Component 2 - SymPy constraint solving (no LLM)
  cad_builder/             Component 3 - geometry -> DXF, layer-aware
  geometry/primitives.py   polygons, uniform insets, boolean difference
  binding/verifier.py      the propose-then-verify engine
  templates/               parametric antenna families (6 shapes)
  template_pipeline.py     PDF -> DXF
```

## Design rules

Taken from `MD/Idea.md` and enforced by the test suite:

- Stated dimensions outrank pixel measurements; figures are evidence for
  topology and relationships, not for numbers.
- No component silently guesses missing geometry.
- Underdetermined and contradictory inputs are reported, never resolved away.
- An empty result is never reported as success.
- Units are explicit and canonical (mm); geometry generation is deterministic.
- Component 2 never uses an LLM to choose coordinates.

Every assumption a template makes that is *not* provable from the numbers — the
hexagons being flat-top, the ring sitting on the feed — is recorded in
`TemplateResult.assumptions` and printed with the result.

## Adding a template

1. Subclass `Template`; declare `required` / `optional` symbols.
2. Implement `relations()` with every redundancy the family offers. **This is
   the most valuable part** — it is what makes a binding falsifiable.
3. Implement `build()` using `geometry.primitives`; append anything the symbols
   do not determine to `underdetermined`, and any figure-derived choice to
   `assumptions`.
4. Register it in `templates/__init__.py` and render it against the paper's
   figure.

## Tests

```bash
python -m pytest tests -q
```

97 tests. `tests/test_no_silent_success.py` pins the regression that motivated
this design: the pipeline used to return success with an empty DXF.
`tests/test_papers_end_to_end.py` pins what each sample paper should produce.
