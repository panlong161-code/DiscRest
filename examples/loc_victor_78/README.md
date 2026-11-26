# Victor 73978, Library of Congress transfer, 30 seconds

This example exercises the rumble, hum, and dehiss stages. The recording is real; the
impairments added to it are of known size, which is what makes the numbers checkable.

## Source

Library of Congress, National Jukebox: Victor 73978, matrix B-28269. The downloaded
file is `master-mbrsrs-mbrsjukebox-jvm_victor_73978_01_b28269_01.wav`, 44 100 Hz,
16-bit PCM, two channels, 202.53 s. `input.wav` keeps seconds 38.000–68.000,
downmixed to mono. That span has the flattest level in the transfer (coefficient of
variation 0.185 over 30 one-second windows).

Under United States law the recording is in the public domain. This repository does
not claim a worldwide public-domain status.

## The delivered file carries no rumble and no hum

The transfer is a delivery master rather than a raw transcription, and four
measurements say so:

| Property | Measured | Why it matters |
|---|---|---|
| Channels | two, correlation 1.000000, difference ≈1 LSB | acoustic-era recordings are mono; the second channel is a copy |
| Peak | 32 766 / 32 768 | normalised to about 0 dBFS |
| Crest factor | 5.8 | an untreated acoustic transfer usually sits above 12 |
| 99% bandwidth | 7 250 Hz | acoustic recordings stop at 3–3.5 kHz |

The low band was filtered before delivery: `rumble_ratio` is 0.0008 and
`hum_prominence` is 3.49, against profile thresholds of 0.08 and 8.0. Neither stage
has anything to act on in the file as downloaded.

## What `overlay.py` adds

`overlay.py` adds three impairments to the transfer at levels it reports, and writes
`input.wav`. The base is attenuated 6 dB first so the sum does not clip; that scaling
cancels out of every ratio below.

| Stage | Model | Target | Measured in `input.wav` |
|---|---|---|---|
| rumble | 1/f noise, 4th-order Butterworth low-pass at 35 Hz, plus a 0.5556 Hz (33⅓ rpm) eccentricity term | `rumble_ratio` 0.18 | 0.1781 |
| hum | 50 Hz and two harmonics at 0 and −3 and −6 dB, with ±0.01 Hz slow drift | `hum_prominence` 25 | 11.96 |
| hiss | white noise, 2nd-order high-pass at 1 kHz | SNR 20 dB against the base | — |

The hum figure drops from 25 to 11.96 once the rumble overlay is added: low-frequency
noise fills the skirt around 50 Hz and hides the line. Both still clear the thresholds,
and `profile` reports `low-frequency, mains-hum`.

Because the base is preserved, the error signal is known exactly and a true SNR can be
computed. A raw transfer cannot give that, which is the only reason the overlay exists.

## What the run does

`run.yaml` turns rumble, hum, and dehiss on, and leaves declick and decrackle off: the
transfer has no impulsive damage, and `click_count` is 0.

| Quantity | Value |
|---|---|
| `rumble_ratio` before → after | 0.1781 → 0.0006 |
| `hum_prominence` before → after | 11.96 → 1.60 |
| removed RMS, rumble / hum / dehiss | 0.0643 / 0.0012 / 0.0171 |
| leakage, hum | share 0.3795, occupied 0.0000, not reverted |

The hum stage is above the 0.35 share threshold but `occupied` is 0.0000, so the guard
does not revert it. This example is why the guard needs both conditions: share alone
would have reverted a stage that removed nothing from the music band.

## dehiss is a negative result here

`dehiss` lowers the high-band floor by 3.4 dB but drops SNR from 20.00 to 15.32 dB.
Thirty parameter combinations were tried; the best gained 0.29 dB. The cause is the
noise estimate: `dehiss` takes the quietest 15% of frames, and this span is continuous
music with no silent frame, so music is estimated as noise.

Inserting silence in front of the base, without changing the noise, moves SNR from
−4.68 dB to +2.57 dB as the silent share reaches 15%, then it saturates — the same 15%
as `noise_percentile`. `dehiss` needs identifiable quiet frames; a continuously playing
transfer does not have them, and the stage is off by default for that reason.

```text
python -m discrest verify examples/loc_victor_78
```

The hashes in `expected.yaml` were recorded on win32 with Python 3.12.4, NumPy 2.0.0,
and SciPy 1.17.1, the same environment as the other four examples.
