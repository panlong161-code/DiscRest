"""WAV read/write and file hashes."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from discrest.config import ConfigError


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    if not path.is_file():
        raise ConfigError(f"input not found: {path}")
    try:
        rate, data = wavfile.read(path)
    except Exception as exc:
        raise ConfigError(f"could not read wav: {path.name}") from exc
    array = np.asarray(data)
    if array.size == 0:
        raise ConfigError("input wav is empty")
    if np.issubdtype(array.dtype, np.floating):
        samples = array.astype(np.float64)
    elif np.issubdtype(array.dtype, np.integer):
        scale = float(abs(np.iinfo(array.dtype).min))
        samples = array.astype(np.float64) / scale
    else:
        raise ConfigError(f"unsupported wav dtype: {array.dtype}")
    if samples.ndim == 1:
        samples = samples[:, None]
    elif samples.ndim != 2:
        raise ConfigError("wav must be mono or stereo")
    return int(rate), samples


def to_int16(samples: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.rint(samples * 32767.0), -32768, 32767)
    return clipped.astype(np.int16)


def write_wav(path: Path, rate: int, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = to_int16(samples)
    if data.ndim == 2 and data.shape[1] == 1:
        data = data[:, 0]
    wavfile.write(path, int(rate), data)


def resample_audio(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate:
        return samples
    factor = int(np.gcd(source_rate, target_rate))
    up = target_rate // factor
    down = source_rate // factor
    columns = [
        resample_poly(samples[:, index], up, down)
        for index in range(samples.shape[1])
    ]
    return np.stack(columns, axis=1)
