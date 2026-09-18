# Antenna Reconstruction

Reconstructs exact antenna geometry from research papers, deterministically and
traceably. Dimensions come from what the paper states; coordinates come from
solving equations; anything the paper does not determine is **reported as
undetermined rather than guessed**.

## Two pipelines

**`template_pipeline.TemplatePipeline`** — the path that works on real papers.

```text
PDF --> tables + prose + derived --> template match --> BINDING VERIFICATION --> geometry --> DXF
                                                                |
                                                          refuted? stop.
```

Dimensions are read from parameter tables where they exist and from running
text where they do not, and a third source computes what a paper implies but
never prints. Authority runs tables > prose > derived: a printed value always
beats one this code worked out.

**Derived quantities.** The array paper states only "Distance between patches is
kept as lambda/2" - but it also states a 2.4 GHz centre frequency, and a
wavelength follows by definition. `derived/physics.py` computes it
(`lambda0 = c/f = 124.91 mm`, so spacing = 62.46 mm) and carries the formula and
inputs with the value, so a computed number is never mistaken for a stated one.
Where a paper quotes many frequencies and marks none as its design frequency,
nothing is derived.

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
| rectangular_patch_array | table headers + derived | rectangular_patch_array | yes | **yes** (2/2) |
| square_patch_antenna | prose | — | no | contested symbols |
| synthetic_antenna | — | — | no | no planar geometry stated |

The two failures are honest. `square_patch_antenna` describes three design
variants and assigns `L` five different values, so its symbols are dropped
rather than guessed; `synthetic_antenna` states only a substrate thickness.
Per-paper outcomes are pinned in `tests/test_papers_end_to_end.py` so a
regression in coverage fails the suite.

For `hexagonal_ring_antenna` every part of Fig. 2 is now reconstructed and
nothing is left undetermined. Reaching that took reading the figure against the
table and correcting three mistakes, which is worth recording:

- **`F1` is metal, not a gap.** It was modelled as a split that cut the inner
  ring open. The paper calls it the "thickness of stub feed": it is the width
  of the narrow bar joining the inner arc down to the feed.
- **The inner structure is not a closed ring.** Fig. 2 shows only the lower
  three hexagon edges, terminating at the left and right vertices.
- **The tapered ground is determined after all.** Each side is a right triangle
  with its apex at the substrate's bottom outer corner, a vertical inner edge
  of height `GL` standing `G1` clear of the feed, and a base of exactly `W1`.
  It had been reported as needing two more values.

The measurements that settle these are checked against Table 1 in
`tests/test_templates.py`. Compare for yourself:

```bash
python examples/render_all_comparisons.py
```

That script renders every paper's own figure beside what the pipeline builds.
Run it for each new template: it is the only check that catches a wrong
*shape*, as opposed to wrongly bound *numbers*.

## Shape vocabulary

| template | symbols | verified by |
|---|---|---|
| `hexagonal_ring_cpw_monopole` | `L W S1..S4 H1 H2 F1 FW FL G1 GL W1` | 3 relations |
| `rectangular_patch` | `W L` + optional `SW SL FW FI FG FL` | inset feed length |
| `circular_patch` | `R` + optional `D` | `D = 2R` |
| `annular_ring` | `RO RI` + optional `WR` | `WR = RO - RI` |
| `triangular_patch` | `ST` + optional `HT` | `HT = ST*sqrt(3)/2` |
| `rectangular_patch_array` | `W L NX NY DX DY` | spacing clears the element |
| `trimmed_square_patch` | `W2 L2 W3 L3` + optional `W1 L1` | square, and symmetric trim |
| `horse_shoe_patch` | `L_S W L_P W_P L_g W_f L_f` | containment bounds only |

Curves are emitted as 180-segment polylines (chord error under ~0.02% of the
radius), giving CAD and EM consumers one uniform representation.

```bash
python examples/render_shape_gallery.py
```

## Reading tables

Parameter tables are read from **word coordinates**, not from a detected cell
grid. That is not a preference - the grid parser is structurally unable to read
some real layouts. On a four-column
`Parameter | Value | Parameter | Value` table, pdfplumber returned only the
right-hand half, so the left *value* column was paired with the right
*parameter* column and **all seven recovered symbols carried another symbol's
number**, with nothing to signal it. Reading the header's own x positions makes
that impossible: a value can only pair with the symbol printed beside it. The
same pass folds in typeset subscripts, where `L` sits above `SII` to mean
`L_SII`.

A table must also declare a length unit. Defaulting to mm let a
machine-learning results table - model names against resonant frequencies in
GHz - be read as antenna dimensions.

## Layout

```text
src/antenna_reconstruction/
  geometry_extraction/     Component 1 - evidence -> GeometryIR
    ingestion/pdf.py         structure-preserving PDF + table extraction
    ingestion/word_tables.py parameter tables rebuilt from word coordinates
    ingestion/prose.py       dimensions stated in running text
  coordinate_engine/       Component 2 - SymPy constraint solving (no LLM)
  cad_builder/             Component 3 - geometry -> DXF, layer-aware
  geometry/primitives.py   polygons, uniform insets, boolean difference
  geometry/feeds.py        microstrip lines and inset feeds
  derived/physics.py       quantities a paper implies but never prints
  binding/verifier.py      the propose-then-verify engine
  templates/               parametric antenna families (8 shapes)
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

148 tests. `tests/test_no_silent_success.py` pins the regression that motivated
this design: the pipeline used to return success with an empty DXF.
`tests/test_papers_end_to_end.py` pins what each sample paper should produce.
