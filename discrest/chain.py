"""Rumble high-pass, mains notch, and short-crackle attenuation.

PD-Cleaner runs rumble and hum before clicks. A zero-phase high-pass or
notch spreads one impulse into a ring, and the AR detector then marks
that ring as more clicks. DiscRest therefore repairs clicks and crackle
first, then applies these filters. Era equalization is not included.
The filters themselves are ordinary Butterworth and biquad sections.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import butter, iirnotch, sosfiltfilt, tf2sos

from discrest.config import ConfigError, DecrackleSettings, HumSettings, RumbleSettings
from discrest.declick import _merge, _peaks


@dataclass
class CrackleResult:
    audio: np.ndarray
    repaired: int
    protected: int
    flags: list[str]


def _filter(sos: np.ndarray, samples: np.ndarray) -> np.ndarray:
    padlen = 3 * int(sos.shape[0])
    if len(samples) <= padlen * 3:
        return np.array(samples, dtype=np.float64, copy=True)
    return sosfiltfilt(sos, samples)


def apply_rumble(samples: np.ndarray, rate: int, settings: RumbleSettings) -> np.ndarray:
    signal = np.asarray(samples, dtype=np.float64)
    if not settings.enabled:
        return signal.copy()
    nyquist = rate / 2.0
    if settings.cutoff_hz >= nyquist * 0.9:
        raise ConfigError("rumble.cutoff_hz must stay below the Nyquist frequency")
    sos = butter(settings.order, settings.cutoff_hz, btype="highpass", fs=rate, output="sos")
    return _filter(sos, signal)


def apply_hum(samples: np.ndarray, rate: int, settings: HumSettings) -> np.ndarray:
    signal = np.asarray(samples, dtype=np.float64)
    if not settings.enabled:
        return signal.copy()
    output = signal.copy()
    nyquist = rate / 2.0
    for harmonic in range(1, settings.harmonics + 1):
        freq = settings.mains_hz * harmonic
        if freq >= nyquist * 0.9:
            break
        zeros, poles = iirnotch(freq, settings.quality, fs=rate)
        output = _filter(tf2sos(zeros, poles), output)
    return output


def decrackle_channel(samples: np.ndarray, rate: int, settings: DecrackleSettings) -> CrackleResult:
    signal = np.asarray(samples, dtype=np.float64)
    if not settings.enabled or len(signal) < 8:
        return CrackleResult(signal.copy(), 0, 0, [])
    kernel = int(round(settings.median_ms * rate / 1000.0))
    if kernel % 2 == 0:
        kernel += 1
    kernel = max(3, min(kernel, len(signal) - 1 if len(signal) % 2 == 0 else len(signal)))
    if kernel < 3:
        return CrackleResult(signal.copy(), 0, 0, [])
    baseline = median_filter(signal, size=kernel, mode="nearest")
    error = signal - baseline
    # A sine sits slightly off a short median, so the MAD can collapse to zero.
    # The upper tail of that smooth error is the scale; real spikes rise above it.
    scale = max(float(np.quantile(np.abs(error), 0.95)), 1e-5)
    separation = max(2, int(round(settings.max_ms * rate / 1000.0)))
    centers = _peaks(np.abs(error), settings.threshold * scale, separation)
    span = max(1, separation // 4)
    regions = _merge(
        [(max(0, center - span), min(len(signal), center + span + 1)) for center in centers]
    )
    window = max(1, int(round(settings.window_ms * rate / 1000.0)))
    dense = []
    for origin in range(0, len(signal), window):
        count = sum(1 for start, _end in regions if origin <= start < origin + window)
        if count / (window / rate) > settings.dense_per_second:
            dense.append(origin)
    repaired_regions = []
    protected = 0
    for start, end in regions:
        if any(origin <= start < origin + window for origin in dense):
            protected += 1
            continue
        repaired_regions.append((start, end))
    output = signal.copy()
    for start, end in repaired_regions:
        output[start:end] = baseline[start:end] + settings.keep * error[start:end]
    flags = ["dense-crackle"] if dense else []
    return CrackleResult(output, len(repaired_regions), protected, flags)
