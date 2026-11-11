"""Least-squares autoregressive gap fill.

The missing samples minimize the AR prediction-error energy of a short
block, using coefficients fit on the uncorrupted context. This is the
LSAR interpolator associated with Godsill and Rayner (1998). A gap that
cannot be solved stably falls back to a straight line between its edges.
"""

from __future__ import annotations

import numpy as np


def _linear(samples: np.ndarray, start: int, end: int) -> None:
    length = len(samples)
    left = float(samples[start - 1]) if start > 0 else 0.0
    right = float(samples[end]) if end < length else left
    samples[start:end] = np.linspace(left, right, end - start + 2)[1:-1]


def _solve_gap(block: np.ndarray, start: int, end: int, coeffs: np.ndarray) -> np.ndarray | None:
    order = len(coeffs) - 1
    length = len(block)
    rows = length - order
    if rows <= order or end <= start:
        return None
    matrix = np.zeros((rows, length), dtype=np.float64)
    for row, index in enumerate(range(order, length)):
        for lag in range(order + 1):
            matrix[row, index - lag] = coeffs[lag]
    unknown = np.zeros(length, dtype=bool)
    unknown[start:end] = True
    known = ~unknown
    system = matrix[:, unknown]
    rhs = -matrix[:, known] @ block[known]
    try:
        filled, _, rank, _ = np.linalg.lstsq(system, rhs, rcond=None)
    except np.linalg.LinAlgError:
        return None
    if rank < system.shape[1] or not np.all(np.isfinite(filled)):
        return None
    return filled


def lsar_replace(samples: np.ndarray, regions: list[tuple[int, int]], order: int) -> np.ndarray:
    from discrest.declick import fit_ar

    restored = np.array(samples, dtype=np.float64, copy=True)
    if order < 2 or not regions:
        for start, end in regions:
            _linear(restored, start, end)
        return restored
    for start, end in regions:
        start = max(0, int(start))
        end = min(len(restored), int(end))
        if end <= start:
            continue
        context = max(order * 8, 128)
        left0 = max(0, start - context)
        right1 = min(len(restored), end + context)
        left = restored[left0:start]
        right = restored[end:right1]
        train = left if len(left) >= len(right) else right
        if len(train) <= order + 2 or len(left) < order or len(right) < order:
            _linear(restored, start, end)
            continue
        block = restored[left0:right1].copy()
        local_start = start - left0
        local_end = end - left0
        coeffs = fit_ar(train, order)
        solved = _solve_gap(block, local_start, local_end, coeffs)
        if solved is None:
            _linear(restored, start, end)
            continue
        reference = max(float(np.max(np.abs(train))), 1e-3)
        if float(np.max(np.abs(solved))) > 4.0 * reference + 0.5:
            _linear(restored, start, end)
            continue
        restored[start:end] = solved
    return restored
