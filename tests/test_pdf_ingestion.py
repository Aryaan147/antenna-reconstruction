import os
import pytest

from antenna_reconstruction.geometry_extraction.ingestion.pdf import (
    RawTable, extract_pdf, normalize_symbol, parse_header_symbol,
    parse_parameter_table,
)

PAPER = "data/raw/papers/hexagonal_ring_antenna.pdf"


@pytest.mark.parametrize("raw,expected", [
    ("S1", "S1"), ("S 1", "S1"), ("S_1", "S1"), ("FW", "FW"), ("W", "W"),
    ("Return loss in dB", None), ("", None), ("12", None),
])
def test_symbol_normalisation(raw, expected):
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize("header,expected", [
    ("Patch width W (mm)", ("W", "mm")),
    ("L(mm)", ("L", "mm")),
    ("S11 (dB)", None),      # a results column, not geometry
    ("Gain (dB)", None),
    ("HPBW (deg)", None),
])
def test_header_symbols_require_a_length_unit(header, expected):
    assert parse_header_symbol(header) == expected


def test_results_table_is_not_mistaken_for_a_parameter_table():
    table = RawTable(page=1, index=0, rows=[
        ["Antenna Parameters", "Trimmed square", "Edge feed"],
        ["Return loss in dB", "-18.9", "-19.6"],
        ["Gain in dB", "3.28", "2.88"],
    ])
    assert parse_parameter_table(table) is None


def test_key_value_parameter_table_is_parsed():
    table = RawTable(page=1, index=0, rows=[
        ["Parameters", "Dimensions (mm)"],
        ["L", "20"], ["W", "20"], ["S1", "6.5"], ["H1", "1"],
    ])
    parsed = parse_parameter_table(table)
    assert parsed is not None
    assert parsed.unit == "mm"
    assert parsed.values == {"L": 20.0, "W": 20.0, "S1": 6.5, "H1": 1.0}
    assert parsed.provenance["S1"]["row"] == 3


@pytest.mark.skipif(not os.path.exists(PAPER), reason="paper PDF not available")
def test_real_paper_table_survives_extraction():
    """pypdf flattened this table into unusable text; pdfplumber must not."""
    doc = extract_pdf(PAPER)
    values = doc.merged_parameters()

    assert len(values) == 14
    assert values["L"] == 20.0 and values["W"] == 20.0
    assert values["S1"] == 6.5 and values["S4"] == 4.76
    assert values["W1"] == 9.1
    # Provenance must point back at a real table cell.
    pt = doc.parameter_tables[0]
    assert pt.provenance["S1"]["page"] >= 1


def test_a_table_with_no_length_unit_is_not_a_parameter_table():
    """Regression: a machine-learning results table - model names against
    resonant frequencies in GHz - was read as antenna dimensions because the
    unit defaulted to mm when none was declared."""
    table = RawTable(page=1, index=0, rows=[
        ["Model", "f (GHz)", "eta", "SAR(W/Kg)"],
        ["ANN", "3.297195", "0.9567030", "0.35847158"],
        ["GPR", "3.10019433", "0.98", "0.31"],
        ["SVR", "3.09318565", "0.96", "0.33"],
    ])
    assert parse_parameter_table(table) is None


def test_column_headers_are_not_mistaken_for_symbols():
    for word in ("Model", "Value", "Gain", "Type", "SNo"):
        assert normalize_symbol(word) is None


def test_multi_character_subscripts_survive():
    assert normalize_symbol("L SII") == "L_SII"
    assert normalize_symbol("W R") == "WR"
