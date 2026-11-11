"""Impairment profile, preset suggestion, and a Praat TextGrid.

Speech front-ends separate impulsive events, low-frequency noise, stationary
hum, and a broadband floor before they choose a module. This profile uses
that split to point at an existing DiscRest preset. It does not train a
classifier and it does not change the audio.

``kept_band_share`` asks whether a removed stage still carries the tones
that remain in the restored signal. Speech-enhancement checks ask the same
question of a noise estimate. A high share is recorded as tonal leakage.

The TextGrid is the interval tier Praat already opens. Each click keeps the
action, reason, and score already stored in ``clicks.csv``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from discrest.audio import read_wav
from discrest.config import DeclickSettings
from discrest.declick import declick_channel

RUMBLE_RATIO_MIN = 0.08
HUM_PROMINENCE_MIN = 8.0
DENSE_PER_SECOND = 10.0
SPARSE_PER_SECOND = 0.2
LEAKAGE_SHARE_MIN = 0.35
LEAKAGE_OCCUPIED_MIN = 0.05


def _mono(samples: np.ndarray) -> np.ndarray:
    audio = np.asarray(samples, dtype=np.float64)
    if audio.ndim == 1:
        return audio
    return np.mean(audio, axis=1)


def _spectrum(mono: np.ndarray, rate: int) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(mono.size)
    power = np.abs(np.fft.rfft(mono * window)) ** 2
    freqs = np.fft.rfftfreq(mono.size, d=1.0 / rate)
    return freqs, power


def rumble_ratio(mono: np.ndarray, rate: int) -> float:
    """Share of power below 40 Hz, excluding the DC bin."""
    if mono.size < 16:
        return 0.0
    freqs, power = _spectrum(mono, rate)
    usable = freqs >= 1.0
    total = float(power[usable].sum())
    if total <= 0.0:
        return 0.0
    low = usable & (freqs < 40.0)
    return float(power[low].sum() / total)


def hum_prominence(mono: np.ndarray, rate: int) -> float:
    """How far a 50 Hz or 60 Hz harmonic rises above its local skirt."""
    if mono.size < 16:
        return 0.0
    freqs, power = _spectrum(mono, rate)
    best = 0.0
    for mains in (50.0, 60.0):
        for harmonic in range(1, 4):
            center = mains * harmonic
            if center >= rate / 2.0 - 20.0:
                continue
            core = np.abs(freqs - center) <= 1.5
            skirt = (np.abs(freqs - center) >= 4.0) & (np.abs(freqs - center) <= 12.0)
            if not np.any(core) or not np.any(skirt):
                continue
            core_mean = float(np.mean(power[core]))
            skirt_mean = float(np.mean(power[skirt]))
            best = max(best, core_mean / (skirt_mean + 1e-20))
    return best


def suggest_preset(
    *,
    click_rate: float,
    dense: bool,
    rumble: float,
    hum: float,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if dense or click_rate >= DENSE_PER_SECOND:
        reasons.append("dense-impulses")
    if rumble >= RUMBLE_RATIO_MIN:
        reasons.append("low-frequency")
    if hum >= HUM_PROMINENCE_MIN:
        reasons.append("mains-hum")
    if not reasons and click_rate >= SPARSE_PER_SECOND:
        reasons.append("sparse-clicks")
    if not reasons:
        reasons.append("little-impairment")
    if "dense-impulses" in reasons:
        return "protect", reasons
    if "low-frequency" in reasons or "mains-hum" in reasons:
        return "surface", reasons
    return "isolated", reasons


def profile_signal(samples: np.ndarray, rate: int, settings: DeclickSettings | None = None) -> dict[str, object]:
    """Listen-only profile. The declick result is counted and then discarded."""
    audio = np.asarray(samples, dtype=np.float64)
    if audio.ndim == 1:
        audio = audio[:, None]
    settings = settings or DeclickSettings()
    regions = 0
    dense = False
    for channel in range(audio.shape[1]):
        found = declick_channel(audio[:, channel], int(rate), settings)
        regions += len(found.regions)
        dense = dense or "dense-transient" in found.flags
    return _assemble(audio, int(rate), regions, dense)


def profile_from_run(
    samples: np.ndarray,
    rate: int,
    regions: list[tuple],
    flags: list[str],
) -> dict[str, object]:
    """Profile that matches the clicks already written for this run."""
    audio = np.asarray(samples, dtype=np.float64)
    if audio.ndim == 1:
        audio = audio[:, None]
    dense = "dense-transient" in flags or any(str(item).startswith("dense") for item in flags)
    return _assemble(audio, int(rate), len(regions), dense)


def _assemble(audio: np.ndarray, rate: int, regions: int, dense: bool) -> dict[str, object]:
    duration = audio.shape[0] / float(rate) if rate else 0.0
    click_rate = regions / duration if duration else 0.0
    mono = _mono(audio)
    rumble = rumble_ratio(mono, rate)
    hum = hum_prominence(mono, rate)
    preset, reasons = suggest_preset(click_rate=click_rate, dense=dense, rumble=rumble, hum=hum)
    if preset == "protect":
        confident = dense or click_rate >= DENSE_PER_SECOND * 1.25
    elif preset == "surface":
        confident = rumble >= RUMBLE_RATIO_MIN * 1.25 or hum >= HUM_PROMINENCE_MIN * 1.25
    else:
        confident = click_rate < DENSE_PER_SECOND * 0.5
    return {
        "click_rate": round(click_rate, 4),
        "rumble_ratio": round(rumble, 4),
        "hum_prominence": round(hum, 4),
        "dense": bool(dense),
        "preset": preset,
        "reasons": reasons,
        "confident": bool(confident),
    }


def kept_band_share(restored: np.ndarray, removed: np.ndarray, rate: int) -> dict[str, object]:
    """Fraction of removed music-band power that sits on the kept tones."""
    kept = _mono(restored)
    gone = _mono(removed)
    count = min(kept.size, gone.size)
    empty = {"share": 0.0, "occupied": 0.0, "flag": False}
    if count < 1024:
        return empty
    window = np.hanning(count)
    freqs = np.fft.rfftfreq(count, d=1.0 / rate)
    kept_power = np.abs(np.fft.rfft(kept[:count] * window)) ** 2
    gone_power = np.abs(np.fft.rfft(gone[:count] * window)) ** 2
    band = (freqs >= 180.0) & (freqs <= min(6000.0, rate * 0.45))
    kept_band = kept_power[band]
    gone_band = gone_power[band]
    kept_sum = float(kept_band.sum())
    gone_sum = float(gone_band.sum())
    if kept_sum <= 0.0 or gone_sum <= 0.0:
        return empty
    cutoff = float(np.quantile(kept_band, 0.99))
    mask = kept_band >= max(cutoff, 1e-12)
    if not np.any(mask):
        return empty
    share = float(gone_band[mask].sum() / gone_sum)
    occupied = float(gone_sum / kept_sum)
    flag = share >= LEAKAGE_SHARE_MIN and occupied >= LEAKAGE_OCCUPIED_MIN
    return {"share": round(share, 4), "occupied": round(occupied, 4), "flag": bool(flag)}


def leakage_by_stage(
    restored: np.ndarray,
    removed: dict[str, np.ndarray],
    rate: int,
) -> dict[str, dict[str, object]]:
    return {stage: kept_band_share(restored, signal, rate) for stage, signal in removed.items()}


def profile_file(path: str | Path) -> dict[str, object]:
    path = Path(path)
    rate, samples = read_wav(path)
    report = profile_signal(samples, int(rate))
    report["input"] = Path(path).name
    report["sample_rate"] = int(rate)
    return report


def write_textgrid(path: str | Path, regions: list[tuple], n_samples: int, rate: int) -> None:
    """Write one Praat interval tier per channel. Gaps are empty intervals."""
    grouped: dict[int, list[tuple[int, int, str]]] = {}
    for item in regions:
        channel, start, end, action, reason, score = item
        label = f"{action} {reason} {float(score):.1f}"
        grouped.setdefault(int(channel), []).append((int(start), int(end), label))
    channels = sorted(grouped) or [0]
    lines = [
        'File type = "ooTextFile"',
        'Object class = "TextGrid"',
        "",
        "xmin = 0",
        f"xmax = {_seconds(n_samples, rate)}",
        "tiers? <exists>",
        f"size = {len(channels)}",
        "item []:",
    ]
    for index, channel in enumerate(channels, start=1):
        rows = _cover(grouped.get(channel, []), n_samples)
        name = "clicks" if len(channels) == 1 else f"clicks-{channel}"
        lines.extend(
            [
                f"    item [{index}]:",
                '        class = "IntervalTier"',
                f'        name = "{name}"',
                "        xmin = 0",
                f"        xmax = {_seconds(n_samples, rate)}",
                f"        intervals: size = {len(rows)}",
            ]
        )
        for row_index, (start, end, text) in enumerate(rows, start=1):
            lines.extend(
                [
                    f"        intervals [{row_index}]:",
                    f"            xmin = {_seconds(start, rate)}",
                    f"            xmax = {_seconds(end, rate)}",
                    f'            text = "{_escape(text)}"',
                ]
            )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _cover(events: list[tuple[int, int, str]], n_samples: int) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    cursor = 0
    for start, end, label in sorted(events):
        start = min(max(start, cursor), n_samples)
        end = min(max(end, start), n_samples)
        if start > cursor:
            rows.append((cursor, start, ""))
        if end > start:
            rows.append((start, end, label))
            cursor = end
    if cursor < n_samples:
        rows.append((cursor, n_samples, ""))
    if not rows:
        rows.append((0, n_samples, ""))
    return rows


def _seconds(sample: int, rate: int) -> str:
    return f"{sample / float(rate):.6f}"


def _escape(text: str) -> str:
    return text.replace('"', '""')
