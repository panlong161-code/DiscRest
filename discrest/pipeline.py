"""Run one config and check it against the recorded example."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from discrest import __version__
from discrest.audio import read_wav, resample_audio, sha256_file, write_wav
from discrest.chain import apply_hum, apply_rumble, decrackle_channel
from discrest.config import ConfigError, RunConfig, load_config
from discrest.declick import declick_channel
from discrest.dehiss import dehiss_channel
from discrest.profile import kept_band_share, profile_from_run, write_textgrid


def _apply_neural(checkpoint: str) -> None:
    path = Path(checkpoint)
    if not path.is_file():
        raise ConfigError(f"neural checkpoint not found: {path}")
    raise ConfigError(
        "The optional neural backend has no bundled weights. "
        "Leave neural.enabled false for the reproducible example. "
        "A local Moliner checkpoint can be connected in a later version; "
        "DiscRest will not invent that result."
    )


def _prepare(samples: np.ndarray, rate: int, config: RunConfig) -> tuple[np.ndarray, int]:
    policy = config.sample_rate_policy
    target = config.expected_sample_rate
    if policy == "require" and rate != target:
        raise ConfigError(
            f"sample rate {rate} does not match expected_sample_rate {target}"
        )
    if policy == "resample" and rate != target:
        return resample_audio(samples, rate, target), target
    return samples, rate


def _rms(before: np.ndarray, after: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(before - after))))


def _guard_stage(before: np.ndarray, after: np.ndarray, rate: int, *, revert: bool) -> tuple[np.ndarray, dict[str, Any]]:
    """Record whether a stage took the tones that were present at its input.

    Filter and dehiss stages can be put back. Click repairs stay, because a
    short impulse does not own those tones; an onset is handled earlier.
    """
    report = dict(kept_band_share(before, before - after, rate))
    if revert and report["flag"]:
        report["reverted"] = True
        return np.array(before, copy=True), report
    report["reverted"] = False
    return after, report


def process(samples: np.ndarray, rate: int, config: RunConfig) -> dict[str, Any]:
    if config.neural.enabled:
        _apply_neural(config.neural.checkpoint or "")
    audio, process_rate = _prepare(samples, rate, config)
    removed_rms: dict[str, float] = {}
    clicked_audio = np.empty_like(audio)
    crackled_audio = np.empty_like(audio)
    regions: list[tuple[int, int, int, str, str, float]] = []
    flags: set[str] = set()
    rejected = 0
    dense_windows: list[int] = []
    crackle_repaired = 0
    crackle_protected = 0
    for channel in range(audio.shape[1]):
        column = audio[:, channel]
        clicked = declick_channel(column, process_rate, config.declick)
        crackled = decrackle_channel(clicked.audio, process_rate, config.decrackle)
        clicked_audio[:, channel] = clicked.audio
        crackled_audio[:, channel] = crackled.audio
        for (start, end), action, reason, score in zip(
            clicked.regions, clicked.actions, clicked.reasons, clicked.scores
        ):
            regions.append((channel, start, end, action, reason, score))
        flags.update(clicked.flags)
        flags.update(crackled.flags)
        rejected += clicked.rejected_long_regions
        dense_windows.extend(clicked.dense_window_starts)
        crackle_repaired += crackled.repaired
        crackle_protected += crackled.protected
    removed_rms["declick"] = _rms(audio, clicked_audio)
    removed_rms["decrackle"] = _rms(clicked_audio, crackled_audio)
    leakage = {
        "declick": _guard_stage(audio, clicked_audio, process_rate, revert=False)[1],
        "decrackle": _guard_stage(clicked_audio, crackled_audio, process_rate, revert=False)[1],
    }

    current = crackled_audio
    rumbled = np.empty_like(current)
    for channel in range(current.shape[1]):
        rumbled[:, channel] = apply_rumble(current[:, channel], process_rate, config.rumble)
    rumbled, leakage["rumble"] = _guard_stage(current, rumbled, process_rate, revert=True)
    removed_rms["rumble"] = _rms(current, rumbled)

    hummed = np.empty_like(rumbled)
    for channel in range(rumbled.shape[1]):
        hummed[:, channel] = apply_hum(rumbled[:, channel], process_rate, config.hum)
    hummed, leakage["hum"] = _guard_stage(rumbled, hummed, process_rate, revert=True)
    removed_rms["hum"] = _rms(rumbled, hummed)

    restored = np.empty_like(hummed)
    for channel in range(hummed.shape[1]):
        restored[:, channel] = dehiss_channel(hummed[:, channel], config.dehiss)
    restored, leakage["dehiss"] = _guard_stage(hummed, restored, process_rate, revert=True)
    removed_rms["dehiss"] = _rms(hummed, restored)
    if any(item["reverted"] for item in leakage.values()):
        flags.add("leakage-reverted")
    removed = {
        "declick": audio - clicked_audio,
        "decrackle": clicked_audio - crackled_audio,
        "rumble": crackled_audio - rumbled,
        "hum": rumbled - hummed,
        "dehiss": hummed - restored,
    }
    regions.sort()
    residual = audio - restored
    repaired = sum(1 for item in regions if item[3] == "repaired")
    protected = sum(1 for item in regions if item[3] == "protected")
    return {
        "audio": audio,
        "restored": restored,
        "residual": residual,
        "process_rate": process_rate,
        "regions": regions,
        "flags": sorted(flags),
        "rejected_long_regions": rejected,
        "dense_window_starts": dense_windows,
        "repaired_count": repaired,
        "protected_count": protected,
        "crackle_repaired": crackle_repaired,
        "crackle_protected": crackle_protected,
        "removed_rms": removed_rms,
        "removed": removed,
        "leakage": leakage,
    }


def _write_clicks(path: Path, regions: list[tuple[int, int, int, str, str, float]], rate: int) -> None:
    lines = ["channel,start_sample,end_sample,time_sec,action,reason,score\n"]
    for channel, start, end, action, reason, score in regions:
        lines.append(
            f"{channel},{start},{end},{start / rate:.6f},{action},{reason},{score:.4f}\n"
        )
    path.write_text("".join(lines), encoding="utf-8", newline="\n")


def _write_log(path: Path, result: dict[str, Any]) -> None:
    flag_text = ", ".join(result["flags"]) if result["flags"] else "none"
    text = (
        f"DiscRest {__version__}\n"
        f"clicks: {len(result['regions'])}\n"
        f"repaired: {result['repaired_count']}\n"
        f"protected: {result['protected_count']}\n"
        f"rejected_long_regions: {result['rejected_long_regions']}\n"
        f"crackle_repaired: {result['crackle_repaired']}\n"
        f"crackle_protected: {result['crackle_protected']}\n"
        f"flags: {flag_text}\n"
        f"profile: {result['profile']['preset']} ({', '.join(result['profile']['reasons'])})\n"
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def run_config(config: RunConfig) -> dict[str, Any]:
    original_rate, samples = read_wav(config.input_path)
    result = process(samples, original_rate, config)
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    restored_path = output_dir / "restored.wav"
    residual_path = output_dir / "residual.wav"
    clicks_path = output_dir / "clicks.csv"
    record_path = output_dir / "run.yaml"
    log_path = output_dir / "log.txt"
    rate = int(result["process_rate"])
    write_wav(restored_path, rate, result["restored"])
    write_wav(residual_path, rate, result["residual"])
    removed_names = {}
    for stage, signal in result["removed"].items():
        removed_path = output_dir / f"removed_{stage}.wav"
        write_wav(removed_path, rate, signal)
        removed_names[stage] = removed_path.name
    _write_clicks(clicks_path, result["regions"], rate)
    profile = profile_from_run(result["audio"], rate, result["regions"], result["flags"])
    leakage = result["leakage"]
    result["profile"] = profile
    result["leakage"] = leakage
    textgrid_path = output_dir / "clicks.textgrid"
    write_textgrid(textgrid_path, result["regions"], int(result["audio"].shape[0]), rate)
    _write_log(log_path, result)
    record: dict[str, Any] = {
        "software": "DiscRest",
        "version": __version__,
        "input": config.input_path.name,
        "input_sha256": sha256_file(config.input_path),
        "original_sample_rate": int(original_rate),
        "processing_sample_rate": rate,
        "channels": int(samples.shape[1]),
        "samples": int(result["audio"].shape[0]),
        "click_count": len(result["regions"]),
        "repaired_count": int(result["repaired_count"]),
        "protected_count": int(result["protected_count"]),
        "crackle_repaired": int(result["crackle_repaired"]),
        "crackle_protected": int(result["crackle_protected"]),
        "flags": list(result["flags"]),
        "rejected_long_regions": int(result["rejected_long_regions"]),
        "dense_window_starts": [int(item) for item in result["dense_window_starts"]],
        "removed_rms": result["removed_rms"],
        "profile": profile,
        "leakage": leakage,
        "settings": config.resolved(),
        "outputs": {
            "restored": restored_path.name,
            "residual": residual_path.name,
            "clicks": clicks_path.name,
            "log": log_path.name,
            "textgrid": textgrid_path.name,
            "removed": removed_names,
            "restored_sha256": sha256_file(restored_path),
            "residual_sha256": sha256_file(residual_path),
            "clicks_sha256": sha256_file(clicks_path),
        },
    }
    record_path.write_text(
        yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
    record["output_dir"] = str(output_dir)
    return record


_HASH_KEYS = ("restored_sha256", "residual_sha256", "clicks_sha256")
_COUNT_KEYS = ("click_count", "flags")


def keys_checked(expected: dict[str, Any], platform: str | None = None) -> tuple[str, ...]:
    """Compare SHA-256 only on the platform that recorded the hashes."""
    current = sys.platform if platform is None else platform
    recorded = expected.get("recorded_platform")
    if recorded in (None, "") or recorded == current:
        return _HASH_KEYS + _COUNT_KEYS
    return _COUNT_KEYS


def verify_example(example_dir: str | Path) -> tuple[bool, str]:
    folder = Path(example_dir).resolve()
    config_path = folder / "run.yaml"
    expected_path = folder / "expected.yaml"
    if not expected_path.is_file():
        return False, f"missing {expected_path.name}"
    try:
        expected = yaml.safe_load(expected_path.read_text(encoding="utf-8"))
        config = load_config(config_path)
        record = run_config(config)
    except (ConfigError, OSError, yaml.YAMLError) as exc:
        return False, str(exc)
    if not isinstance(expected, dict):
        return False, "expected.yaml must be a mapping"
    required = _HASH_KEYS + _COUNT_KEYS
    missing = [key for key in required if key not in expected]
    if missing:
        return False, "expected.yaml missing " + ", ".join(missing)
    outputs = record["outputs"]
    checks = {
        "restored_sha256": outputs["restored_sha256"],
        "residual_sha256": outputs["residual_sha256"],
        "clicks_sha256": outputs["clicks_sha256"],
        "click_count": record["click_count"],
        "flags": record["flags"],
    }
    compared = keys_checked(expected)
    mismatched = [key for key in compared if checks[key] != expected[key]]
    output_dir = Path(record["output_dir"])
    present = all((output_dir / name).is_file() for name in ("restored.wav", "residual.wav", "clicks.csv", "run.yaml", "log.txt"))
    if not present:
        return False, "output files are missing"
    if mismatched:
        detail = ", ".join(f"{key}: got {checks[key]!r}" for key in mismatched)
        return False, "mismatch " + detail
    flag_text = ",".join(record["flags"]) if record["flags"] else "none"
    recorded = expected.get("recorded_platform")
    hash_note = ""
    if recorded not in (None, "") and recorded != sys.platform:
        hash_note = f" hashes_recorded_on={recorded}"
    return True, (
        f"verify: ok clicks={record['click_count']} "
        f"flags={flag_text}{hash_note} "
        f"restored_sha256={outputs['restored_sha256']}"
    )
