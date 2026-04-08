"""Tests for the switch-building helpers."""

import pytest

import dtcc_tetgen_wrapper
from dtcc_tetgen_wrapper import build_tetgen_switches, tetgen_defaults


def test_tetgen_defaults_returns_fresh_copy() -> None:
    """Changing a defaults dict must not leak into future callers."""
    defaults = tetgen_defaults()
    defaults["plc"] = False

    new_defaults = tetgen_defaults()
    assert new_defaults["plc"] is True
    assert new_defaults is not defaults


def test_build_tetgen_switches_concatenates_expected_flags() -> None:
    """A subset of parameters should map to their documented TetGen flags."""
    switches = build_tetgen_switches(
        params={
            "quality": 2.5,
            "output_faces": True,
            "output_edges": True,
        },
        max_volume=0.1,
        quiet=True,
        extra="XYZ",
    )
    
    # Default PLC flag plus the ones requested above.
    assert switches.startswith("p")
    assert "q2.5" in switches
    assert "f" in switches
    assert "e" in switches
    assert "a0.1" in switches
    assert switches.endswith("XYZ")
    

def test_build_tetgen_switches_detects_conflicting_options() -> None:
    """Mutually exclusive quiet/verbose flags raise a ValueError."""
    with pytest.raises(ValueError):
        build_tetgen_switches(quiet=True, verbose=True)


def test_package_exports_switches_module() -> None:
    """The package namespace exposes the switches helper module directly."""
    assert dtcc_tetgen_wrapper.switches.build_tetgen_switches is build_tetgen_switches
