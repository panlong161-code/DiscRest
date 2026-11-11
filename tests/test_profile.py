"""Listen-only profile, Praat tier, and tonal-leakage check."""

from __future__ import annotations

import re
from pathlib import Path

from discrest.cli import main
from discrest.presets import run_preset
from discrest.profile import kept_band_share, profile_signal, write_textgrid
from discrest.synthetic import dense_example_signal, public_example_signal, surface_example_signal

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def test_each_example_suggests_its_own_preset() -> None:
    public, _spans = public_example_signal()
    assert profile_signal(public, 44100)["preset"] == "isolated"
    dense = profile_signal(dense_example_signal(), 44100)
    assert dense["preset"] == "protect"
    assert dense["reasons"] == ["dense-impulses"]
    surface = profile_signal(surface_example_signal(), 44100)
    assert surface["preset"] == "surface"
    assert surface["reasons"] == ["low-frequency", "mains-hum"]
    assert surface["confident"] is True
    assert profile_signal(public, 44100)["confident"] is True
    assert dense["confident"] is True


def test_profile_command_names_the_public_example(capsys) -> None:
    code = main(["profile", "--input", str(ROOT / "examples" / "public_78" / "input.wav")])
    assert code == 0
    text = capsys.readouterr().out
    assert "preset: isolated" in text
    assert "sparse-clicks" in text


def test_removing_the_tone_is_leakage_and_a_click_is_not() -> None:
    rate = 44100
    time = np.arange(rate, dtype=np.float64) / rate
    tone = 0.2 * np.sin(2.0 * np.pi * 330.0 * time)
    click = np.zeros_like(tone)
    click[20000:20006] = 0.8
    assert kept_band_share(tone, click, rate)["flag"] is False
    assert kept_band_share(tone, tone, rate)["flag"] is True


def test_textgrid_intervals_cover_the_file_without_gaps(tmp_path: Path) -> None:
    regions = [(0, 100, 140, "repaired", "isolated-click", 20.0)]
    path = tmp_path / "clicks.textgrid"
    write_textgrid(path, regions, 1000, 1000)
    text = path.read_text(encoding="utf-8")
    assert 'Object class = "TextGrid"' in text
    assert 'text = "repaired isolated-click 20.0"' in text
    pairs = re.findall(r"intervals \[\d+\]:\n\s+xmin = ([0-9.]+)\n\s+xmax = ([0-9.]+)", text)
    assert pairs[0][0] == "0.000000"
    assert pairs[-1][1] == "1.000000"
    for previous, current in zip(pairs, pairs[1:]):
        assert previous[1] == current[0]


def test_surface_run_keeps_rumble_out_of_the_tone(tmp_path: Path) -> None:
    record = run_preset("surface", ROOT / "examples" / "surface" / "input.wav", tmp_path)
    assert record["profile"]["preset"] == "surface"
    assert record["leakage"]["rumble"]["flag"] is False
    assert record["leakage"]["hum"]["flag"] is False
    assert record["leakage"]["declick"]["flag"] is False
    text = (tmp_path / "clicks.textgrid").read_text(encoding="utf-8")
    assert "isolated-click" in text


def test_a_highpass_that_takes_the_tone_is_put_back(tmp_path: Path) -> None:
    import copy

    from discrest.audio import read_wav, write_wav
    from discrest.chain import apply_rumble
    from discrest.config import RumbleSettings
    from discrest.presets import get_preset, run_with_settings

    rate = 44100
    time = np.arange(rate * 2, dtype=np.float64) / rate
    signal = 0.2 * np.sin(2.0 * np.pi * 330.0 * time) + 0.12 * np.sin(2.0 * np.pi * 30.0 * time)
    source = tmp_path / "in.wav"
    write_wav(source, rate, signal)
    settings = copy.deepcopy(get_preset("surface")["settings"])
    settings["rumble"]["cutoff_hz"] = 2000
    record = run_with_settings(settings, source, tmp_path / "out")
    assert record["leakage"]["rumble"]["reverted"] is True
    assert "leakage-reverted" in record["flags"]
    _rate, restored = read_wav(tmp_path / "out" / "restored.wav")
    raw = apply_rumble(signal, rate, RumbleSettings(enabled=True, cutoff_hz=2000, order=4))

    def peak(samples: np.ndarray) -> float:
        column = samples[:, 0] if samples.ndim == 2 else samples
        spectrum = np.abs(np.fft.rfft(column * np.hanning(column.size)))
        bin_index = int(round(330.0 * column.size / rate))
        return float(spectrum[bin_index])

    original = peak(signal)
    assert peak(raw) < 0.25 * original
    assert peak(restored) > 0.8 * original

