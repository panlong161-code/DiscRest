"""Autoregressive click detection with LSAR interpolation.

A short-frame linear predictor is fit to a median-filtered copy of the
channel and applied to the original samples. Local peaks of the prediction
error that exceed a robust threshold become click centers. A short
neighborhood around each center is replaced by least-squares AR
interpolation. Regions longer than ``max_click_ms`` are left in place.
When a window contains more short clicks than ``dense_per_second``, those
clicks are listed as protected and are not replaced.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import lfilter

from discrest.config import DeclickSettings
from discrest.lsar import lsar_replace


@dataclass
class DeclickResult:
    audio: np.ndarray
    regions: list[tuple[int, int]]
    actions: list[str]
    flags: list[str]
    rejected_long_regions: int
    dense_window_starts: list[int]
    reasons: list[str]
    scores: list[float]


def levinson(autocorr: np.ndarray) -> np.ndarray:
    """Levinson-Durbin. ``autocorr[0]`` is the lag-0 coefficient."""
    order = len(autocorr) - 1
    coeffs = np.zeros(order + 1, dtype=np.float64)
    coeffs[0] = 1.0
    error = float(autocorr[0])
    if error <= 1e-18:
        return coeffs
    for step in range(1, order + 1):
        acc = float(autocorr[step])
        for lag in range(1, step):
            acc += float(coeffs[lag] * autocorr[step - lag])
        gamma = -acc / error
        if abs(gamma) >= 0.999:
            break
        updated = coeffs.copy()
        for lag in range(1, step):
            updated[lag] = coeffs[lag] + gamma * coeffs[step - lag]
        updated[step] = gamma
        coeffs = updated
        error *= 1.0 - gamma * gamma
        if error <= 1e-18:
            break
    return coeffs


def fit_ar(samples: np.ndarray, order: int) -> np.ndarray:
    centered = np.asarray(samples, dtype=np.float64)
    centered = centered - np.mean(centered)
    length = len(centered)
    if length <= order + 2:
        coeffs = np.zeros(order + 1, dtype=np.float64)
        coeffs[0] = 1.0
        return coeffs
    corr = np.correlate(centered, centered, mode="full")[length - 1 : length + order] / length
    corr[0] += 1e-6 * abs(float(corr[0])) + 1e-12
    return levinson(corr)


def prediction_error(samples: np.ndarray, settings: DeclickSettings, rate: int) -> np.ndarray:
    signal = np.asarray(samples, dtype=np.float64)
    length = len(signal)
    frame = max(int(round(settings.frame_ms * rate / 1000.0)), settings.order * 8)
    hop = max(frame // 2, settings.order)
    error_acc = np.zeros(length, dtype=np.float64)
    weight_acc = np.zeros(length, dtype=np.float64)
    if length <= frame:
        starts = [0]
        frame = length
    else:
        starts = list(range(0, length - frame + 1, hop))
        if starts[-1] != length - frame:
            starts.append(length - frame)
    window = np.hanning(frame)
    for start in starts:
        segment = signal[start : start + frame]
        centered = segment - np.mean(segment)
        kernel = min(settings.median_size, frame if frame % 2 == 1 else frame - 1)
        kernel = max(kernel, 3)
        smoothed = median_filter(centered, size=kernel, mode="nearest")
        coeffs = fit_ar(smoothed, settings.order)
        residual = lfilter(coeffs, [1.0], centered)
        fade = window.copy()
        fade[: settings.order] = 0.0
        error_acc[start : start + frame] += residual * fade
        weight_acc[start : start + frame] += fade
    output = np.zeros(length, dtype=np.float64)
    valid = weight_acc > 1e-8
    output[valid] = error_acc[valid] / weight_acc[valid]
    return output


def robust_sigma(error: np.ndarray) -> float:
    magnitude = np.abs(error)
    if magnitude.size == 0:
        return 1e-10
    cutoff = np.quantile(magnitude, 0.9)
    core = magnitude[magnitude <= cutoff]
    if core.size < 8:
        core = magnitude
    med = float(np.median(core))
    mad = float(np.median(np.abs(core - med)))
    return max(1.4826 * mad, 1e-10)


def _peaks(magnitude: np.ndarray, threshold: float, separation: int) -> list[int]:
    found: list[int] = []
    last = -separation
    for index in range(1, len(magnitude) - 1):
        value = magnitude[index]
        if value < threshold:
            continue
        if value < magnitude[index - 1] or value < magnitude[index + 1]:
            continue
        if index - last < separation:
            if found and value > magnitude[found[-1]]:
                found[-1] = index
                last = index
            continue
        found.append(index)
        last = index
    return found


def _merge(regions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not regions:
        return []
    ordered = sorted(regions)
    merged: list[list[int]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _sustained_onset(signal: np.ndarray, start: int, end: int, rate: int) -> bool:
    """A short spike followed by a much louder decay is a note attack.

    Clicks sitting on a steady tone have nearly the same level before and
    after the spike. A sparse drum hit does not, so density alone misses it.
    """
    width = max(8, int(round(0.03 * rate)))
    before = signal[max(0, start - width) : start]
    after = signal[end : end + width]
    if before.size < width // 2 or after.size < width // 2:
        return False
    before_rms = float(np.sqrt(np.mean(before * before)))
    after_rms = float(np.sqrt(np.mean(after * after)))
    if after_rms < 0.02:
        return False
    return after_rms > 2.5 * (before_rms + 1e-8)


def declick_channel(samples: np.ndarray, rate: int, settings: DeclickSettings) -> DeclickResult:
    signal = np.asarray(samples, dtype=np.float64)
    if not settings.enabled:
        return DeclickResult(signal.copy(), [], [], [], 0, [], [], [])
    error = prediction_error(signal, settings, rate)
    usable = error[settings.order : -settings.order] if len(error) > 2 * settings.order else error
    sigma = robust_sigma(usable)
    half = max(2, int(round(settings.half_width_ms * rate / 1000.0)))
    centers = _peaks(np.abs(error), settings.threshold * sigma, half)
    regions = _merge([(max(0, center - half), min(len(signal), center + half + 1)) for center in centers])
    max_len = max(half, int(round(settings.max_click_ms * rate / 1000.0)))
    kept = [(start, end) for start, end in regions if (end - start) <= max_len]
    rejected = len(regions) - len(kept)
    window = max(1, int(round(settings.window_ms * rate / 1000.0)))
    dense_starts: list[int] = []
    for origin in range(0, len(signal), window):
        count = sum(1 for start, _end in kept if origin <= start < origin + window)
        per_second = count / (window / rate)
        if per_second > settings.dense_per_second:
            dense_starts.append(origin)
    actions: list[str] = []
    reasons: list[str] = []
    scores: list[float] = []
    to_repair: list[tuple[int, int]] = []
    for start, end in kept:
        protected = settings.protect_dense and any(
            origin <= start < origin + window for origin in dense_starts
        )
        peak = float(np.max(np.abs(error[start:end]))) if end > start else 0.0
        scores.append(peak / sigma)
        onset = settings.protect_onset and _sustained_onset(signal, start, end, rate)
        if protected:
            actions.append("protected")
            reasons.append("dense-transient")
        elif onset:
            actions.append("protected")
            reasons.append("sustained-onset")
        else:
            actions.append("repaired")
            reasons.append("isolated-click")
            to_repair.append((start, end))
    flags = ["dense-transient"] if dense_starts else []
    if "sustained-onset" in reasons:
        flags.append("sustained-onset")
    restored = lsar_replace(signal, to_repair, settings.order)
    return DeclickResult(restored, kept, actions, flags, rejected, dense_starts, reasons, scores)
