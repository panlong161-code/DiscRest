"""Audacity 2.x Click Removal, defaults only.

This is a direct reading of ``EffectClickRemoval::RemoveClicks`` as shipped
with Audacity 2.1 (Craig DeForest): 8192-sample windows, hop 4096, a
4096-sample mean-square context, threshold 200, and max spike width 20.
Detected spikes are replaced by a straight line. It is here so a paper
example can be compared with that published effect. It is not Audacity,
and it is not part of the DiscRest chain.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

WINDOW = 8192
HOP = WINDOW // 2
SEP0 = 2049
THRESHOLD = 200
WIDTH = 20


@dataclass
class AudacityClickResult:
    audio: np.ndarray
    regions: list[tuple[int, int]]
    changed_samples: int


def _remove_clicks(buffer: np.ndarray, threshold: int, width: int) -> list[tuple[int, int]]:
    length = int(buffer.size)
    sep = SEP0
    squared = buffer * buffer
    context = squared.copy()
    step = 1
    while step < sep:
        context[: length - step] += context[step:]
        step *= 2
    sep = step
    context = context[: length - sep] / sep
    regions: list[tuple[int, int]] = []
    width_scale = max(width // 4, 1)
    while width_scale >= 1:
        spike = max(width // width_scale, 1)
        half = SEP0 // 2
        left = 0
        limit = min(context.size, length - half - spike)
        for index in range(limit):
            start = index + half
            local = float(np.mean(squared[start : start + spike]))
            if local >= threshold * float(context[index]) / 10.0:
                if left == 0:
                    left = start
                continue
            if left != 0 and index - left + half <= spike * 2:
                right = index + spike + half
                if right > left and right < length:
                    left_value = float(buffer[left])
                    right_value = float(buffer[min(right, length - 1)])
                    span = right - left
                    for sample in range(left, right):
                        weight = (sample - left) / span
                        buffer[sample] = right_value * weight + left_value * (1.0 - weight)
                        squared[sample] = buffer[sample] * buffer[sample]
                    regions.append((left, right))
                left = 0
            elif left != 0:
                left = 0
        width_scale //= 2
    return regions


def audacity_click_removal(
    samples: np.ndarray,
    threshold: int = THRESHOLD,
    width: int = WIDTH,
) -> AudacityClickResult:
    """Run the default Click Removal effect over one mono channel."""
    audio = np.asarray(samples, dtype=np.float64).reshape(-1).copy()
    original = audio.copy()
    if audio.size <= HOP:
        return AudacityClickResult(audio, [], 0)
    regions: list[tuple[int, int]] = []
    for origin in range(0, audio.size - HOP, HOP):
        stop = min(origin + WINDOW, audio.size)
        window = np.zeros(WINDOW, dtype=np.float64)
        window[: stop - origin] = audio[origin:stop]
        found = _remove_clicks(window, threshold, width)
        audio[origin:stop] = window[: stop - origin]
        for start, end in found:
            absolute_start = origin + start
            absolute_end = min(origin + end, stop)
            if absolute_end > absolute_start:
                regions.append((absolute_start, absolute_end))
    changed = int(np.count_nonzero(np.abs(audio - original) > 1e-8))
    return AudacityClickResult(audio, _merge(regions), changed)


def _merge(regions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not regions:
        return []
    ordered = sorted(regions)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]
