"""The four-column table that broke the cell-grid parser.

A paper printed "Parameter | Value | Parameter | Value". pdfplumber's grid
detection returned only the right-hand half, so the LEFT value column was
paired with the RIGHT parameter column and all seven recovered symbols carried
another symbol's number - silently. These pin the word-position parser that
replaced it.
"""
import pytest

from antenna_reconstruction.geometry_extraction.ingestion.word_tables import (
    _fold_subscripts, _group_lines, _header_columns, _symbol_from,
)


def _w(text, x0, top):
    return {"text": text, "x0": x0, "x1": x0 + 5 * len(text), "top": top,
            "bottom": top + 8}


def test_symbol_keeps_its_subscript_whole():
    # Concatenating first and re-parsing split "LSIII" into "LSI" + "II".
    assert _symbol_from(["L", "SIII"]) == "L_SIII"
    assert _symbol_from(["W", "f"]) == "W_f"
    assert _symbol_from(["D"]) == "D"


def test_nonsense_bases_and_subscripts_are_rejected():
    assert _symbol_from([]) is None
    assert _symbol_from(["Parameter"]) is None
    assert _symbol_from(["L", "far-too-long-a-subscript"]) is None


def test_header_needs_both_kinds_of_column():
    both = _header_columns([_w("Parameter", 225, 600), _w("Value(mm)", 318, 600)])
    assert both == [(225, "param"), (318, "value")]
    assert _header_columns([_w("Parameter", 225, 600)]) is None
    assert _header_columns([_w("Model", 10, 600), _w("Gain", 80, 600)]) is None


def test_four_column_header_is_read_as_two_pairs():
    columns = _header_columns([
        _w("Parameter", 225, 600), _w("Value(mm)", 318, 600),
        _w("Parameter", 415, 600), _w("Value(mm)", 507, 600),
    ])
    assert [kind for _, kind in columns] == ["param", "value", "param", "value"]


def test_a_results_header_is_not_a_parameter_table():
    assert _header_columns([
        _w("Model", 10, 600), _w("f(GHz)", 80, 600), _w("SAR(W/Kg)", 160, 600),
    ]) is None


def test_subscript_lines_are_folded_into_their_row():
    lines = _group_lines([
        _w("L", 239, 610), _w("34", 334, 610),
        _w("S", 244, 615),                      # the subscript of L
        _w("W", 239, 625), _w("28", 334, 625),
    ])
    folded = _fold_subscripts(lines)
    assert len(folded) == 2
    assert [w["text"] for w in folded[0]] == ["L", "S", "34"]


def test_a_full_row_is_not_folded_into_the_one_above():
    lines = _group_lines([
        _w("L", 239, 610), _w("34", 334, 610),
        _w("W", 239, 640), _w("28", 334, 640),
    ])
    assert len(_fold_subscripts(lines)) == 2
