# DiscRest

DiscRest is a local workbench for recordings that have already been digitized. Five stages can be switched independently: declick, decrackle, a rumble high-pass, a mains-hum notch, and dehiss. Each run writes the restored signal, the full residual, the audio removed by each stage, a click table with a reason for every region, and a frozen configuration. Audio stays on the machine that runs the command.

Version 0.8.1. License: MIT. The three presets and the local studio share the command-line settings. `profile` suggests a preset before any audio is written. When a measurement sits near a threshold, the profile is marked not confident.

The public example is `examples/archive_78`, a 20-second excerpt from an unrestored 1919 cylinder. The same excerpt is counted with a reimplementation of the Audacity 2.1.0 `RemoveClicks` algorithm. That count is not a session in the Audacity application. Four bundled inputs are archival recordings; `examples/loc_victor_78` is derived from a Library of Congress transfer with controlled synthetic impairments added by `overlay.py`.

## Install

```text
pip install -e ".[dev]"
```

To run the examples without the test tools, install NumPy, SciPy, and PyYAML, then use `python -m discrest`.

## Reproduce

```text
python -m discrest verify examples/archive_78
python -m discrest verify examples/surface
python -m discrest verify examples/public_cyl
python -m discrest verify examples/dense_transient
python -m discrest verify examples/loc_victor_78
```

`verify` checks that the output files exist and that the click count and flags match `expected.yaml`. SHA-256 hashes are compared only when the platform, Python, NumPy, and SciPy versions match the recorded environment (Windows, Python 3.12.4, NumPy 2.0.0, SciPy 1.17.1). Otherwise the command checks the counts and flags, and reports the platform on which hashes were recorded.

## Paper supplement

The controlled click-detection noise sweep is in `supplementary/noise_sensitivity_sweep.py`:

```text
python supplementary/noise_sensitivity_sweep.py
```

It uses a synthetic 440 Hz tone with 12 clicks across five noise levels and three seeds. The results describe detector behavior in this controlled signal only; they are not a listening study or evidence of perceptual quality on real recordings.

## Presets

| Preset | Use when | Stages enabled |
| --- | --- | --- |
| `isolated` | Clicks are separated | Declick and dehiss |
| `protect` | Drum hits or dense crackle may be marked as clicks | Declick only; dense windows are not replaced |
| `surface` | Rumble, hum, and fine crackle | Declick, decrackle, high-pass, and notch |

```text
python -m discrest presets
python -m discrest profile --input examples/public_cyl/input.wav
python -m discrest run --preset isolated --input examples/public_cyl/input.wav --output-dir out
python -m discrest ui
```

`profile` measures and writes no audio. It reports clicks per second, the share of power below 40 Hz, and how far the 50 Hz or 60 Hz harmonics stand out, then suggests `isolated`, `protect`, or `surface`.

`ui` listens on this machine only. Files longer than 180 seconds are processed with the command line.

## Examples

`examples/archive_78` is the paper example. Seconds 98–118 of the unrestored 1919 Edison Blue Amberol transfer are processed with the protect preset. The run lists 149 regions: 82 repaired as `isolated-click`, 66 left in place as `dense-transient`, and 1 left in place as `sustained-onset`. Provenance and the United States public-domain limit are in that directory's README.

`examples/public_cyl` is 20 seconds of the 1910 Edison Amberol 473 transfer of “My south polar expedition”, UCSB cylinder 1859. Declick is on. The archive's access copy has already been filtered below 40 Hz, so the run repairs all 14 regions and raises no flag; the low-frequency stages are exercised on `examples/loc_victor_78` instead.

`examples/dense_transient` is 17.4 seconds of a worn 1906 Columbia cylinder, “‘Tis but a dream”, UCSB 13692. The run lists 552 regions, protects 485 in 45 dense windows, and repairs 67. 28 regions longer than 3 ms are not replaced. The flag is `dense-transient`.

`examples/surface` is 20 seconds of a real 78 rpm transfer with strong mains hum, Freesound 18627 under CC0. The 50 Hz notch and decrackle run: hum prominence falls from 33.88 to 1.19, 7 crackles are repaired, and no flag is raised. The high-pass stays off because the file has nothing below 40 Hz to remove.

`examples/loc_victor_78` exercises the rumble, hum, and dehiss stages on a real Library of Congress transfer of Victor 73978 (matrix B-28269). Seconds 38–68 are kept. The delivered file is a master with the low band already filtered, so `overlay.py` adds low-frequency, mains, and broadband noise at the levels it reports; the untouched base is kept next to the sum, which is what allows a true SNR to be computed. `profile` reports `low-frequency, mains-hum`. The run takes `rumble_ratio` from 0.1781 to 0.0006 and `hum_prominence` from 11.96 to 1.60, with the hum leakage guard held off by `occupied = 0.0000`. The dehiss stage is a negative result on this material: SNR falls from 20.00 to 15.32 dB because the span has no quiet frames for the noise estimate. Details are in that directory's README.

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

## Hearing what was removed

Two things make the repair hard to hear, and neither is a fault in the run:

1. `removed_*.wav` is written for all five stages, including the stages that were off. A stage that did not run writes exact zeros, so `removed_hum.wav` from `examples/archive_78` is silent because the hum stage was off, not because hum was absent from the audio.
2. What a working stage removes is small next to the music. On `examples/archive_78` the declick stage removes 0.49% of the samples at −47 dBFS, so `restored.wav` and `input.wav` differ by 0.02 dB overall. On `examples/loc_victor_78` the rumble stage removes 0.064 RMS, the output is 2.5 dB quieter, and the difference sits below 80 Hz where laptop speakers do not reproduce anything.

`audition` writes a listening kit for one example. It peak-normalises the removed audio, cuts 1.6 s around the largest repair, and plots a spectrogram:

```text
python -m discrest audition examples/archive_78
```

The kit lands in `examples/archive_78/listen/`: `4_removed_<stage>_boosted.wav` for every stage that ran, `5`–`7` for the excerpt (input, restored, removed), `8_spectrum.png`, and `index.html` with players and the per-stage levels. Gain is printed on the page; the waveform is not altered in any other way.

`audition` is the only command with an extra dependency: it needs `soundfile`, installed with `pip install "discrest[audition]"`. The five processing stages themselves need only NumPy, SciPy, and PyYAML.

## Processing order

Declick, then decrackle, then the rumble high-pass, then the hum notch, then dehiss. Impulses are repaired before the zero-phase filters, because those filters spread a click into ringing that the click detector would count again.

A short region whose following 30 ms is much louder than the preceding 30 ms is marked `sustained-onset` and left in place. If the rumble, hum, or dehiss stage removes energy that still belongs to the remaining musical band, that whole stage is reverted and the log records `leakage-reverted`.

`neural.enabled: true` requires a local checkpoint. This version ships no neural weights. The command stops when the file is missing.

## Support

Questions and support inquiries can be directed to Long Pan (`540432274@qq.com`) or opened at https://github.com/panlong161-code/DiscRest/issues.

The code for version 0.8.1 is https://github.com/panlong161-code/DiscRest/tree/v0.8.1.

Godsill SJ, Rayner PJW. Digital Audio Restoration. Springer; 1998. https://doi.org/10.1007/978-1-4471-1561-8

Moliner E, Välimäki V. A two-stage U-Net for high-fidelity denoising of historical recordings. IEEE ICASSP; 2022. https://doi.org/10.1109/ICASSP43922.2022.9746977

## Tests

```text
pytest
```
