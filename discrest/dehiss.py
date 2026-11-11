"""Percentile spectral subtraction for steady hiss.

The noise curve is the median-smoothed mean magnitude of the quietest
frames. Tonal peaks are narrower than the smoothing window, so they stay
above the curve and are attenuated less than the surrounding hiss.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter

from discrest.config import DehissSettings


def dehiss_channel(samples: np.ndarray, settings: DehissSettings) -> np.ndarray:
    signal = np.asarray(samples, dtype=np.float64)
    if not settings.enabled:
        return signal.copy()
    n_fft = int(settings.n_fft)
    hop = int(settings.hop)
    window = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n_fft) / n_fft)
    padded = np.pad(signal, (n_fft, n_fft))
    limit = len(padded) - n_fft + 1
    starts = list(range(0, max(limit, 1), hop))
    spec = np.empty((n_fft // 2 + 1, len(starts)), dtype=np.complex128)
    frame_rms = np.empty(len(starts), dtype=np.float64)
    for index, start in enumerate(starts):
        frame = padded[start : start + n_fft]
        frame_rms[index] = float(np.sqrt(np.mean(frame * frame) + 1e-18))
        spec[:, index] = np.fft.rfft(frame * window)
    magnitude = np.abs(spec)
    cutoff = np.quantile(frame_rms, settings.noise_percentile / 100.0)
    quiet = np.flatnonzero(frame_rms <= cutoff + 1e-15)
    if quiet.size < 3:
        quiet = np.argsort(frame_rms)[: max(3, len(starts) // 10)]
    profile = np.mean(magnitude[:, quiet], axis=1)
    profile = median_filter(profile, size=settings.smooth_bins, mode="nearest")
    gain = 1.0 - settings.subtract * profile[:, None] / np.maximum(magnitude, 1e-12)
    gain = np.clip(gain, settings.floor, 1.0)
    spec *= gain
    output = np.zeros(len(padded), dtype=np.float64)
    weight = np.zeros(len(padded), dtype=np.float64)
    synth = window * window
    for index, start in enumerate(starts):
        frame = np.fft.irfft(spec[:, index], n=n_fft)
        output[start : start + n_fft] += frame * window
        weight[start : start + n_fft] += synth
    valid = weight > 1e-8
    output[valid] /= weight[valid]
    restored = output[n_fft : n_fft + len(signal)]
    if len(restored) < len(signal):
        restored = np.pad(restored, (0, len(signal) - len(restored)))
    return restored[: len(signal)]
