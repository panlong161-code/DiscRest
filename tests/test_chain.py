"""Rumble, hum, crackle, LSAR fill, and dense-window protection."""

from __future__ import annotations

import numpy as np

from discrest.chain import apply_hum, apply_rumble, decrackle_channel
from discrest.config import DecrackleSettings, DeclickSettings, HumSettings, RumbleSettings
from discrest.declick import declick_channel
from discrest.synthetic import dense_example_signal


def _tone_amp(samples: np.ndarray, rate: int, freq: float) -> float:
    window = np.hanning(len(samples))
    spectrum = np.fft.rfft(samples * window)
    bin_index = int(round(freq * len(samples) / rate))
    return float(abs(spectrum[bin_index]))


def test_rumble_reduces_low_frequency_and_keeps_the_tone() -> None:
    rate = 44100
    time = np.arange(rate, dtype=np.float64) / rate
    mixed = 0.2 * np.sin(2.0 * np.pi * 30.0 * time) + 0.2 * np.sin(2.0 * np.pi * 440.0 * time)
    restored = apply_rumble(mixed, rate, RumbleSettings(enabled=True, cutoff_hz=80.0, order=4))
    assert _tone_amp(restored, rate, 30.0) < 0.35 * _tone_amp(mixed, rate, 30.0)
    assert _tone_amp(restored, rate, 440.0) > 0.8 * _tone_amp(mixed, rate, 440.0)


def test_hum_reduces_mains_and_keeps_the_tone() -> None:
    rate = 44100
    time = np.arange(rate, dtype=np.float64) / rate
    mixed = 0.2 * np.sin(2.0 * np.pi * 50.0 * time) + 0.2 * np.sin(2.0 * np.pi * 440.0 * time)
    restored = apply_hum(
        mixed,
        rate,
        HumSettings(enabled=True, mains_hz=50.0, harmonics=3, quality=30.0),
    )
    assert _tone_amp(restored, rate, 50.0) < 0.35 * _tone_amp(mixed, rate, 50.0)
    assert _tone_amp(restored, rate, 440.0) > 0.8 * _tone_amp(mixed, rate, 440.0)


def test_lsar_pulls_a_click_back_toward_the_sine() -> None:
    rate = 44100
    time = np.arange(rate, dtype=np.float64) / rate
    clean = 0.25 * np.sin(2.0 * np.pi * 440.0 * time)
    broken = clean.copy()
    gap = slice(20000, 20006)
    broken[gap] += 0.8
    restored = declick_channel(broken, rate, DeclickSettings()).audio
    before = float(np.mean((broken[gap] - clean[gap]) ** 2))
    after = float(np.mean((restored[gap] - clean[gap]) ** 2))
    assert after < 0.25 * before


def test_dense_windows_are_detected_and_left_in_place() -> None:
    signal = dense_example_signal()
    protected = declick_channel(signal, 44100, DeclickSettings(protect_dense=True))
    repaired = declick_channel(signal, 44100, DeclickSettings(protect_dense=False))
    burst = slice(44100, 88200)
    protected_change = float(np.mean(np.abs(protected.audio[burst] - signal[burst])))
    repaired_change = float(np.mean(np.abs(repaired.audio[burst] - signal[burst])))
    assert "dense-transient" in protected.flags
    assert "protected" in protected.actions
    assert "dense-transient" in protected.reasons
    assert protected_change < 0.25 * repaired_change


def test_decrackle_repairs_sparse_spikes_and_protects_a_burst() -> None:
    rate = 44100
    time = np.arange(rate, dtype=np.float64) / rate
    signal = 0.2 * np.sin(2.0 * np.pi * 330.0 * time)
    sparse = signal.copy()
    sparse[8000:8002] += 0.45
    sparse[20000:20002] -= 0.45
    settings = DecrackleSettings(enabled=True, threshold=8.0)
    sparse_result = decrackle_channel(sparse, rate, settings)
    assert sparse_result.flags == []
    assert sparse_result.repaired >= 2
    assert abs(float(sparse_result.audio[8000] - signal[8000])) < abs(float(sparse[8000] - signal[8000]))

    burst = signal.copy()
    for start in range(12000, 12000 + rate // 2, 40):
        burst[start : start + 2] += 0.45
    burst_result = decrackle_channel(burst, rate, settings)
    assert "dense-crackle" in burst_result.flags
    assert burst_result.protected > burst_result.repaired


def test_a_sparse_stick_hit_is_left_in_place() -> None:
    rate = 44100
    time = np.arange(rate, dtype=np.float64) / rate
    quiet = 0.02 * np.sin(2.0 * np.pi * 196.0 * time)
    onset = int(0.6 * rate)
    drum = quiet.copy()
    drum[onset : onset + 5] += 0.8
    decay_n = int(0.08 * rate)
    decay_t = np.arange(decay_n, dtype=np.float64) / rate
    drum[onset + 5 : onset + 5 + decay_n] += (
        0.28 * np.exp(-decay_t * 40.0) * np.sin(2.0 * np.pi * 180.0 * decay_t)
    )
    kept = declick_channel(drum, rate, DeclickSettings())
    removed = declick_channel(drum, rate, DeclickSettings(protect_onset=False))
    assert "sustained-onset" in kept.flags
    assert "sustained-onset" in kept.reasons
    assert abs(float(kept.audio[onset] - drum[onset])) < abs(float(removed.audio[onset] - drum[onset]))
