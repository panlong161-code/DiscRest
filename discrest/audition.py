"""Build a listening kit for one example directory.

A restored file often differs from its input by less than 1 dB of overall level,
because clicks and hum carry very little energy compared to the music.  Playing
``removed_*.wav`` at unity gain therefore sounds like silence.  This module writes
peak-normalised copies of the removed audio, a short excerpt around the largest
repair, and a spectrogram, so the change can actually be heard and seen.

Nothing here changes the pipeline or the recorded hashes.
"""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

import numpy as np

try:
    import soundfile as sf
except ModuleNotFoundError as exc:  # pragma: no cover - depends on the environment
    raise ModuleNotFoundError(
        "the audition command needs the optional soundfile package: "
        'pip install "discrest[audition]"'
    ) from exc

STAGES = ("declick", "decrackle", "rumble", "hum", "dehiss")
STAGE_LABEL = {
    "declick": "去咔嗒",
    "decrackle": "去裂纹",
    "rumble": "滚降隆隆声",
    "hum": "去交流声",
    "dehiss": "去嘶声",
}
SILENT_DB = -120.0


def _read(path: Path) -> tuple[np.ndarray, int]:
    data, rate = sf.read(str(path), dtype="float64", always_2d=True)
    return data.mean(axis=1), int(rate)


def _db(value: float) -> float:
    return 20.0 * math.log10(max(float(value), 1e-12))


def _rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(float(np.mean(np.square(x)))))


def _band_share(x: np.ndarray, rate: int, low: float, high: float) -> float:
    """Share of power that falls between ``low`` and ``high`` hertz."""
    if x.size == 0:
        return 0.0
    spectrum = np.fft.rfft(x * np.hanning(x.size))
    power = np.abs(spectrum) ** 2
    freqs = np.fft.rfftfreq(x.size, 1.0 / rate)
    total = float(power.sum())
    if total <= 0.0:
        return 0.0
    band = power[(freqs >= low) & (freqs < high)]
    return float(band.sum()) / total


def measure(example_dir: Path) -> dict[str, Any]:
    """Report what each stage removed, in a form that explains audibility."""
    out = example_dir / "out"
    source, rate = _read(example_dir / "input.wav")
    restored, _ = _read(out / "restored.wav")
    rows: list[dict[str, Any]] = []
    for stage in STAGES:
        path = out / f"removed_{stage}.wav"
        if not path.is_file():
            continue
        removed, _ = _read(path)
        level = _db(_rms(removed))
        active = level > SILENT_DB
        rows.append(
            {
                "stage": stage,
                "label": STAGE_LABEL[stage],
                "level_db": level,
                "peak": float(np.abs(removed).max()) if removed.size else 0.0,
                "nonzero": float(np.mean(np.abs(removed) > 1e-6)) if removed.size else 0.0,
                "low_share": _band_share(removed, rate, 0.0, 80.0) if active else 0.0,
                "active": active,
            }
        )
    delta = _db(_rms(source) - 0.0) - _db(_rms(restored)) if restored.size else 0.0
    return {
        "rate": rate,
        "seconds": len(source) / rate if rate else 0.0,
        "input_db": _db(_rms(source)),
        "restored_db": _db(_rms(restored)),
        "delta_db": delta,
        "rows": rows,
    }


def _verdict(row: dict[str, Any]) -> str:
    if not row["active"]:
        return "这一级没有运行，文件是整段静音"
    if row["low_share"] > 0.6:
        return "能量集中在 80 Hz 以下，笔记本扬声器放不出来，需耳机或看频谱"
    if row["nonzero"] < 0.02:
        return "极稀疏脉冲，顺序播放几乎听不到，见放大版与片段"
    if row["level_db"] > -30.0:
        return "可以直接听见"
    return "偏弱，建议用放大版试听"


def _write(path: Path, rate: int, signal: np.ndarray) -> None:
    peak = float(np.abs(signal).max()) if signal.size else 0.0
    if peak > 0.999:
        signal = signal * (0.999 / peak)
    sf.write(str(path), signal.astype(np.float32), rate, subtype="PCM_16")


def _normalise(signal: np.ndarray, target: float = 0.89) -> tuple[np.ndarray, float]:
    peak = float(np.abs(signal).max()) if signal.size else 0.0
    if peak <= 0.0:
        return signal, 0.0
    gain = target / peak
    return signal * gain, _db(gain)


def _spectrogram(signal: np.ndarray, rate: int, rows: int, cols: int):
    from scipy.signal import spectrogram

    nperseg = min(4096, max(256, signal.size // 16))
    freqs, times, spec = spectrogram(signal, fs=rate, nperseg=nperseg, noverlap=nperseg * 3 // 4)
    spec_db = 10.0 * np.log10(np.maximum(spec, 1e-20))
    return freqs, times, spec_db


def _plot(example_dir: Path, rate: int, curves: list[tuple[str, np.ndarray]], target: Path) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    from scipy.signal import welch

    figure, axes = plt.subplots(len(curves) + 1, 1, figsize=(11, 2.6 * (len(curves) + 1)), sharex=False)
    for axis, (title, signal) in zip(axes[:-1], curves):
        freqs, times, spec_db = _spectrogram(signal, rate, len(curves), 1)
        top = min(8000.0, rate / 2.0)
        band = freqs <= top
        axis.pcolormesh(times, freqs[band], spec_db[band], shading="auto", cmap="magma", vmin=-120, vmax=-20)
        axis.set_ylabel("Hz")
        axis.set_title(title, loc="left", fontsize=10)
        axis.set_ylim(0, top)
    for axis in axes[:-1]:
        axis.set_xlim(0, curves[0][1].size / rate if rate else 1.0)

    low = axes[-1]
    for title, signal in curves:
        freqs, power = welch(signal, fs=rate, nperseg=min(16384, max(1024, signal.size // 4)))
        keep = freqs <= 500.0
        low.semilogx(freqs[keep], 10.0 * np.log10(np.maximum(power[keep], 1e-22)), linewidth=1.0, label=title)
    low.set_xlim(10.0, 500.0)
    low.set_xlabel("frequency (Hz, log)")
    low.set_ylabel("dB/Hz")
    low.set_title("average spectrum, low band", loc="left", fontsize=10)
    low.grid(True, which="both", alpha=0.25)
    low.legend(fontsize=8, loc="upper right")
    figure.tight_layout()
    figure.savefig(str(target), dpi=110)
    plt.close(figure)
    return True


def build(example_dir: Path, listen_dir: Path | None = None) -> dict[str, Any]:
    """Write the listening kit and return the measurements behind it."""
    example_dir = Path(example_dir)
    info = measure(example_dir)
    listen_dir = Path(listen_dir) if listen_dir else example_dir / "listen"
    listen_dir.mkdir(parents=True, exist_ok=True)
    rate = info["rate"]
    out = example_dir / "out"

    source, _ = _read(example_dir / "input.wav")
    restored, _ = _read(out / "restored.wav")
    _write(listen_dir / "1_input.wav", rate, source)
    _write(listen_dir / "2_restored.wav", rate, restored)

    removal = source[: restored.size] - restored
    active = [row for row in info["rows"] if row["active"]]
    written: list[tuple[str, str, float]] = []
    if len(active) > 1:
        boosted, gain_db = _normalise(removal)
        _write(listen_dir / "3_removed_all_boosted.wav", rate, boosted)
        written.append(("3_removed_all_boosted.wav", "全部移除量", gain_db))
    for row in active:
        signal, stage_gain = _normalise(_read(out / f"removed_{row['stage']}.wav")[0])
        name = f"4_removed_{row['stage']}_boosted.wav"
        _write(listen_dir / name, rate, signal)
        written.append((name, row["label"], stage_gain))

    zoom_names: list[str] = []
    if removal.size and float(np.abs(removal).max()) > 0.0:
        centre = int(np.argmax(np.abs(removal)))
        half = int(0.8 * rate)
        start = max(0, centre - half)
        stop = min(source.size, centre + half)
        _write(listen_dir / "5_click_zoom_input.wav", rate, source[start:stop])
        _write(listen_dir / "6_click_zoom_restored.wav", rate, restored[start:stop])
        _write(listen_dir / "7_click_zoom_removed_boosted.wav", rate, _normalise(removal[start:stop])[0])
        zoom_names = ["5_click_zoom_input.wav", "6_click_zoom_restored.wav", "7_click_zoom_removed_boosted.wav"]

    curves = [
        ("input", source),
        ("restored", restored),
        ("input minus restored, peak normalised", removal),
    ]
    has_plot = _plot(example_dir, rate, curves, listen_dir / "8_spectrum.png")

    rows_html = []
    for row in info["rows"]:
        state = "运行" if row["active"] else "未运行"
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(row['label'])}</td>"
            f"<td>{state}</td>"
            f"<td>{row['level_db']:.1f}</td>"
            f"<td>{row['nonzero'] * 100:.2f}%</td>"
            f"<td>{row['low_share'] * 100:.0f}%</td>"
            f"<td>{html.escape(_verdict(row))}</td>"
            "</tr>"
        )

    players = [
        '<div class="lane"><b>1 原声</b><audio controls preload="none" src="1_input.wav"></audio></div>',
        '<div class="lane"><b>2 修复</b><audio controls preload="none" src="2_restored.wav"></audio></div>',
    ]
    for name, label, gain in written:
        players.append(
            f'<div class="lane"><b>{html.escape(label)}（增益 +{gain:.0f} dB）</b>'
            f'<audio controls preload="none" src="{name}"></audio></div>'
        )
    if zoom_names:
        players.append(
            '<div class="lane"><b>5/6/7 最大一处修复的 1.6 秒片段：原声 / 修复 / 移除量（放大）</b>'
            '<audio controls preload="none" src="5_click_zoom_input.wav"></audio>'
            '<audio controls preload="none" src="6_click_zoom_restored.wav"></audio>'
            '<audio controls preload="none" src="7_click_zoom_removed_boosted.wav"></audio>'
            "</div>"
        )

    plot_html = '<p><img src="8_spectrum.png" alt="spectrogram"></p>' if has_plot else ""
    page = f"""<!DOCTYPE html>
<html lang="zh">
<meta charset="utf-8">
<title>{html.escape(example_dir.name)} 试听</title>
<style>
 body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; margin: 28px auto; max-width: 960px; color: #1a1a1a; background: #fbfbfb; line-height: 1.6; }}
 h1 {{ font-size: 20px; margin: 0 0 4px; }}
 p.lead {{ color: #555; margin-top: 0; }}
 .lane {{ background: #fff; border: 1px solid #e3e3e3; border-radius: 8px; padding: 10px 12px; margin: 8px 0; }}
 .lane audio {{ display: block; width: 100%; margin-top: 6px; }}
 table {{ border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 13px; }}
 th, td {{ border-bottom: 1px solid #e6e6e6; padding: 6px 8px; text-align: left; }}
 th {{ background: #f2f2f2; font-weight: 600; }}
 img {{ max-width: 100%; border: 1px solid #e3e3e3; border-radius: 6px; }}
 .note {{ background: #fff8e6; border: 1px solid #f0e0b0; border-radius: 8px; padding: 10px 12px; font-size: 13px; }}
</style>
<h1>{html.escape(example_dir.name)}</h1>
<p class="lead">{info['seconds']:.1f} s, {rate} Hz. 原声平均电平 {info['input_db']:.1f} dBFS，修复后 {info['restored_db']:.1f} dBFS，整体相差 {info['delta_db']:.2f} dB。</p>
<div class="note">整体电平几乎不变是正常结果：咔嗒、交流声在总能量里占比很小。要听出变化，看下面被放大过的“移除量”，或直接听 1.6 秒片段。</div>
{''.join(players)}
<h2 style="font-size:16px;margin-top:22px">各级读数</h2>
<table>
<tr><th>级</th><th>状态</th><th>移除量 dBFS</th><th>非零样本</th><th>80 Hz 以下能量</th><th>判断</th></tr>
{''.join(rows_html)}
</table>
{plot_html}
<p class="lead">放大版只调整增益，波形形状未改；dB 增益标在播放器上方。</p>
</html>
"""
    (listen_dir / "index.html").write_text(page, encoding="utf-8")

    lines = [
        f"{example_dir.name}: {info['seconds']:.1f} s, {rate} Hz",
        f"input {info['input_db']:.1f} dBFS, restored {info['restored_db']:.1f} dBFS, delta {info['delta_db']:+.2f} dB",
        "",
    ]
    for row in info["rows"]:
        lines.append(
            f"{row['stage']:10} {'on ' if row['active'] else 'off'} "
            f"{row['level_db']:7.1f} dBFS  nonzero {row['nonzero'] * 100:5.2f}%  "
            f"below80 {row['low_share'] * 100:5.1f}%  {_verdict(row)}"
        )
    (listen_dir / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    info["listen_dir"] = listen_dir
    info["has_plot"] = has_plot
    return info
