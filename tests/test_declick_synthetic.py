"""Synthetic checks for autoregressive declicking."""

from __future__ import annotations

import numpy as np

from discrest.config import DeclickSettings
from discrest.declick import declick_channel, fit_ar, levinson
from discrest.synthetic import clicked_tone, dense_example_signal, public_example_signal


def _overlaps(start: int, end: int, regions: list[tuple[int, int]]) -> bool:
    return any(start < region_end and end > region_start for region_start, region_end in regions)


def test_levinson_reduces_error_on_an_ar_process() -> None:
    rng = np.random.default_rng(0)
    drive = rng.normal(size=8000)
    signal = np.zeros_like(drive)
    for index in range(2, len(drive)):
        signal[index] = 0.7 * signal[index - 1] - 0.2 * signal[index - 2] + 0.05 * drive[index]
    coeffs = fit_ar(signal, 8)
    residual = np.convolve(signal - np.mean(signal), coeffs, mode="valid")
    assert np.mean(residual**2) < 0.85 * np.var(signal)
    assert coeffs[0] == 1.0
    assert len(levinson(np.array([1.0, 0.0, 0.0]))) == 3


def test_known_clicks_are_removed_and_dominate_the_residual() -> None:
    rate = 44100
    starts = [8000, 22000, 41000, 63000]
    signal = clicked_tone(rate, 2.0, starts, click_width=6, click_amp=0.7, noise=0.004, seed=1)
    result = declick_channel(signal, rate, DeclickSettings())
    assert result.flags == []
    assert len(result.regions) == len(starts)
    for start in starts:
        assert _overlaps(start, start + 6, result.regions)
    assert set(result.actions) == {"repaired"}
    residual = signal - result.audio
    click = np.zeros(len(signal), dtype=bool)
    covered = np.zeros(len(signal), dtype=bool)
    for start in starts:
        click[start : start + 6] = True
    for start, end in result.regions:
        covered[start:end] = True
    inside = float(np.mean(residual[click] ** 2))
    outside = float(np.mean(residual[~covered] ** 2))
    assert inside > 20.0 * max(outside, 1e-12)
    assert np.max(np.abs(result.audio)) < 2.0


def test_clean_sine_is_left_unchanged() -> None:
    rate = 44100
    time = np.arange(rate * 2, dtype=np.float64) / rate
    signal = 0.25 * np.sin(2.0 * np.pi * 440.0 * time)
    result = declick_channel(signal, rate, DeclickSettings())
    assert result.regions == []
    assert np.max(np.abs(result.audio - signal)) < 1e-12


def test_public_example_keeps_each_planted_click() -> None:
    signal, spans = public_example_signal()
    result = declick_channel(signal, 44100, DeclickSettings(enabled=True))
    assert result.flags == []
    assert set(result.reasons) == {"isolated-click"}
    assert min(result.scores) >= 16.0
    assert len(result.regions) == len(spans)
    for start, end in spans:
        assert _overlaps(start, end, result.regions)


def test_dense_burst_is_flagged() -> None:
    signal = dense_example_signal()
    result = declick_channel(signal, 44100, DeclickSettings())
    assert "dense-transient" in result.flags
    assert len(result.regions) > 40
    assert len(result.audio) == len(signal)
