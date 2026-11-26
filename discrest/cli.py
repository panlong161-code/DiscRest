"""Command line: ``run`` one config, or ``verify`` a recorded example."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from discrest import __version__
from discrest.config import ConfigError, load_config
from discrest.pipeline import run_config, verify_example
from discrest.presets import PRESETS, run_preset
from discrest.profile import profile_file
from discrest.studio import serve


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="discrest",
        description="Local stepwise restoration for digitized disc recordings.",
    )
    parser.add_argument("--version", action="version", version=f"DiscRest {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="restore a wav from a config file or a product preset")
    run_parser.add_argument("--config", help="path to run.yaml")
    run_parser.add_argument("--preset", help="isolated, protect, or surface")
    run_parser.add_argument("--input", help="wav used with --preset")
    run_parser.add_argument("--output-dir", default="out", help="directory for preset output")

    verify_parser = commands.add_parser("verify", help="re-run an example and compare recorded hashes")
    verify_parser.add_argument("example_dir", help="directory containing run.yaml and expected.yaml")

    commands.add_parser("presets", help="list product modes")

    audition_parser = commands.add_parser(
        "audition", help="write boosted removed audio and a spectrogram for an example"
    )
    audition_parser.add_argument("example_dir", help="directory containing input.wav and out/")
    audition_parser.add_argument("--listen-dir", help="where to write the listening kit")

    profile_parser = commands.add_parser("profile", help="measure the file and suggest a preset")
    profile_parser.add_argument("--input", required=True, help="wav to measure; no audio is written")

    ui_parser = commands.add_parser("ui", help="open the local listening bench")
    ui_parser.add_argument("--port", type=int, default=8765)
    ui_parser.add_argument("--no-browser", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = _build()
    args = parser.parse_args(argv)
    try:
        if args.command == "presets":
            for item in PRESETS:
                print(f"{item['id']:12} {item['cli']}")
            return 0
        if args.command == "profile":
            report = profile_file(args.input)
            reasons = ", ".join(report["reasons"])
            print(f"click_rate: {report['click_rate']}")
            print(f"rumble_ratio: {report['rumble_ratio']}")
            print(f"hum_prominence: {report['hum_prominence']}")
            print(f"preset: {report['preset']}")
            print(f"reasons: {reasons}")
            return 0
        if args.command == "ui":
            serve(port=args.port, open_browser=not args.no_browser)
            return 0
        if args.command == "audition":
            from discrest.audition import build

            info = build(Path(args.example_dir), Path(args.listen_dir) if args.listen_dir else None)
            print(f"seconds: {info['seconds']:.1f}")
            print(f"input: {info['input_db']:.1f} dBFS")
            print(f"restored: {info['restored_db']:.1f} dBFS")
            print(f"delta: {info['delta_db']:+.2f} dB")
            for row in info["rows"]:
                state = "on" if row["active"] else "off"
                print(
                    f"{row['stage']:10} {state:3} {row['level_db']:8.1f} dBFS "
                    f"nonzero={row['nonzero'] * 100:.2f}% below80={row['low_share'] * 100:.0f}%"
                )
            print(f"listen: {info['listen_dir'] / 'index.html'}")
            return 0
        if args.command == "run":
            if args.preset:
                if not args.input:
                    print("error: --input is required with --preset", file=sys.stderr)
                    return 2
                record = run_preset(args.preset, Path(args.input), Path(args.output_dir))
            elif args.config:
                record = run_config(load_config(args.config))
            else:
                print("error: pass --config or --preset", file=sys.stderr)
                return 2
            flags = ", ".join(record["flags"]) if record["flags"] else "none"
            print(f"clicks: {record['click_count']}")
            print(f"repaired: {record['repaired_count']}")
            print(f"protected: {record['protected_count']}")
            print(f"flags: {flags}")
            profile = record["profile"]
            print(f"profile: {profile['preset']} ({', '.join(profile['reasons'])})")
            print(f"restored: {record['output_dir']}\\restored.wav")
            print(f"residual: {record['output_dir']}\\residual.wav")
            print(f"record: {record['output_dir']}\\run.yaml")
            return 0
        ok, message = verify_example(args.example_dir)
        print(message)
        return 0 if ok else 1
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
