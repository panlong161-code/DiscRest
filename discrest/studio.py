"""Local listening bench. Audio is processed on this machine only."""

from __future__ import annotations

import json
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from discrest import __version__
from discrest.config import ConfigError
from discrest.presets import EXAMPLES, public_presets, run_with_settings

_PAGE = Path(__file__).with_name("studio.html").read_text(encoding="utf-8")
_MAX_BODY = 32 * 1024 * 1024
_MAX_SECONDS = 180
_JOBS: dict[str, dict[str, Path]] = {}
_JOB_ORDER: list[str] = []
_LOCK = threading.Lock()


def examples_root() -> Path:
    root = Path(__file__).resolve().parents[1] / "examples"
    if not root.is_dir():
        raise ConfigError("examples directory is missing")
    return root


def parse_multipart(content_type: str, body: bytes) -> dict[str, tuple[str | None, bytes]]:
    marker = "boundary="
    if marker not in content_type:
        raise ConfigError("expected a multipart form")
    boundary = content_type.split(marker, 1)[1].strip().strip('"')
    if ";" in boundary:
        boundary = boundary.split(";", 1)[0].strip().strip('"')
    token = boundary.encode("utf-8")
    if body.startswith(b"--" + token):
        body = b"\r\n" + body
    found: dict[str, tuple[str | None, bytes]] = {}
    for raw in body.split(b"\r\n--" + token):
        if not raw or raw.startswith(b"--"):
            continue
        chunk = raw[2:] if raw.startswith(b"\r\n") else raw
        header_blob, sep, data = chunk.partition(b"\r\n\r\n")
        if not sep:
            continue
        header = header_blob.decode("utf-8", errors="replace")
        name = None
        filename = None
        for line in header.split("\r\n"):
            if "content-disposition" not in line.lower():
                continue
            for piece in line.split(";"):
                piece = piece.strip()
                if piece.startswith("name="):
                    name = piece.split("=", 1)[1].strip().strip('"')
                elif piece.startswith("filename="):
                    filename = piece.split("=", 1)[1].strip().strip('"')
        if name:
            found[name] = (filename, data)
    return found


def _click_preview(path: Path, limit: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:
        channel, start, end, time_sec, action, reason, score = line.split(",")
        rows.append(
            {
                "channel": int(channel),
                "start": int(start),
                "end": int(end),
                "time": float(time_sec),
                "action": action,
                "reason": reason,
                "score": float(score),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _remember(job_id: str, files: dict[str, Path]) -> None:
    with _LOCK:
        _JOBS[job_id] = files
        _JOB_ORDER.append(job_id)
        while len(_JOB_ORDER) > 8:
            old = _JOB_ORDER.pop(0)
            previous = _JOBS.pop(old, None)
            if not previous:
                continue
            folder = previous["input"].parent
            for path in folder.rglob("*"):
                if path.is_file():
                    path.unlink(missing_ok=True)
            for path in sorted(folder.rglob("*"), reverse=True):
                if path.is_dir():
                    path.rmdir()
            folder.rmdir()


class StudioHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = f"DiscRest/{__version__}"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Connection", "close")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            page = _PAGE.replace("__VERSION__", __version__)
            self._send_bytes(200, page.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/presets":
            self._send(200, {"version": __version__, "presets": public_presets()})
            return
        if path.startswith("/api/examples/"):
            name = path.removeprefix("/api/examples/").removesuffix(".wav")
            if name not in EXAMPLES:
                self._send(404, {"error": "unknown example"})
                return
            wav = examples_root() / name / "input.wav"
            if not wav.is_file():
                self._send(404, {"error": "example wav is missing"})
                return
            self._send_bytes(200, wav.read_bytes(), "audio/wav")
            return
        if path.startswith("/jobs/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) != 3 or parts[0] != "jobs":
                self._send(404, {"error": "missing file"})
                return
            job_id, leaf = parts[1], parts[2]
            with _LOCK:
                files = _JOBS.get(job_id)
            if not files or leaf not in files:
                self._send(404, {"error": "job expired"})
                return
            target = files[leaf]
            kind = "audio/wav" if leaf.endswith(".wav") else "text/plain; charset=utf-8"
            if leaf.endswith(".yaml") or leaf.endswith(".csv"):
                kind = "text/plain; charset=utf-8"
            self._send_bytes(200, target.read_bytes(), kind)
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/run":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, {"error": "bad content length"})
            return
        if length <= 0 or length > _MAX_BODY:
            self._send(413, {"error": "音频需要小于 32 MB。更长的文件请用命令行。"})
            return
        body = self.rfile.read(length)
        try:
            form = parse_multipart(self.headers.get("Content-Type", ""), body)
            if "audio" not in form or "settings" not in form:
                raise ConfigError("need audio and settings")
            settings = json.loads(form["settings"][1].decode("utf-8"))
            if not isinstance(settings, dict):
                raise ConfigError("settings must be an object")
            job_id = uuid.uuid4().hex
            folder = Path(tempfile_job(job_id))
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "input.wav").write_bytes(form["audio"][1])
            from discrest.audio import read_wav

            rate, samples = read_wav(folder / "input.wav")
            seconds = samples.shape[0] / float(rate)
            if seconds > _MAX_SECONDS:
                raise ConfigError("工作室单次最多处理 180 秒。更长的文件请用 discrest run。")
            record = run_with_settings(settings, folder / "input.wav", folder / "out", source="studio")
        except (ConfigError, json.JSONDecodeError, OSError, ValueError) as exc:
            self._send(400, {"error": str(exc)})
            return
        out = Path(record["output_dir"])
        files = {
            "input.wav": folder / "input.wav",
            "restored.wav": out / "restored.wav",
            "residual.wav": out / "residual.wav",
            "clicks.csv": out / "clicks.csv",
            "run.yaml": out / "run.yaml",
            "log.txt": out / "log.txt",
            "clicks.textgrid": out / "clicks.textgrid",
        }
        for stage in ("declick", "decrackle", "rumble", "hum", "dehiss"):
            files[f"removed_{stage}.wav"] = out / f"removed_{stage}.wav"
        _remember(job_id, files)
        self._send(
            200,
            {
                "job": job_id,
                "click_count": record["click_count"],
                "repaired_count": record["repaired_count"],
                "protected_count": record["protected_count"],
                "crackle_repaired": record["crackle_repaired"],
                "crackle_protected": record["crackle_protected"],
                "rejected_long_regions": record["rejected_long_regions"],
                "flags": record["flags"],
                "removed_rms": record["removed_rms"],
                "profile": record["profile"],
                "leakage": record["leakage"],
                "clicks": _click_preview(files["clicks.csv"]),
                "audio": {name: f"/jobs/{job_id}/{name}" for name in files},
            },
        )


def tempfile_job(job_id: str) -> str:
    root = Path(__file__).resolve().parents[1] / ".studio-jobs"
    root.mkdir(exist_ok=True)
    return str(root / job_id)


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost"}:
        raise ConfigError("the studio listens on this machine only")
    return ThreadingHTTPServer((host, port), StudioHandler)


def serve(host: str = "127.0.0.1", port: int = 8765, *, open_browser: bool = False) -> None:
    httpd = make_server(host, port)
    bound = httpd.server_address[1]
    url = f"http://127.0.0.1:{bound}/"
    print(f"DiscRest studio {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
