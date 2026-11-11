"""Product modes. Each preset is a frozen chain, not a new algorithm."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import yaml

from discrest.config import ConfigError, load_config
from discrest.pipeline import run_config

PRESETS: list[dict[str, Any]] = [
    {
        "id": "isolated",
        "title": "孤立咔嗒",
        "blurb": "清楚的爆点，并压低持续嘶声。",
        "cli": "sparse clicks, then hiss",
        "example": "public_78",
        "settings": {
            "sample_rate_policy": "native",
            "expected_sample_rate": 44100,
            "source": "preset-isolated",
            "rumble": {"enabled": False},
            "hum": {"enabled": False},
            "declick": {
                "enabled": True,
                "order": 32,
                "threshold": 16.0,
                "max_click_ms": 3.0,
                "half_width_ms": 0.6,
                "window_ms": 100.0,
                "dense_per_second": 40,
                "protect_dense": True,
            },
            "decrackle": {"enabled": False},
            "dehiss": {
                "enabled": True,
                "n_fft": 2048,
                "hop": 512,
                "noise_percentile": 15,
                "subtract": 1.0,
                "floor": 0.1,
                "smooth_bins": 31,
            },
            "neural": {"enabled": False, "checkpoint": None},
        },
    },
    {
        "id": "protect",
        "title": "密集保护",
        "blurb": "爆点太密时只登记，不把鼓点一起抹掉。",
        "cli": "flag dense transients and leave them",
        "example": "dense_transient",
        "settings": {
            "sample_rate_policy": "native",
            "expected_sample_rate": 44100,
            "source": "preset-protect",
            "rumble": {"enabled": False},
            "hum": {"enabled": False},
            "declick": {
                "enabled": True,
                "order": 32,
                "threshold": 16.0,
                "max_click_ms": 3.0,
                "half_width_ms": 0.6,
                "window_ms": 100.0,
                "dense_per_second": 40,
                "protect_dense": True,
            },
            "decrackle": {"enabled": False},
            "dehiss": {"enabled": False},
            "neural": {"enabled": False, "checkpoint": None},
        },
    },
    {
        "id": "surface",
        "title": "表面噪声",
        "blurb": "先取脉冲，再去掉隆隆声、哼声和细裂纹。",
        "cli": "clicks, crackle, rumble, and hum",
        "example": "surface",
        "settings": {
            "sample_rate_policy": "native",
            "expected_sample_rate": 44100,
            "source": "preset-surface",
            "rumble": {"enabled": True, "cutoff_hz": 80, "order": 4},
            "hum": {"enabled": True, "mains_hz": 50, "harmonics": 3, "quality": 30},
            "declick": {
                "enabled": True,
                "order": 32,
                "threshold": 16.0,
                "protect_dense": True,
            },
            "decrackle": {"enabled": True, "threshold": 3.0},
            "dehiss": {"enabled": False},
            "neural": {"enabled": False, "checkpoint": None},
        },
    },
]

_BY_ID = {item["id"]: item for item in PRESETS}
EXAMPLES = {"public_78", "dense_transient", "surface"}


def get_preset(preset_id: str) -> dict[str, Any]:
    try:
        return _BY_ID[preset_id]
    except KeyError as exc:
        known = ", ".join(_BY_ID)
        raise ConfigError(f"unknown preset {preset_id!r}; choose {known}") from exc


def public_presets() -> list[dict[str, Any]]:
    """Preset cards for the studio. Settings stay in the payload."""
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "blurb": item["blurb"],
            "example": item["example"],
            "settings": item["settings"],
        }
        for item in PRESETS
    ]


def document_for_settings(settings: dict[str, Any], source: str | None = None) -> dict[str, Any]:
    if "declick" not in settings or "dehiss" not in settings:
        raise ConfigError("settings need declick and dehiss")
    document = {
        "sample_rate_policy": settings.get("sample_rate_policy", "native"),
        "expected_sample_rate": int(settings.get("expected_sample_rate", 44100)),
        "source": source or settings.get("source") or "studio",
        "rumble": settings.get("rumble") or {"enabled": False},
        "hum": settings.get("hum") or {"enabled": False},
        "declick": settings["declick"],
        "decrackle": settings.get("decrackle") or {"enabled": False},
        "dehiss": settings["dehiss"],
        "neural": {"enabled": False, "checkpoint": None},
    }
    return document


def run_with_settings(
    settings: dict[str, Any],
    input_path: Path,
    output_dir: Path,
    source: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise ConfigError(f"input not found: {input_path}")
    document = document_for_settings(settings, source=source)
    document["input"] = str(input_path)
    document["output_dir"] = str(output_dir)
    with tempfile.TemporaryDirectory(prefix="discrest-req-") as tmp:
        cfg_path = Path(tmp) / "run.yaml"
        cfg_path.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
            newline="\n",
        )
        return run_config(load_config(cfg_path))


def run_preset(preset_id: str, input_path: Path, output_dir: Path) -> dict[str, Any]:
    preset = get_preset(preset_id)
    return run_with_settings(
        preset["settings"],
        input_path,
        output_dir,
        source=str(preset["settings"].get("source") or preset_id),
    )
