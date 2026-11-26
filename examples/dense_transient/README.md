# Dense transients on a worn cylinder

This example shows the dense-window rule on real wear rather than on a constructed impulse
train.

## Source

UCSB Cylinder Audio Archive, cylinder 13692: “‘Tis but a dream”, tenor solo by Henry Burr
with orchestra, Columbia Phonograph Co. 33041, released 1906. Durable URL
<http://www.library.ucsb.edu/OBJID/Cylinder13692>. The archive's access file is
`cusb-cyl13692d.mp3`; it was decoded to 44100 Hz, 16-bit, mono, 17.425 s, and written as
`input.wav`.

The recording was published in 1906 and is in the public domain in the United States
(17 U.S.C. § 1401). This repository does not claim a worldwide public-domain status.

The access copy has already been treated in the low band, so `rumble_ratio` is 0.0131 and
`hum_prominence` is 2.10. Surface wear is not treated: this is a heavily played cylinder.

## What the run does

`profile` reports 31.68 clicks per second, preset `protect` with reason `dense-impulses`, and
`confident: true`. `run.yaml` enables declick only, with `protect_dense` on.

| Quantity | Value |
|---|---|
| regions | 552 |
| repaired as `isolated-click` | 67 (12.1%) |
| protected as `dense-transient` | 485 (87.9%) |
| dense windows | 45 |
| regions longer than 3 ms, not replaced | 28 |
| flag | `dense-transient` |
| declick removed RMS | 0.011232 |
| leakage, declick | share 0.0320, occupied 0.0043, not reverted |

The point of the example is the 87.9%: on a surface this worn the local rule protects most
of what the detector finds, and the run says so instead of rewriting it. Turning
`protect_dense` off on this file repairs all 552 regions and multiplies the removed energy,
which is why the default keeps them.

```text
python -m discrest verify examples/dense_transient
```

`expected.yaml` was recorded on win32 with Python 3.12.4, NumPy 2.0.0, and SciPy 1.17.1,
the same environment as the other four examples.
