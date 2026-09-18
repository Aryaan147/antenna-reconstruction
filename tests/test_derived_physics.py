import os
import pytest

from antenna_reconstruction.derived.physics import (
    derived_symbols, extract_physics,
)

ARRAY = (
    "Rectangular Microstrip 4x2 Patch Array Antenna at 2.4 GHz for WLAN. "
    "Dielectric Constant e r 4.3. Distance between patches is kept as lambda/2."
)


def test_frequency_wavelength_and_spacing_are_derived():
    p = extract_physics(ARRAY)
    assert p.frequency_hz == pytest.approx(2.4e9)
    assert p.array_nx == 4 and p.array_ny == 2
    assert p.spacing_divisor == 2

    values = derived_symbols(p)
    assert values["DX"] == pytest.approx(62.4568, abs=1e-3)
    assert values["DY"] == pytest.approx(62.4568, abs=1e-3)
    assert values["NX"] == 4 and values["NY"] == 2


def test_every_derived_value_carries_its_formula():
    for q in extract_physics(ARRAY).derived:
        assert q.formula and q.inputs and q.unit


def test_raw_wavelengths_are_not_offered_as_dimensions():
    """LAMBDA0 is real but is not a length of any part, so it is not a symbol."""
    values = derived_symbols(extract_physics(ARRAY))
    assert "LAMBDA0" not in values
    assert "LAMBDA_G_MIN" not in values


def test_the_lambda_convention_is_recorded_as_an_assumption():
    assert any("free-space" in a for a in extract_physics(ARRAY).assumptions)


def test_many_quoted_frequencies_derive_nothing():
    p = extract_physics(
        "Resonances at 2.9 GHz, 5.9 GHz and 7 GHz are observed. Spacing is "
        "lambda/2 between patches."
    )
    assert p.frequency_hz is None
    assert derived_symbols(p) == {}
    assert any("no wavelength is derived" in d for d in p.diagnostics)


def test_a_marked_centre_frequency_wins_over_other_mentions():
    p = extract_physics(
        "Bands at 3.5 GHz and 5.8 GHz were measured. The antenna was designed "
        "at 2.4 GHz for WLAN."
    )
    assert p.frequency_hz == pytest.approx(2.4e9)


def test_conflicting_permittivities_are_not_used():
    p = extract_physics(
        "dielectric constant of 4.4 is used. A dielectric constant of 2.2 was "
        "also tried. Designed at 2.4 GHz."
    )
    assert p.epsilon_r is None
    assert any("conflicting dielectric" in d for d in p.diagnostics)


@pytest.mark.skipif(
    not os.path.exists("data/raw/extracted_text/hexagonal_ring_antenna.txt"),
    reason="extracted text absent",
)
def test_a_wideband_paper_derives_nothing():
    """A dual-band paper quotes many frequencies; none may be picked."""
    p = extract_physics(
        open("data/raw/extracted_text/hexagonal_ring_antenna.txt").read()
    )
    assert p.frequency_hz is None
