# 隆隆声、哼声和裂纹

`input.wav` 是 4 秒合成音：330 Hz 乐音、30 Hz 隆隆声、50 Hz 与 150 Hz 哼声、轻微嘶声、3 次咔嗒，以及 3 次更小的双样本裂纹。

`run.yaml` 打开去咔嗒、去裂纹、80 Hz 高通和 50 Hz 陷波。去嘶声关闭。当前运行修复 3 个咔嗒区间和 3 处裂纹，日志没有密集标记。`out/run.yaml` 的 `removed_rms` 里，隆隆声约 0.094，哼声约 0.021。

脉冲放在滤波之前。零相位高通和陷波会把咔嗒展成振铃，若先滤波，检测会把振铃再数成咔嗒。

```text
python -m discrest run --config examples/surface/run.yaml
python -m discrest verify examples/surface
```
