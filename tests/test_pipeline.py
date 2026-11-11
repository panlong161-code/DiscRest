"""Pipeline, hiss removal, and command-line checks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from discrest.audio import write_wav
from discrest.cli import main
from discrest.config import ConfigError, DehissSettings, load_config
from discrest.dehiss import dehiss_channel
from discrest.pipeline import process, verify_example
from discrest.synthetic import clicked_tone


def test_dehiss_lowers_noise_and_keeps_the_tone() -> None:
    rate = 16000
    time = np.arange(rate * 2, dtype=np.float64) / rate
    clean = 0.3 * np.sin(2.0 * np.pi * 440.0 * time)
    rng = np.random.default_rng(3)
    noisy = clean + 0.05 * rng.normal(size=clean.shape)
    restored = dehiss_channel(noisy, DehissSettings(enabled=True, n_fft=512, hop=128, floor=0.05))
    assert len(restored) == len(noisy)
    noisy_error = float(np.mean((noisy - clean) ** 2))
    restored_error = float(np.mean((restored - clean) ** 2))
    assert restored_error < noisy_error
    assert np.corrcoef(restored, clean)[0, 1] > 0.95


def test_dehiss_reduces_noise_only_rms() -> None:
    rng = np.random.default_rng(4)
    noise = 0.1 * rng.normal(size=16000)
    restored = dehiss_channel(noise, DehissSettings(enabled=True, n_fft=512, hop=128, floor=0.05))
    assert np.sqrt(np.mean(restored**2)) < 0.5 * np.sqrt(np.mean(noise**2))


def test_disabled_dehiss_matches_declick_only(tmp_path: Path) -> None:
    rate = 22050
    signal = clicked_tone(rate, 1.5, [5000, 14000], noise=0.01, seed=5)
    wav_path = tmp_path / "in.wav"
    write_wav(wav_path, rate, signal)
    config_path = tmp_path / "run.yaml"
    config_path.write_text(
        """
input: in.wav
output_dir: out
sample_rate_policy: native
expected_sample_rate: 22050
declick:
  enabled: true
  order: 24
  threshold: 16
dehiss:
  enabled: false
neural:
  enabled: false
  checkpoint: null
""".strip(),
        encoding="utf-8",
    )
    config = load_config(config_path)
    from discrest.audio import read_wav

    file_rate, audio = read_wav(wav_path)
    result = process(audio, file_rate, config)
    assert np.allclose(result["restored"] + result["residual"], result["audio"])
    assert result["flags"] == []
    assert result["regions"]


def test_require_policy_rejects_a_different_rate(tmp_path: Path) -> None:
    wav_path = tmp_path / "in.wav"
    write_wav(wav_path, 16000, np.zeros(16000))
    config_path = tmp_path / "run.yaml"
    config_path.write_text(
        "input: in.wav\nexpected_sample_rate: 44100\nsample_rate_policy: require\n"
        "declick: {enabled: false}\ndehiss: {enabled: false}\n",
        encoding="utf-8",
    )
    assert main(["run", "--config", str(config_path)]) == 2


def test_run_is_repeatable_and_writes_the_four_outputs(tmp_path: Path) -> None:
    rate = 22050
    signal = clicked_tone(rate, 1.2, [4000, 12000], click_amp=0.8, noise=0.008, seed=6)
    write_wav(tmp_path / "in.wav", rate, signal)
    (tmp_path / "run.yaml").write_text(
        """
input: in.wav
output_dir: out
sample_rate_policy: native
declick:
  enabled: true
dehiss:
  enabled: true
  n_fft: 512
  hop: 128
neural:
  enabled: false
""".strip(),
        encoding="utf-8",
    )
    assert main(["run", "--config", str(tmp_path / "run.yaml")]) == 0
    first = yaml.safe_load((tmp_path / "out" / "run.yaml").read_text(encoding="utf-8"))
    assert main(["run", "--config", str(tmp_path / "run.yaml")]) == 0
    second = yaml.safe_load((tmp_path / "out" / "run.yaml").read_text(encoding="utf-8"))
    assert first["outputs"]["restored_sha256"] == second["outputs"]["restored_sha256"]
    assert first["outputs"]["residual_sha256"] == second["outputs"]["residual_sha256"]
    for name in ("restored.wav", "residual.wav", "clicks.csv", "run.yaml", "log.txt"):
        assert (tmp_path / "out" / name).is_file()
    assert "input_sha256" in first
    assert first["version"] == "0.7.0"
    assert "removed_rms" in first
    text = (tmp_path / "out" / "clicks.csv").read_text(encoding="utf-8")
    assert text.startswith("channel,start_sample,end_sample,time_sec,action,reason,score\n")


def test_missing_config_field(tmp_path: Path) -> None:
    path = tmp_path / "run.yaml"
    path.write_text("input: in.wav\n", encoding="utf-8")
    try:
        load_config(path)
    except ConfigError as exc:
        assert "declick" in str(exc)
    else:
        raise AssertionError("expected ConfigError")


def test_neural_backend_does_not_invent_audio(tmp_path: Path) -> None:
    write_wav(tmp_path / "in.wav", 16000, np.zeros(8000))
    (tmp_path / "run.yaml").write_text(
        "input: in.wav\ndeclick: {enabled: false}\ndehiss: {enabled: false}\n"
        "neural: {enabled: true, checkpoint: missing.bin}\n",
        encoding="utf-8",
    )
    assert main(["run", "--config", str(tmp_path / "run.yaml")]) == 2


def test_verify_reports_a_missing_record(tmp_path: Path) -> None:
    ok, message = verify_example(tmp_path)
    assert ok is False
    assert "expected.yaml" in message
