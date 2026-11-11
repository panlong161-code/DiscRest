# 密集瞬态

`input.wav` 是 4 秒合成音。1.0 秒到 2.0 秒之间每 80 个样本有一个短脉冲，用来观察鼓点或密裂纹会被怎样标出。

这一配置只做去咔嗒，并且 `protect_dense` 为真。当前运行列出 726 个短区间：701 个在过密的窗里，`action` 为 `protected`，样本没有被改写；25 个被修复。另有 13 个长于 3 ms 的区间没有进入列表。日志为 `dense-transient`。

```text
python -m discrest run --config examples/dense_transient/run.yaml
python -m discrest verify examples/dense_transient
```
