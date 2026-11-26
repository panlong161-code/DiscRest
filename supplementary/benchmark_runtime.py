"""Measure example runtimes without modifying the bundled example outputs."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import scipy
import yaml

from discrest.audio import read_wav
from discrest.config import load_config
from discrest.pipeline import run_config


EXAMPLES = (
    "archive_78",
    "public_cyl",
    "dense_transient",
    "surface",
    "loc_victor_78",
)


def processor_name() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            with key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    return platform.processor()


def measure(example_name: str, repetitions: int) -> dict[str, Any]:
    example = ROOT / "examples" / example_name
    raw_config = yaml.safe_load((example / "run.yaml").read_text(encoding="utf-8"))
    input_path = (example / raw_config["input"]).resolve()
    raw_config["input"] = str(input_path)

    durations: list[float] = []
    with tempfile.TemporaryDirectory(prefix=f"discrest-{example_name}-") as temporary:
        scratch = Path(temporary)
        config_path = scratch / "run.yaml"
        for repeat in range(repetitions):
            raw_config["output_dir"] = str(scratch / f"out-{repeat + 1}")
            config_path.write_text(
                yaml.safe_dump(raw_config, sort_keys=False),
                encoding="utf-8",
            )
            config = load_config(config_path)
            start = time.perf_counter()
            record = run_config(config)
            durations.append(time.perf_counter() - start)

            expected = yaml.safe_load(
                (example / "expected.yaml").read_text(encoding="utf-8")
            )
            for key in ("click_count", "flags"):
                if record[key] != expected[key]:
                    raise RuntimeError(
                        f"{example_name}: {key} mismatch on repetition "
                        f"{repeat + 1}: {record[key]!r} != {expected[key]!r}"
                    )
            output = Path(record["output_dir"])
            required = (
                "restored.wav",
                "residual.wav",
                "clicks.csv",
                "clicks.textgrid",
                "log.txt",
                "run.yaml",
            )
            if not all((output / name).is_file() for name in required):
                raise RuntimeError(f"{example_name}: incomplete run artifacts")

    sample_rate, samples = read_wav(input_path)
    seconds = samples.shape[0] / sample_rate
    median_seconds = statistics.median(durations)
    return {
        "example": example_name,
        "duration_s": seconds,
        "repetitions": repetitions,
        "runs_s": [round(value, 6) for value in durations],
        "median_s": median_seconds,
        "speed_x_real_time": seconds / median_seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="CSV destination; a JSON metadata sidecar is written beside it",
    )
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.repetitions < 3:
        parser.error("--repetitions must be at least 3")

    results = [measure(name, args.repetitions) for name in EXAMPLES]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "example",
                "duration_s",
                "repetitions",
                "runs_s",
                "median_s",
                "speed_x_real_time",
            ),
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    **result,
                    "runs_s": ";".join(f"{value:.6f}" for value in result["runs_s"]),
                    "duration_s": f"{result['duration_s']:.3f}",
                    "median_s": f"{result['median_s']:.6f}",
                    "speed_x_real_time": f"{result['speed_x_real_time']:.3f}",
                }
            )

    metadata = {
        "platform": platform.platform(),
        "processor": processor_name(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pyyaml": yaml.__version__,
        "timing_scope": (
            "run_config only; includes artifact writing and SHA-256 hashing, "
            "excludes interpreter startup and imports"
        ),
        "results": results,
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    for result in results:
        print(
            f"{result['example']}: median={result['median_s']:.3f} s; "
            f"{result['speed_x_real_time']:.2f}x real time"
        )
    print(f"CSV: {args.output.resolve()}")
    print(f"JSON: {args.output.with_suffix('.json').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
