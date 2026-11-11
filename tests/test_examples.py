"""The bundled examples reproduce the recorded hashes."""

from __future__ import annotations

from pathlib import Path

from discrest.pipeline import verify_example

ROOT = Path(__file__).resolve().parents[1]


def test_public_example_matches_the_recorded_hashes() -> None:
    ok, message = verify_example(ROOT / "examples" / "public_78")
    assert ok, message
    assert "clicks=12" in message


def test_dense_example_matches_the_recorded_hashes() -> None:
    ok, message = verify_example(ROOT / "examples" / "dense_transient")
    assert ok, message
    assert "dense-transient" in message


def test_surface_example_matches_the_recorded_hashes() -> None:
    ok, message = verify_example(ROOT / "examples" / "surface")
    assert ok, message
    assert "clicks=3" in message
    assert "flags=none" in message
