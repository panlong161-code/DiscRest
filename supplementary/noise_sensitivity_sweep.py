"""Reproduce the controlled click-detection noise sweep reported in the paper.

Run from the project root with:
    python supplementary/noise_sensitivity_sweep.py

This controlled 440 Hz tone experiment measures detector behavior; it is not
a perceptual-quality evaluation or evidence about real-recording performance.
"""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from discrest.config import load_config
from discrest.pipeline import process
from discrest.synthetic import clicked_tone


RATE = 44_100
DURATION = 8.0
NOISE_LEVELS = (0.006, 0.012, 0.024, 0.048, 0.096)
SEEDS = (3, 7, 11)
CLICK_STARTS = [
    int(0.45 * RATE) + index * int(0.55 * RATE)
    for index in range(12)
]
TRUTH = [(start, start + 5) for start in CLICK_STARTS]


def snr_db(reference: np.ndarray, estimate: np.ndarray) -> float:
    error = np.asarray(estimate, dtype=np.float64) - reference
    return float(
        10.0
        * np.log10(
            np.sum(np.square(reference))
            / max(float(np.sum(np.square(error))), 1e-20)
        )
    )


def count_matches(
    predicted: list[tuple[int, int]],
) -> tuple[int, int, int]:
    used: set[int] = set()
    true_positive = 0
    for start, end in TRUTH:
        match = next(
            (
                index
                for index, (left, right) in enumerate(predicted)
                if index not in used and left < end and right > start
            ),
            None,
        )
        if match is not None:
            used.add(match)
            true_positive += 1
    false_positive = len(predicted) - len(used)
    false_negative = len(TRUTH) - true_positive
    return true_positive, false_positive, false_negative


def main() -> None:
    count = int(RATE * DURATION)
    time = np.arange(count, dtype=np.float64) / RATE
    clean = 0.25 * np.sin(2.0 * np.pi * 440.0 * time)
    config = load_config(ROOT / "examples" / "archive_78" / "run.yaml")

    for sigma in NOISE_LEVELS:
        detections = false_positives = misses = 0
        gains: list[float] = []
        for seed in SEEDS:
            observed = clicked_tone(
                RATE,
                DURATION,
                CLICK_STARTS,
                click_width=5,
                click_amp=0.62,
                noise=sigma,
                seed=seed,
                freq=440.0,
            )
            result = process(observed[:, None], RATE, config)
            predicted = [
                (int(region[1]), int(region[2]))
                for region in result["regions"]
            ]
            tp, fp, fn = count_matches(predicted)
            detections += tp
            false_positives += fp
            misses += fn
            gains.append(
                snr_db(clean, result["restored"][:, 0])
                - snr_db(clean, observed)
            )

        background_snr = 20.0 * np.log10(
            np.sqrt(np.mean(np.square(clean))) / sigma
        )
        if detections + false_positives:
            precision = detections / (detections + false_positives)
            precision_text = f"{precision:.2f}"
        else:
            precision_text = "n/a"
        recall = detections / (len(TRUTH) * len(SEEDS))
        print(
            f"sigma={sigma:.3f} background_snr={background_snr:.1f} dB "
            f"TP={detections} FP={false_positives} FN={misses} "
            f"P={precision_text} R={recall:.2f} "
            f"mean_delta_snr={mean(gains):+.2f} dB"
        )


if __name__ == "__main__":
    main()
