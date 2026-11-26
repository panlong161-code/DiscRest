"""The audition kit writes boosted removed audio and a readable report."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from discrest.audio import write_wav
from discrest.audition import build, measure
from discrest.synthetic import clicked_tone


def _example(root: Path) -> Path:
    rate = 44100
    clean = clicked_tone(rate, 2.0, [])
    clicked = clicked_tone(rate, 2.0, [int(0.5 * rate), int(1.4 * rate)])
    folder = root / "example"
    out = folder / "out"
    out.mkdir(parents=True)
    write_wav(folder / "input.wav", rate, clicked)
    write_wav(out / "restored.wav", rate, clean)
    write_wav(out / "residual.wav", rate, clicked - clean)
    write_wav(out / "removed_declick.wav", rate, clicked - clean)
    for stage in ("decrackle", "rumble", "hum", "dehiss"):
        write_wav(out / f"removed_{stage}.wav", rate, np.zeros_like(clean))
    return folder


def test_measure_separates_a_running_stage_from_a_silent_one(tmp_path: Path) -> None:
    folder = _example(tmp_path)
    info = measure(folder)
    rows = {row["stage"]: row for row in info["rows"]}
    assert rows["declick"]["active"] is True
    assert rows["declick"]["nonzero"] < 0.05
    assert rows["hum"]["active"] is False
    assert info["delta_db"] < 1.0


def test_build_writes_a_kit_only_for_stages_that_ran(tmp_path: Path) -> None:
    folder = _example(tmp_path)
    info = build(folder)
    listen = folder / "listen"
    assert (listen / "index.html").is_file()
    assert (listen / "report.txt").is_file()
    assert (listen / "4_removed_declick_boosted.wav").is_file()
    assert not (listen / "4_removed_hum_boosted.wav").exists()
    assert not (listen / "3_removed_all_boosted.wav").exists()
    assert (listen / "5_click_zoom_input.wav").is_file()
    text = (listen / "report.txt").read_text(encoding="utf-8")
    assert "declick" in text
    assert info["rate"] == 44100
