# A real 78 rpm transfer with mains hum

This example runs the mains notch and the crackle stage on a real 78 rpm transfer.

## Source

Freesound sound 18627, “78 rpm.aif”, uploaded by Walter_Odington, released under CC0
<https://freesound.org/s/18627/>. The full file is 175 s at 44100 Hz; its 99% energy
boundary is 3588 Hz and its hum prominence is 30.05, so the 50 Hz line and its harmonics
stand well above the surrounding floor. `input.wav` keeps seconds 8.000–28.000, 20.000 s,
mono, with the DC offset removed.

This is a personal upload, not an institutional transfer. It is good evidence that the
recording is real and the hum is real; it is not evidence of which disc, year, or label it
came from, and this repository does not claim that.

## What the run does

`profile` reports 0.05 clicks per second, a rumble ratio of 0.0000, a hum prominence of
33.88, preset `surface` with reason `mains-hum`, and `confident: true`.

`run.yaml` enables the 50 Hz notch with four harmonics at Q 30, and decrackle at threshold
3.0. Two stages stay off:

- **dehiss.** The transfer is continuous music with no quiet frame, and the stage estimates
  its noise floor from the quietest 15% of frames. On such material it lowers the high band
  while raising the total error; see `examples/loc_victor_78/README.md` for the measurement.
- **the 80 Hz high-pass.** `rumble_ratio` is 0.0000, so there is nothing below 40 Hz to
  remove and a high-pass would only take music with it.

| Quantity | Value |
|---|---|
| hum prominence before → after | 33.88 → 1.19 |
| crackles repaired / protected | 7 / 0 |
| flags | none |
| removed RMS, hum / decrackle | 0.00006 / 0.000359 |
| leakage, hum | share 0.0027, occupied 0.0000, not reverted |
| leakage, decrackle | share 0.0214, occupied 0.0001, not reverted |

The hum prominence falls by a factor of 26 while the removed energy stays at 6e-05 RMS,
which is the audible claim of the notch stage: it takes the line and little else. The
leakage share of 0.0027 on the hum stage says the same thing from the other side.

```text
python -m discrest verify examples/surface
```

`expected.yaml` was recorded on win32 with Python 3.12.4, NumPy 2.0.0, and SciPy 1.17.1,
the same environment as the other four examples.
