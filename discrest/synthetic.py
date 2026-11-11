"""Deterministic signals used by the tests and the bundled examples."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile

from discrest.audio import to_int16


def clicked_tone(
    rate: int,
    seconds: float,
    click_starts: list[int],
    click_width: int = 6,
    click_amp: float = 0.55,
    noise: float = 0.0,
    seed: int = 0,
    freq: float = 440.0,
) -> np.ndarray:
    count = int(rate * seconds)
    time = np.arange(count, dtype=np.float64) / rate
    signal = 0.25 * np.sin(2.0 * np.pi * freq * time)
    if noise:
        signal = signal + noise * np.random.default_rng(seed).normal(size=count)
    for start in click_starts:
        end = min(count, start + click_width)
        if start < 0 or start >= count:
            continue
        sign = 1.0 if (start // max(click_width, 1)) % 2 == 0 else -1.0
        signal[start:end] += sign * click_amp
    return signal


def public_example_signal(rate: int = 44100) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Eight-second chord with hiss and twelve isolated clicks."""
    seconds = 8.0
    count = int(rate * seconds)
    time = np.arange(count, dtype=np.float64) / rate
    tone = (
        0.16 * np.sin(2.0 * np.pi * 220.0 * time)
        + 0.10 * np.sin(2.0 * np.pi * 277.0 * time)
        + 0.07 * np.sin(2.0 * np.pi * 330.0 * time)
    )
    envelope = np.minimum(1.0, time / 0.05) * np.minimum(1.0, (seconds - time) / 0.08)
    hiss = 0.012 * np.random.default_rng(7).normal(size=count)
    signal = tone * envelope + hiss
    width = 5
    spans: list[tuple[int, int]] = []
    for index in range(12):
        start = int(0.45 * rate) + index * int(0.55 * rate)
        end = start + width
        signal[start:end] += (1.0 if index % 2 == 0 else -1.0) * 0.62
        spans.append((start, end))
    return signal, spans


def dense_example_signal(rate: int = 44100) -> np.ndarray:
    """Four-second tone with a one-second burst of impulses."""
    seconds = 4.0
    count = int(rate * seconds)
    time = np.arange(count, dtype=np.float64) / rate
    signal = 0.22 * np.sin(2.0 * np.pi * 196.0 * time)
    signal += 0.008 * np.random.default_rng(11).normal(size=count)
    begin = int(1.0 * rate)
    end = int(2.0 * rate)
    spacing = 80
    for start in range(begin, end, spacing):
        signal[start : start + 3] += 0.7 if ((start // spacing) % 2 == 0) else -0.7
    return signal


def write_wav_mono(path: Path, rate: int, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, rate, to_int16(samples))


def surface_example_signal(rate: int = 44100) -> np.ndarray:
    """Tone plus rumble, mains hum, three clicks, and three short crackles."""
    seconds = 4.0
    count = int(rate * seconds)
    time = np.arange(count, dtype=np.float64) / rate
    signal = 0.18 * np.sin(2.0 * np.pi * 330.0 * time)
    signal += 0.12 * np.sin(2.0 * np.pi * 30.0 * time)
    signal += 0.06 * np.sin(2.0 * np.pi * 50.0 * time)
    signal += 0.03 * np.sin(2.0 * np.pi * 150.0 * time)
    signal += 0.015 * np.random.default_rng(19).normal(size=count)
    for index, start in enumerate((int(0.5 * rate), int(1.5 * rate), int(2.6 * rate))):
        signal[start : start + 5] += 0.65 if index % 2 == 0 else -0.65
    for start in (int(0.9 * rate), int(2.0 * rate), int(3.2 * rate)):
        signal[start : start + 2] += 0.14
    return signal


def write_bundled_inputs(root: Path) -> None:
    public, _spans = public_example_signal()
    write_wav_mono(root / "examples" / "public_78" / "input.wav", 44100, public)
    dense = dense_example_signal()
    write_wav_mono(root / "examples" / "dense_transient" / "input.wav", 44100, dense)
    surface = surface_example_signal()
    write_wav_mono(root / "examples" / "surface" / "input.wav", 44100, surface)


if __name__ == "__main__":
    write_bundled_inputs(Path(__file__).resolve().parents[1])
