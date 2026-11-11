# Rumble, hum, and crackle

`input.wav` is 4 seconds of synthetic audio: a 330 Hz tone, 30 Hz rumble, 50 Hz and 150 Hz hum, light hiss, 3 clicks, and 3 smaller two-sample crackles.

`run.yaml` enables declick, decrackle, an 80 Hz high-pass, and a 50 Hz notch. Dehiss is off. This run repairs 3 click regions and 3 crackles. The log has no dense flag. In `out/run.yaml`, the rumble removed RMS is about 0.094 and the hum removed RMS is about 0.021.

Impulses run before the filters. A zero-phase high-pass or notch spreads a click into ringing, and a click detector that runs after the filter counts that ringing.

```text
python -m discrest run --config examples/surface/run.yaml
python -m discrest verify examples/surface
```
