# Unrestored 1919 cylinder, 20 seconds

This is the real-recording example used in the paper.

The source is the Wikimedia Commons file “Irving Berlin - Arthur Fields - Oh! How I Hate To Get Up In The Morning (unrestored).ogg”. Commons records an upload by Adam Cuerden on 2008-10-04 from the University of California, Santa Barbara cylinder project, unrestored. The song is Irving Berlin’s *Oh! How I Hate to Get Up in the Morning*, sung by Arthur Fields, Edison Blue Amberol 3639, matrix 6287, recorded in 1919. File page: <https://commons.wikimedia.org/wiki/File:Irving_Berlin_-_Arthur_Fields_-_Oh!_How_I_Hate_To_Get_Up_In_The_Morning_(unrestored).ogg>. The original file SHA-1 is `7ce2e563c46b997496517f82bc39d77be3611af2`.

Under United States law, recordings published before 1 January 1926 are in the public domain (17 U.S.C. § 1401). The Commons page also states that the recording may remain protected outside the United States. This repository does not claim a worldwide public-domain status.

`input.wav` keeps seconds 98.000–118.000. The stereo file was downmixed to mono at 44100 Hz, 16-bit PCM. `profile` selects `protect` with `confident: true`, so `run.yaml` runs declick only. Dense windows and a sustained onset are left in place.

The comparison is a reimplementation of Craig DeForest’s Audacity 2.1 `RemoveClicks`, at the default threshold 200 and width 20, and again at threshold 40. It is not a session in the Audacity application. Counts are in `comparison.yaml` and are recomputed by the tests.

The recorded run lists 149 regions: 82 `isolated-click` repaired, 66 `dense-transient` protected, and 1 `sustained-onset` protected. Declick removed RMS is about 0.0043. The share of removed declick energy that falls on the remaining musical band is 0.0335, so the stage is not reverted.

There is no blind listening test. The author still has to listen to `out/restored.wav` and `out/residual.wav` and write whether a musical phrase remains in the residual, stating that only one author listened.

```text
python -m discrest verify examples/archive_78
```
