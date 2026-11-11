"""The public-domain cylinder excerpt and the Audacity click-removal baseline."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import yaml

from discrest.audio import read_wav
from discrest.audacity_click import audacity_click_removal
from discrest.pipeline import verify_example
from discrest.profile import profile_signal

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "archive_78"


def test_archive_excerpt_matches_the_recorded_hashes() -> None:
    ok, message = verify_example(EXAMPLE)
    assert ok, message
    assert "clicks=149" in message
    recorded = yaml.safe_load((EXAMPLE / "comparison.yaml").read_text(encoding="utf-8"))
    lines = (EXAMPLE / "out" / "clicks.csv").read_text(encoding="utf-8").splitlines()[1:]
    reasons = Counter(line.split(",")[5] for line in lines)
    disc = recorded["disc"]
    assert reasons["isolated-click"] == disc["isolated_click"]
    assert reasons["dense-transient"] == disc["dense_transient"]
    assert reasons["sustained-onset"] == disc["sustained_onset"]


def test_archive_excerpt_is_the_protect_preset() -> None:
    rate, samples = read_wav(EXAMPLE / "input.wav")
    report = profile_signal(samples[:, 0], rate)
    assert report["preset"] == "protect"
    assert report["confident"] is True
    assert report["reasons"] == ["dense-impulses"]


def test_audacity_defaults_and_a_sensitive_setting_match_the_record() -> None:
    recorded = yaml.safe_load((EXAMPLE / "comparison.yaml").read_text(encoding="utf-8"))
    rate, samples = read_wav(EXAMPLE / "input.wav")
    piece = samples[:, 0]
    for key in ("audacity_default", "audacity_sensitive"):
        spec = recorded[key]
        result = audacity_click_removal(piece, threshold=spec["threshold"], width=spec["width"])
        assert len(result.regions) == spec["regions"]
        assert result.changed_samples == spec["changed_samples"]


def test_audacity_default_edits_a_loud_click_on_a_quiet_tone() -> None:
    rate = 44100
    time = np.arange(rate, dtype=np.float64) / rate
    tone = 0.05 * np.sin(2.0 * np.pi * 220.0 * time)
    tone[20000:20004] += 0.9
    result = audacity_click_removal(tone)
    assert result.changed_samples > 0
    assert result.regions
