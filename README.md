# DiscRest

DiscRest is a local workbench for recordings that have already been digitized. Five stages can be switched independently: declick, decrackle, a rumble high-pass, a mains-hum notch, and dehiss. Each run writes the restored signal, the full residual, the audio removed by each stage, a click table with a reason for every region, and a frozen configuration. Audio stays on the machine that runs the command.

Version 0.7.0. License: MIT. The three presets and the local studio share the command-line settings. `profile` suggests a preset before any audio is written. When a measurement sits near a threshold, the profile is marked not confident.

The public example is `examples/archive_78`, a 20-second excerpt from an unrestored 1919 cylinder. The same excerpt is counted with a reimplementation of the Audacity 2.1 `RemoveClicks` algorithm. That count is not a session in the Audacity application.

## Install

```text
pip install -e ".[dev]"
```

To run the examples without the test tools, install NumPy, SciPy, and PyYAML, then use `python -m discrest`.

## Reproduce

```text
python -m discrest verify examples/archive_78
python -m discrest verify examples/surface
python -m discrest verify examples/public_78
python -m discrest verify examples/dense_transient
```

`verify` checks that the output files exist and that the click count and flags match `expected.yaml`. SHA-256 hashes are compared on the platform that recorded them: Windows, Python 3.12.7, NumPy 1.26.4, SciPy 1.16.3. On another platform the command still checks the counts and flags, and it prints `hashes_recorded_on=win32`.

## Presets

| Preset | Use when | Stages enabled |
| --- | --- | --- |
| `isolated` | Clicks are separated | Declick and dehiss |
| `protect` | Drum hits or dense crackle may be marked as clicks | Declick only; dense windows are not replaced |
| `surface` | Rumble, hum, and fine crackle | Declick, decrackle, high-pass, and notch |

```text
python -m discrest presets
python -m discrest profile --input examples/public_78/input.wav
python -m discrest run --preset isolated --input examples/public_78/input.wav --output-dir out
python -m discrest ui
```

`profile` measures and writes no audio. It reports clicks per second, the share of power below 40 Hz, and how far the 50 Hz or 60 Hz harmonics stand out, then suggests `isolated`, `protect`, or `surface`.

`ui` listens on this machine only. Files longer than 180 seconds are processed with the command line.

## Examples

`examples/archive_78` is the paper example. Seconds 98–118 of the unrestored 1919 Edison Blue Amberol transfer are processed with the protect preset. The run lists 149 regions: 82 repaired as `isolated-click`, 66 left in place as `dense-transient`, and 1 left in place as `sustained-onset`. Provenance and the United States public-domain limit are in that directory's README.

`examples/public_78` is an 8-second synthetic tone with 12 isolated clicks. Declick and dehiss are on. The run repairs 12 regions.

`examples/dense_transient` places an impulse every 80 samples for one second. The run lists 726 short regions. 701 fall in dense windows and stay in place. 25 are repaired. 13 regions longer than 3 ms are not replaced. The flag is `dense-transient`.

`examples/surface` is a 4-second synthetic tone with 30 Hz rumble, 50 Hz and 150 Hz hum, 3 clicks, and 3 smaller crackles. The run repairs 3 click regions and 3 crackles. In `out/run.yaml` the rumble removed RMS is about 0.094 and the hum removed RMS is about 0.021.

## Outputs

| File | Contents |
| --- | --- |
| `restored.wav` | 16-bit restored signal |
| `residual.wav` | Input minus output |
| `removed_declick.wav` and four siblings | Audio removed by one stage |
| `clicks.csv` | Channel, region, time, `repaired` or `protected`, reason, and error score |
| `clicks.textgrid` | The same regions as a Praat interval tier |
| `run.yaml` | Input hash, sample rate, settings, profile, per-stage leakage, removed RMS, and output hashes |
| `log.txt` | Click, protection, crackle, and flag counts |

Sample-rate policy: `native` keeps the file rate, `require` stops when the rate is not `expected_sample_rate`, and `resample` converts to that rate while recording the original rate.

## Processing order

Declick, then decrackle, then the rumble high-pass, then the hum notch, then dehiss. Impulses are repaired before the zero-phase filters, because those filters spread a click into ringing that the click detector would count again.

A short region whose following 30 ms is much louder than the preceding 30 ms is marked `sustained-onset` and left in place. If the rumble, hum, or dehiss stage removes energy that still belongs to the remaining musical band, that whole stage is reverted and the log records `leakage-reverted`.

`neural.enabled: true` requires a local checkpoint. This version ships no neural weights. The command stops when the file is missing.

## Support

The SoftwareX code-metadata table needs the corresponding author's email. That address is not in this repository yet. Until it is added, questions can be opened at https://github.com/panlong161-code/DiscRest/issues.

The code for version 0.7.0 is https://github.com/panlong161-code/DiscRest/tree/v0.7.0.

Godsill SJ, Rayner PJW. Digital Audio Restoration. Springer; 1998. https://doi.org/10.1007/978-1-4471-1561-8

Moliner E, Välimäki V. A two-stage U-Net for high-fidelity denoising of historical recordings. IEEE ICASSP; 2022. https://doi.org/10.1109/ICASSP43922.2022.9746977

## Tests

```text
pytest
```
