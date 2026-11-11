"""Load and resolve a DiscRest run configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """The run file is missing a field or a value is out of range."""


@dataclass
class DeclickSettings:
    enabled: bool = True
    order: int = 32
    threshold: float = 16.0
    max_click_ms: float = 3.0
    half_width_ms: float = 0.6
    window_ms: float = 100.0
    dense_per_second: float = 40.0
    frame_ms: float = 40.0
    median_size: int = 11
    protect_dense: bool = True
    protect_onset: bool = True

    def check(self) -> None:
        if self.order < 2 or self.order > 128:
            raise ConfigError("declick.order must be between 2 and 128")
        if self.threshold <= 0:
            raise ConfigError("declick.threshold must be positive")
        if self.max_click_ms <= 0 or self.half_width_ms <= 0:
            raise ConfigError("declick widths must be positive")
        if self.window_ms <= 0 or self.dense_per_second <= 0:
            raise ConfigError("declick density window must be positive")
        if self.frame_ms < 10:
            raise ConfigError("declick.frame_ms must be at least 10")
        if self.median_size < 3 or self.median_size % 2 == 0:
            raise ConfigError("declick.median_size must be an odd integer >= 3")


@dataclass
class DehissSettings:
    enabled: bool = False
    n_fft: int = 2048
    hop: int = 512
    noise_percentile: float = 15.0
    subtract: float = 1.0
    floor: float = 0.1
    smooth_bins: int = 31

    def check(self) -> None:
        if self.n_fft < 32:
            raise ConfigError("dehiss.n_fft must be at least 32")
        if self.hop < 1 or self.hop >= self.n_fft:
            raise ConfigError("dehiss.hop must be in [1, n_fft)")
        if not 0 < self.noise_percentile < 100:
            raise ConfigError("dehiss.noise_percentile must be between 0 and 100")
        if self.subtract < 0:
            raise ConfigError("dehiss.subtract must be >= 0")
        if not 0 < self.floor <= 1:
            raise ConfigError("dehiss.floor must be in (0, 1]")
        if self.smooth_bins < 3 or self.smooth_bins % 2 == 0:
            raise ConfigError("dehiss.smooth_bins must be an odd integer >= 3")


@dataclass
class RumbleSettings:
    enabled: bool = False
    cutoff_hz: float = 40.0
    order: int = 4

    def check(self) -> None:
        if self.cutoff_hz <= 0:
            raise ConfigError("rumble.cutoff_hz must be positive")
        if self.order < 1 or self.order > 8:
            raise ConfigError("rumble.order must be between 1 and 8")


@dataclass
class HumSettings:
    enabled: bool = False
    mains_hz: float = 50.0
    harmonics: int = 4
    quality: float = 30.0

    def check(self) -> None:
        if self.mains_hz < 40:
            raise ConfigError("hum.mains_hz must be at least 40")
        if self.harmonics < 1 or self.harmonics > 8:
            raise ConfigError("hum.harmonics must be between 1 and 8")
        if self.quality < 5:
            raise ConfigError("hum.quality must be at least 5")


@dataclass
class DecrackleSettings:
    enabled: bool = False
    threshold: float = 10.0
    max_ms: float = 0.8
    median_ms: float = 0.5
    keep: float = 0.2
    window_ms: float = 100.0
    dense_per_second: float = 80.0

    def check(self) -> None:
        if self.threshold <= 0:
            raise ConfigError("decrackle.threshold must be positive")
        if self.max_ms <= 0 or self.median_ms <= 0 or self.window_ms <= 0:
            raise ConfigError("decrackle durations must be positive")
        if not 0 < self.keep < 1:
            raise ConfigError("decrackle.keep must be between 0 and 1")
        if self.dense_per_second <= 0:
            raise ConfigError("decrackle.dense_per_second must be positive")


@dataclass
class NeuralSettings:
    enabled: bool = False
    checkpoint: str | None = None

    def check(self) -> None:
        if self.enabled and not self.checkpoint:
            raise ConfigError("neural.checkpoint is required when neural.enabled is true")


@dataclass
class RunConfig:
    path: Path
    base_dir: Path
    input_path: Path
    output_dir: Path
    sample_rate_policy: str
    expected_sample_rate: int
    source: str | None
    rumble: RumbleSettings
    hum: HumSettings
    declick: DeclickSettings
    decrackle: DecrackleSettings
    dehiss: DehissSettings
    neural: NeuralSettings

    def resolved(self) -> dict[str, Any]:
        return {
            "sample_rate_policy": self.sample_rate_policy,
            "expected_sample_rate": self.expected_sample_rate,
            "source": self.source,
            "rumble": asdict(self.rumble),
            "hum": asdict(self.hum),
            "declick": asdict(self.declick),
            "decrackle": asdict(self.decrackle),
            "dehiss": asdict(self.dehiss),
            "neural": asdict(self.neural),
        }


_POLICIES = {"native", "require", "resample"}

_TOP_KEYS = {
    "input",
    "output_dir",
    "sample_rate_policy",
    "expected_sample_rate",
    "source",
    "rumble",
    "hum",
    "declick",
    "decrackle",
    "dehiss",
    "neural",
}


def _reject_unknown(mapping: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ConfigError(f"unknown {where} fields: {', '.join(unknown)}")


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name, {})
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be true or false")
    return value


def _load_settings(raw: dict[str, Any], name: str, cls: type):
    section = _section(raw, name) if name in raw else {}
    _reject_unknown(section, set(cls.__dataclass_fields__), name)
    for key in ("enabled", "protect_dense", "protect_onset"):
        if key in section:
            section[key] = _bool(section[key], f"{name}.{key}")
    settings = cls(**section)
    settings.check()
    return settings


def load_config(path: str | Path) -> RunConfig:
    cfg_path = Path(path).resolve()
    if not cfg_path.is_file():
        raise ConfigError(f"config not found: {cfg_path}")
    try:
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"could not parse {cfg_path.name}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config must be a mapping")
    _reject_unknown(raw, _TOP_KEYS, "config")
    for key in ("input", "declick", "dehiss"):
        if key not in raw:
            raise ConfigError(f"missing {key}")

    base = cfg_path.parent
    rumble = _load_settings(raw, "rumble", RumbleSettings)
    hum = _load_settings(raw, "hum", HumSettings)
    declick = _load_settings(raw, "declick", DeclickSettings)
    decrackle = _load_settings(raw, "decrackle", DecrackleSettings)
    dehiss = _load_settings(raw, "dehiss", DehissSettings)
    neural_raw = _section(raw, "neural") if "neural" in raw else {}
    _reject_unknown(neural_raw, set(NeuralSettings.__dataclass_fields__), "neural")
    if "enabled" in neural_raw:
        neural_raw["enabled"] = _bool(neural_raw["enabled"], "neural.enabled")
    checkpoint = neural_raw.get("checkpoint", None)
    if checkpoint is not None and not isinstance(checkpoint, str):
        raise ConfigError("neural.checkpoint must be a path or null")
    neural = NeuralSettings(
        enabled=neural_raw.get("enabled", False),
        checkpoint=checkpoint,
    )
    neural.check()

    policy = raw.get("sample_rate_policy", "native")
    if policy not in _POLICIES:
        raise ConfigError("sample_rate_policy must be native, require, or resample")
    expected_rate = int(raw.get("expected_sample_rate", 44100))
    if expected_rate < 8000:
        raise ConfigError("expected_sample_rate must be at least 8000")

    source = raw.get("source")
    if source is not None and not isinstance(source, str):
        raise ConfigError("source must be a string")

    input_path = (base / str(raw["input"])).resolve()
    output_dir = (base / str(raw.get("output_dir", "out"))).resolve()
    return RunConfig(
        path=cfg_path,
        base_dir=base,
        input_path=input_path,
        output_dir=output_dir,
        sample_rate_policy=policy,
        expected_sample_rate=expected_rate,
        source=source,
        rumble=rumble,
        hum=hum,
        declick=declick,
        decrackle=decrackle,
        dehiss=dehiss,
        neural=neural,
    )
