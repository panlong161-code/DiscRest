"""Product presets and the local studio API."""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import numpy as np

from discrest.audio import write_wav
from discrest.cli import main
from discrest.presets import get_preset, run_preset
from discrest.studio import make_server
from discrest.synthetic import clicked_tone


ROOT = Path(__file__).resolve().parents[1]


def _form(settings: dict, wav: bytes) -> tuple[str, bytes]:
    boundary = "discrestboundary"
    head_settings = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="settings"\r\n\r\n'
    ).encode()
    head_audio = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="audio"; filename="in.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    ).encode()
    body = (
        head_settings
        + json.dumps(settings).encode()
        + b"\r\n"
        + head_audio
        + wav
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return boundary, body


def test_presets_are_listed_and_isolated_repairs_the_public_example(tmp_path: Path) -> None:
    assert main(["presets"]) == 0
    preset = get_preset("isolated")
    assert preset["settings"]["dehiss"]["enabled"] is True
    assert get_preset("protect")["settings"]["declick"]["protect_dense"] is True
    record = run_preset("isolated", ROOT / "examples" / "public_78" / "input.wav", tmp_path)
    assert record["click_count"] == 12
    assert record["flags"] == []
    assert (tmp_path / "restored.wav").is_file()


def test_surface_preset_separates_clicks_and_crackle(tmp_path: Path) -> None:
    record = run_preset("surface", ROOT / "examples" / "surface" / "input.wav", tmp_path)
    assert record["click_count"] == 3
    assert record["crackle_repaired"] == 3
    assert record["removed_rms"]["rumble"] > record["removed_rms"]["dehiss"]


def test_studio_run_returns_playable_audio() -> None:
    rate = 22050
    signal = clicked_tone(rate, 1.2, [4000, 14000], click_amp=0.8, noise=0.005, seed=2)
    wav_path = Path(__file__).resolve().parent / "_studio_input.wav"
    write_wav(wav_path, rate, signal)
    httpd = make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/presets") as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert [item["id"] for item in payload["presets"]] == ["isolated", "protect", "surface"]
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode("utf-8")
        assert "先听被删掉的声音" in page
        assert "声音结构" in page
        boundary, body = _form(payload["presets"][0]["settings"], wav_path.read_bytes())
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/run",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))
        assert result["click_count"] >= 2
        assert result["repaired_count"] >= 2
        assert result["profile"]["preset"] in {"isolated", "protect", "surface"}
        assert "clicks.textgrid" in result["audio"]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{result['audio']['restored.wav']}") as response:
            audio = response.read(12)
        assert audio.startswith(b"RIFF")
        assert np.isfinite(result["removed_rms"]["declick"])
    finally:
        wav_path.unlink(missing_ok=True)
        httpd.shutdown()
        httpd.server_close()
