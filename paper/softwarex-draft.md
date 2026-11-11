# DiscRest: a local stepwise workbench for reproducible restoration of digitized disc recordings

Author: zx_panlong  
Affiliation: [fill in before submission]  
Corresponding email: [fill in before submission]

This file is a draft for the official SoftwareX template. Paste it into that template. Leave the template’s left-hand metadata labels unchanged. The body below is written to stay near 2,000 words, under the template’s 3,000-word limit. Two items are still blank on purpose: the corresponding email, and the author’s own listening sentence.

## Abstract

Digitized disc and cylinder recordings contain short clicks and longer noise, and a later user often cannot repeat the exact settings of a desktop session. DiscRest is a local Python workbench that runs declick, decrackle, rumble, hum, and dehiss as separate stages and writes the audio each stage removes, together with a reason for every click region. On a 20-second excerpt from an unrestored 1919 cylinder, the protect preset lists 149 regions, repairs 82, and leaves 67 in place. A synthetic surface example runs the rumble, hum, and crackle stages and records their removed RMS. The software is meant for small archive checks. It does not ship a neural denoiser, and it does not report a listening score.

Keywords: audio restoration; digitized recordings; declick; reproducibility; open-source software

## Code metadata

| Nr. | Code metadata description | Please fill in this column |
| --- | --- | --- |
| C1 | Current code version | v0.7.0 |
| C2 | Permanent link to code/repository used for this code version | https://github.com/panlong161-code/DiscRest/tree/v0.7.0 |
| C3 | Permanent link to Reproducible Capsule | Not used. Reproduce with the `verify` commands in the README. |
| C4 | Legal Code License | MIT |
| C5 | Code versioning system used | git |
| C6 | Software code languages, tools, and services used | Python 3.12; NumPy 1.26.4; SciPy 1.16.3; PyYAML 6.0.3 on the machine that recorded the hashes. The repository declares NumPy >= 1.24, SciPy >= 1.11, and PyYAML >= 6. |
| C7 | Compilation requirements, operating environments and dependencies | No compiler and no GPU. Tested on Windows (`win32`) for the recorded hashes, and on GitHub Actions with Python 3.12 for installation and tests. |
| C8 | If available, link to developer documentation/manual | https://github.com/panlong161-code/DiscRest/blob/v0.7.0/README.md |
| C9 | Support email for questions | [corresponding author email] |

## 1. Motivation and significance

A click on a disc or cylinder is a short impulse. Hiss is a continuing noise floor. A drum stroke is also a short transient. Godsill and Rayner treated these as different restoration problems and described autoregressive detection with interpolation of the missing samples [1]. Later neural denoisers remove much of that noise in one pass and can also write a residual. The two-stage U-Net of Moliner and Välimäki is one such model [2]. Diffusion sampling has been used in the same role on historical recordings [3]. The published U-Net implementation asks for a Python environment and a GPU. Desktop programs already expose separate controls for rumble, hum, clicks, and crackle, including PD-Cleaner [4] and Gtk Wave Cleaner [5]. A paper cannot usually repeat one of those interface sessions from a single stored command.

DiscRest addresses that reuse gap for a file that is already a WAV. The user chooses which stages run. The program writes the restored file, the full residual, one file per stage, a click table, and `run.yaml`. The same command can be run again. The software does not propose a new denoising network, a stem separation model, or a bandwidth extender. Those remain the subjects of the systems cited above and of related public projects. An optional neural switch exists only so that a later local checkpoint can be named. With no checkpoint file, the command stops.

The scientific use is modest and concrete. An archive worker, or a methods paper, can show which short regions were replaced, which were left because they were dense or looked like an onset, and which filter stage was reverted because it took musical energy with it. Impact at the time of writing is prospective: the repository is public, and this article is the first report of the tool.

## 2. Software description

### 2.1 Software architecture

The default path uses NumPy and SciPy only [6,7]. A WAV file is read as mono or stereo. The sample-rate policy is `native`, `require`, or `resample`. `native` keeps the file rate. `require` stops when the rate is not the configured rate. `resample` converts to that rate and stores the original rate in `run.yaml`. The program does not change pitch silently.

The stages then run in this order: declick, decrackle, rumble high-pass, hum notch, dehiss. Impulses come first. The rumble and hum filters are zero-phase. Applied first, they spread one click into ringing, and the click detector counts the ringing. Each stage can be turned off. The neural block is beside dehiss and is off unless a local checkpoint path is set. This release contains no weights.

Declick estimates a short-frame autoregressive prediction error and marks peaks above a robust threshold. The bundled examples use a threshold of 16. A short region is replaced by least-squares autoregressive interpolation, or by a straight line when that solution is unstable. A region longer than `max_click_ms` (3 ms in the examples) is left unchanged. Windows whose short-click rate exceeds `dense_per_second` are labeled `dense-transient` and are not interpolated. If the 30 ms after a short region is more than 2.5 times the 30 ms before it, and the later level is high enough, the reason is `sustained-onset` and the samples stay. Density is decided first, so a dense region is not relabeled as an onset.

Decrackle looks for short spikes in the difference between the signal and a short-time median. Rumble is a Butterworth high-pass [8]. Hum is a notch at the mains frequency and its harmonics, with the base set to 50 or 60 Hz. Dehiss is spectral subtraction from quiet frames [9], with the gain limited to a floor. After rumble, hum, or dehiss, DiscRest measures how much of the removed signal still lies on the musical band that remains. If that share and the occupancy of the band both cross their thresholds, the stage is restored to its input and the flag `leakage-reverted` is added. Declick and decrackle record the same measurement and do not revert.

The outputs are 16-bit PCM: `restored.wav`, `residual.wav` (input minus output), `removed_declick.wav` through `removed_dehiss.wav`, `clicks.csv`, `clicks.textgrid`, `log.txt`, and `run.yaml`. Each click row has channel, sample range, time, action (`repaired` or `protected`), reason, and a score equal to the peak absolute prediction error divided by the robust sigma. The TextGrid is a Praat interval tier [10]. `run.yaml` stores the input hash, rates, resolved settings, profile, per-stage leakage, removed RMS, and output hashes.

### 2.2 Software functionalities

Five functions match the claims of this article.

1. Separate switches. Any stage can be off. The removed file for a disabled stage is silent.
2. Something to listen to besides the restored file. The full residual and the five stage files are written every time, with a removed RMS in `run.yaml`.
3. A frozen run. `verify` checks that the output files exist and that the click count and flags match `expected.yaml`. SHA-256 values are compared on the platform named in that file. The hashes in this release were recorded on Windows, Python 3.12.7, NumPy 1.26.4, and SciPy 1.16.3. Another machine still checks the counts and flags.
4. A reason on every click region, also written as `clicks.textgrid`.
5. A profile that only measures. It reports clicks per second, the power below 40 Hz divided by the power from 1 Hz upward, and the prominence of the first three 50 or 60 Hz harmonics. It then suggests `isolated`, `protect`, or `surface`. Near a threshold, `confident` is false. Accepting the suggestion is a separate step. The studio can copy it into the form. The command does not change the audio by itself.

The same settings are available as presets and in a local studio page served on 127.0.0.1. The studio refuses files longer than 180 seconds and forces the neural switch off. Longer files use the command line.

The reproduce commands are:

```text
python -m discrest verify examples/archive_78
python -m discrest verify examples/surface
```

## 3. Illustrative examples

### 3.1 A 20-second unrestored cylinder excerpt

Example A is `examples/archive_78`. The source is the Wikimedia Commons file [11] of Arthur Fields singing Irving Berlin’s *Oh! How I Hate to Get Up in the Morning*, Edison Blue Amberol 3639, matrix 6287, recorded in 1919, from the University of California, Santa Barbara unrestored transfer. The file page records SHA-1 `7ce2e563c46b997496517f82bc39d77be3611af2`. The excerpt is seconds 98.000–118.000, downmixed to mono, 44100 Hz, 16-bit. Under 17 U.S.C. § 1401 [12], a United States recording published before 1 January 1926 is in the public domain in the United States. The Commons page states that the recording may remain protected elsewhere. This article does not claim a worldwide public-domain status.

`profile` on the excerpt reports 7.45 clicks per second, a rumble ratio of 0.0115, a hum prominence of 5.72, preset `protect`, reason `dense-impulses`, and `confident: true`. The run therefore enables declick only, with onset protection. Rumble, hum, decrackle, and dehiss stay off. `verify` reports 149 regions: 82 repaired with reason `isolated-click`, 66 protected as `dense-transient`, and 1 protected as `sustained-onset`. One further region longer than 3 ms is not replaced. The declick removed RMS is 0.00427. The leakage share for declick is 0.0335 and the occupied fraction is 0.0014, so the stage is not reverted. The flags are `dense-transient` and `sustained-onset`.

On the same samples, a reimplementation of the Click Removal effect in Audacity 2.1 [13], Craig DeForest’s `RemoveClicks`, at the default threshold 200 and width 20 forms 1 region and changes 5 samples. At threshold 40 and width 20 it forms 5575 regions and changes 64842 samples. These are two parameter settings of that published algorithm. They are not clicks counted in the Audacity graphical interface, and they are not a claim that one program sounds better.

[Author listening note. Listen to `examples/archive_78/out/restored.wav` and `residual.wav`. Write whether a musical phrase remains in the residual. State that only one author listened and that this is not a blind test. Delete this bracketed instruction before submission.]

### 3.2 Stages the cylinder excerpt does not turn on

Example B is the synthetic `examples/surface` file: 4 seconds, a 330 Hz tone, 30 Hz rumble, 50 and 150 Hz hum, light hiss, 3 clicks, and 3 smaller crackles. The run repairs 3 click regions and 3 crackles. Removed RMS is about 0.0061 for declick, 0.00059 for decrackle, 0.094 for rumble, and 0.021 for hum. Dehiss is off. No leakage flag is raised. This example shows the filter and crackle stages. It is not a substitute for the cylinder excerpt.

Example C, `examples/dense_transient`, places an impulse every 80 samples during one second of a 4-second file. The run lists 726 short regions, protects 701, and repairs 25. The flag is `dense-transient`. It shows the dense-window rule on a constructed signal.

On the recording machine, `python -m discrest verify examples/archive_78` also matches the SHA-256 values stored in `expected.yaml`. The README states that those hashes belong to that Windows environment. Counts and flags are what another machine is asked to match.

## 4. Impact

An archive worker who already has a digitized cylinder can keep a record of which regions were removed and which were kept because they were dense or looked like an onset. On this 20-second protect run, 67 regions are `protected` and 82 are repaired, with a reason and an error score in the same run as the stage residuals. A later `verify` checks the count and the flags.

The same excerpt shows how a threshold changes the amount of audio rewritten. Moving the reimplemented Audacity threshold from 200 to 40 changes the edited sample count from 5 to 64842. DiscRest’s declick removed RMS on this preset is 0.00427. The comparison is about how much was changed and what was written down.

No user count or download count is reported. There is no blind test. The neural option has no weights in the repository and stops if it is enabled without a checkpoint. The cylinder example does not enable dehiss, rumble, or hum; those stages are shown on `examples/surface`. Bit-identical output is claimed for the recorded Windows environment, not for every future NumPy and SciPy build.

## 5. Conclusions

DiscRest keeps declick, decrackle, rumble, hum, and dehiss as separate local stages, writes a reason for each click region, writes the audio each stage removes, reverts a rumble, hum, or dehiss stage that takes the remaining musical band with it, and stores a configuration that a later command can check. On the 1919 excerpt the checked result is 149 regions, 82 repaired and 67 protected. The default path is not a neural denoiser. Dense transients are detected and, when the window is dense, left in place. Later work can attach a published checkpoint or a bandwidth extender. That work is not in this version.

## References

[1] Godsill SJ, Rayner PJW. Digital audio restoration: a statistical model-based approach. London: Springer; 1998. https://doi.org/10.1007/978-1-4471-1561-8

[2] Moliner E, Välimäki V. A two-stage U-Net for high-fidelity denoising of historical recordings. In: IEEE ICASSP; 2022. https://doi.org/10.1109/ICASSP43922.2022.9746977

[3] Miranda BV, Deslandes RA, Irigaray I, Biscainho LWP. Diffusion-based denoising of historical recordings. J Audio Eng Soc 2025;73(4):220–30. https://doi.org/10.17743/jaes.2022.0198

[4] Visemannen. PD-Cleaner. https://github.com/Visemannen/PD-Cleaner

[5] AlisterH. Gtk Wave Cleaner. https://github.com/AlisterH/gwc

[6] Harris CR, Millman KJ, van der Walt SJ, Gommers R, Virtanen P, Cournapeau D, et al. Array programming with NumPy. Nature 2020;585:357–62. https://doi.org/10.1038/s41586-020-2649-2

[7] Virtanen P, Gommers R, Oliphant TE, Haberland M, Reddy T, Cournapeau D, et al. SciPy 1.0: fundamental algorithms for scientific computing in Python. Nat Methods 2020;17:261–72. https://doi.org/10.1038/s41592-019-0686-2

[8] Butterworth S. On the theory of filter amplifiers. Exp Wireless Wireless Eng 1930;7:536–41.

[9] Boll SF. Suppression of acoustic noise in speech using spectral subtraction. IEEE Trans Acoust Speech Signal Process 1979;27(2):113–20. https://doi.org/10.1109/TASSP.1979.1163209

[10] Boersma P, Weenink D. Praat: doing phonetics by computer. https://www.praat.org

[11] Wikimedia Commons. File: Irving Berlin - Arthur Fields - Oh! How I Hate To Get Up In The Morning (unrestored).ogg. https://commons.wikimedia.org/wiki/File:Irving_Berlin_-_Arthur_Fields_-_Oh!_How_I_Hate_To_Get_Up_In_The_Morning_(unrestored).ogg

[12] United States Code. Title 17, § 1401. https://www.law.cornell.edu/uscode/text/17/1401

[13] Audacity Team. Audacity: free audio editor and recorder. https://www.audacityteam.org
