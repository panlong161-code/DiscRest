# Dense transients

`input.wav` is 4 seconds of synthetic audio. From 1.0 to 2.0 seconds an impulse occurs every 80 samples, so the run can show how a drum hit or dense crackle is labeled.

The configuration runs declick only, with `protect_dense` enabled. This run lists 726 short regions. 701 fall in dense windows, have action `protected`, and are not rewritten. 25 are repaired. Another 13 regions longer than 3 ms are not replaced. The flag is `dense-transient`.

```text
python -m discrest run --config examples/dense_transient/run.yaml
python -m discrest verify examples/dense_transient
```
