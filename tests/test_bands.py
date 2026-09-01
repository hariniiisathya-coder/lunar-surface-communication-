"""Tests for the lunarcomms.bands carrier ladder (UHF..S..Ka..FR2..D)."""

import pytest

from lunarcomms import bands


def test_scaffold_bands_preserved():
    # The original UHF/S/Ka anchors must be unchanged.
    assert bands.freq_hz("UHF") == pytest.approx(0.442e9)
    assert bands.freq_hz("S") == pytest.approx(2.5e9)
    assert bands.freq_hz("Ka") == pytest.approx(27.0e9)


def test_high_bands_added():
    # Extension: FR2 (28 GHz) and D-band (140 GHz) for the sub-THz story.
    assert bands.freq_hz("FR2") == pytest.approx(28.0e9)
    assert bands.freq_hz("D") == pytest.approx(140.0e9)


def test_ladder_is_sorted_and_complete():
    assert bands.LADDER_HZ == tuple(sorted(bands.BANDS.values()))
    assert 140e9 in bands.LADDER_HZ


def test_unknown_band_raises():
    with pytest.raises(KeyError):
        bands.freq_hz("X")
