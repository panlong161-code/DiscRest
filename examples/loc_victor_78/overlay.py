"""Rebuild input.wav from the Library of Congress transfer.

The transfer is a delivery master with the low band already filtered, so it carries
no rumble and no hum. This script adds three impairments at the levels printed below
and writes input.wav. Every level is reported, and the base is kept alongside the sum,
so the error signal is known.

    python overlay.py --source master-mbrsrs-....wav --out input.wav

Requires soundfile. The random seed is fixed, so the output is reproducible.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SEGMENT_START_S = 38.0
SEGMENT_SECONDS = 30.0
HEADROOM_DB = -6.0
SEED = 20261112

RUMBLE = {"cutoff_hz": 35.0, "order": 4, "wow_hz": 1.0 / 1.8, "wow_depth": 0.35, "target_ratio": 0.18}
HUM = {"mains_hz": 50.0, "harmonics": (0.0, -3.0, -6.0), "drift_hz": 0.01, "drift_rate_hz": 0.07, "target_prominence": 25.0}
HISS = {"highpass_hz": 1000.0, "order": 2, "snr_db": 20.0}


def power_low_total(signal: np.ndarray, fs: int, edge_hz: float = 40.0) -> tuple[float, float]:
    window = np.hanning(signal.size)
    power = np.abs(np.fft.rfft(signal * window)) ** 2
    freqs = np.fft.rfftfreq(signal.size, d=1.0 / fs)
    usable = freqs >= 1.0
    return float(power[usable & (freqs < edge_hz)].sum()), float(power[usable].sum())


def rumble_ratio(mono: np.ndarray, fs: int) -> float:
    low, total = power_low_total(mono, fs)
    return low / total if total > 0 else 0.0


def hum_prominence(mono: np.ndarray, fs: int) -> float:
    window = np.hanning(mono.size)
    power = np.abs(np.fft.rfft(mono * window)) ** 2
    freqs = np.fft.rfftfreq(mono.size, d=1.0 / fs)
    best = 0.0
    for mains in (50.0, 60.0):
        for harmonic in range(1, 4):
            center = mains * harmonic
            if center >= fs / 2.0 - 20.0:
                continue
            core = np.abs(freqs - center) <= 1.5
            skirt = (np.abs(freqs - center) >= 4.0) & (np.abs(freqs - center) <= 12.0)
            if not np.any(core) or not np.any(skirt):
                continue
            best = max(best, float(np.mean(power[core])) / (float(np.mean(power[skirt])) + 1e-20))
    return best


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="original Library of Congress wav")
    parser.add_argument("--out", default="input.wav")
    args = parser.parse_args()

    rng = np.random.default_rng(SEED)
    audio, fs = sf.read(args.source, dtype="float64")
    mono = audio.mean(axis=1)
    start = int(round(SEGMENT_START_S * fs))
    base = mono[start : start + int(round(SEGMENT_SECONDS * fs))].copy()
    base *= 10.0 ** (HEADROOM_DB / 20.0)

    # rumble: 1/f noise, low-passed, plus the eccentricity term
    white = rng.standard_normal(base.size)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(white.size, d=1.0 / fs)
    spec[0] = 0.0
    spec[1:] /= np.sqrt(freqs[1:])
    white = np.fft.irfft(spec, n=white.size)
    noise = sosfilt(butter(RUMBLE["order"], RUMBLE["cutoff_hz"], btype="lowpass", fs=fs, output="sos"), white)
    noise /= np.sqrt(np.mean(noise**2))
    t = np.arange(base.size) / fs
    noise = noise + RUMBLE["wow_depth"] * np.sin(2.0 * np.pi * RUMBLE["wow_hz"] * t)
    noise /= np.sqrt(np.mean(noise**2))

    low0, total0 = power_low_total(base, fs)
    target = RUMBLE["target_ratio"]
    delta = (target * total0 - low0) / (1.0 - target)
    scale = np.sqrt(delta / power_low_total(noise, fs)[1])
    rumbling = base + scale * noise
    rumbling = base + scale * noise * np.sqrt(target / rumble_ratio(rumbling, fs))

    # hum: mains, harmonics, slow drift
    inst = HUM["mains_hz"] + HUM["drift_hz"] * np.sin(2.0 * np.pi * HUM["drift_rate_hz"] * t)
    phase = 2.0 * np.pi * np.cumsum(inst) / fs
    unit = np.zeros_like(base)
    for k, level_db in enumerate(HUM["harmonics"], start=1):
        unit += 10.0 ** (level_db / 20.0) * np.sin(k * phase)
    unit /= np.sqrt(np.mean(unit**2))
    amp = float(np.sqrt(np.mean(base**2))) * 10.0 ** (-40.0 / 20.0)
    humming = base + amp * unit
    for _ in range(4):
        got = hum_prominence(humming, fs)
        if got <= 0:
            break
        amp *= np.sqrt(HUM["target_prominence"] / got)
        humming = base + amp * unit

    # hiss: broadband, high-passed
    hiss_noise = rng.standard_normal(base.size)
    hiss_noise = sosfilt(butter(HISS["order"], HISS["highpass_hz"], btype="highpass", fs=fs, output="sos"), hiss_noise)
    hiss_noise /= np.sqrt(np.mean(hiss_noise**2))
    hissing = base + float(np.sqrt(np.mean(base**2))) * 10.0 ** (-HISS["snr_db"] / 20.0) * hiss_noise

    out = base + (rumbling - base) + (humming - base) + (hissing - base)
    if np.max(np.abs(out)) >= 1.0:
        raise SystemExit("peak reached full scale; lower HEADROOM_DB")

    sf.write(Path(args.out), out.astype(np.float32), fs, subtype="PCM_16")
    print(f"wrote {args.out}: {out.size} samples at {fs} Hz")
    print(f"  rumble_ratio   {rumble_ratio(out, fs):.4f}  (target {RUMBLE['target_ratio']})")
    print(f"  hum_prominence {hum_prominence(out, fs):.2f}  (target {HUM['target_prominence']})")
    print(f"  rms            {np.sqrt(np.mean(out**2)):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
