import os
import pytest

from antenna_reconstruction.geometry_extraction.ingestion.prose import (
    extract_prose_parameters, resolve_aliases, to_template_symbols,
)

MICROSTRIP = (
    "The antenna is fabricated on 76.8 X 57.8 mm2 FR-4 substrate with thickness "
    "1.6mm. The patch has dimension on 39.4X28.9mm2 and it is fed by a "
    "microstrip line having width of 3.1mm."
)
REAL_TEXT = "data/raw/extracted_text/microstrip_patch_antenna.txt"


def test_dimension_pairs_get_the_nearest_role():
    extraction = extract_prose_parameters(MICROSTRIP)
    roles = {(p.role, p.a, p.b) for p in extraction.pairs}
    assert ("substrate", 76.8, 57.8) in roles
    # "patch" precedes the numbers while "microstrip line" follows them; the
    # nearer edge must win.
    assert ("patch", 39.4, 28.9) in roles


def test_prose_maps_onto_template_symbols():
    values = to_template_symbols(extract_prose_parameters(MICROSTRIP))
    assert values["SW"] == 76.8 and values["SL"] == 57.8
    assert values["W"] == 39.4 and values["L"] == 28.9
    assert values["FW"] == 3.1


def test_explicit_assignments_are_read():
    values = to_template_symbols(extract_prose_parameters(
        "The dimensions are: L1 = 45 mm, L2 = 30 mm, L3 = 25 mm."
    ))
    assert values == {"L1": 45.0, "L2": 30.0, "L3": 25.0}


def test_symbolic_aliases_are_resolved():
    extraction = extract_prose_parameters("L1 = 45 mm, L2 = 30 mm, W1 = L1")
    assert extraction.aliases["W1"] == "L1"
    assert resolve_aliases(extraction)["W1"] == 45.0


def test_a_symbol_with_several_values_is_dropped_not_guessed():
    extraction = extract_prose_parameters(
        "Antenna (a): L1 = 45 mm. Antenna (b): L1 = 40 mm."
    )
    assert "L1" in extraction.contested
    assert "L1" not in extraction.values
    assert any("dropped" in d for d in extraction.diagnostics)


def test_alias_contradicting_a_direct_value_is_dropped():
    values = to_template_symbols(extract_prose_parameters(
        "L1 = 45 mm, W1 = 40 mm, W1 = L1"
    ))
    assert "W1" not in values


def test_overall_board_size_is_not_taken_for_a_part():
    extraction = extract_prose_parameters(
        "The overall dimension of the antenna is 45 x 45 x 1.6 mm3."
    )
    assert extraction.pairs[0].role == "overall"
    assert to_template_symbols(extraction) == {}


def test_competing_extents_for_one_role_are_refused():
    extraction = extract_prose_parameters(
        "The patch is 30 x 20 mm2. A second patch is 40 x 25 mm2."
    )
    values = to_template_symbols(extraction)
    assert "W" not in values and "L" not in values
    assert any("refusing to choose" in d for d in extraction.diagnostics)


@pytest.mark.skipif(not os.path.exists(REAL_TEXT), reason="extracted text absent")
def test_real_paper_prose_yields_the_published_dimensions():
    values = to_template_symbols(
        extract_prose_parameters(open(REAL_TEXT).read())
    )
    assert values["SW"] == 76.8 and values["SL"] == 57.8
    assert values["W"] == 39.4 and values["L"] == 28.9
