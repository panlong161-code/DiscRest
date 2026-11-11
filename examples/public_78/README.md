# 合成唱机片段

`input.wav` 由 `python -m discrest.synthetic` 生成：8 秒，44100 Hz，单声道，三个乐音加轻微嘶声，从 0.45 秒起每 0.55 秒一次咔嗒，共 12 次。

`run.yaml` 打开去咔嗒和去嘶声。阈值是稳健标准差的 16 倍，插值是 LSAR。当前这次运行修复 12 个区间，`action` 都是 `repaired`，没有 `dense-transient`。

```text
python -m discrest run --config examples/public_78/run.yaml
python -m discrest verify examples/public_78
```

`clicks.csv` 的时间是被替换区间的起点。残差在 `out/residual.wav`。
