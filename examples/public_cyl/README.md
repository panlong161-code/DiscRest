# Edison Amberol 473, 1910, 20 seconds

This example runs declick on a real cylinder transfer with sparse clicks.

## Source

UCSB Cylinder Audio Archive, cylinder 1859: “My south polar expedition”, Lieutenant E. H.
Shackleton, Edison Amberol 473, released 1910, William R. Moran collection. Durable URL
<http://www.library.ucsb.edu/OBJID/Cylinder1859>. The archive's access file is
`cusb-cyl1859d.mp3`; it was decoded to 44100 Hz, 16-bit, mono, 20.000 s, and written as
`input.wav`.

The recording was published in 1910 and is in the public domain in the United States
(17 U.S.C. § 1401). This repository does not claim a worldwide public-domain status.

The archive distributes an access copy rather than a raw transcription: the low band and
the broadband floor have already been treated, so on this file `rumble_ratio` is 0.0000 and
`hum_prominence` is 2.94. Impulsive damage is untouched, which is what the example uses.

## What the run does

`profile` reports 0.70 clicks per second, preset `isolated` with reason `sparse-clicks`, and
`confident: true`. `run.yaml` enables declick only.

| Quantity | Value |
|---|---|
| regions | 14, all `repaired` as `isolated-click` |
| flags | none |
| declick removed RMS | 0.003857 |
| leakage, declick | share 0.0103, occupied 0.0021, not reverted |
| clicks per second after the run | 0.10 (from 0.70) |

## Why decrackle is off

`decrackle` was tried on this transfer at threshold 3.0 and made the result worse. It
repaired 96 crackles and protected 662, raised the `dense-crackle` flag, and the click count
**after** processing rose from 0.10 to 2.30 regions per second: the small step edits leave
new prediction errors behind. At threshold 10.0 it repairs a single crackle and the count
stays at 0.15. Neither setting is worth shipping, so the stage stays off and the crackle
stage is shown on `examples/surface` instead.

```text
python -m discrest verify examples/public_cyl
```

`expected.yaml` was recorded on win32 with Python 3.12.4, NumPy 2.0.0, and SciPy 1.17.1,
the same environment as the other four examples.
