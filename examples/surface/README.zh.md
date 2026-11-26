# 真实 78 转转录与交流哼声

这个示例在一条真实的 78 转转录上跑工频陷波与裂纹级。

## 来源

Freesound 声音 18627，《78 rpm.aif》，上传者 Walter_Odington，CC0 授权
<https://freesound.org/s/18627/>。整条 175 秒、44 100 Hz，99% 能量止于 3588 Hz，
`hum_prominence` 为 30.05——50 Hz 及其谐波明显高出周围噪声底。`input.wav` 取第 8–28 秒，
20.000 秒，单声道，已去直流。

这是个人上传，不是馆藏转储。它能证明"录音是真的、哼声是真的"，不能证明它来自哪张唱片、
哪一年、哪家厂牌，本仓库也不作这种主张。

## 这次运行做了什么

`profile` 报每秒 0.05 次咔嗒、`rumble_ratio` 0.0000、`hum_prominence` 33.88，preset 为
`surface`，理由是 `mains-hum`，`confident: true`。

`run.yaml` 打开 50 Hz 陷波（4 次谐波、Q 30）与去裂纹（阈值 3.0）。有两级没开：

- **去嘶声**：这条转录是连续演奏、没有安静帧，而这一级靠最安静的 15% 帧估计噪声底。
  在这种材料上它会压低高频、却抬高总体误差，测量见 `examples/loc_victor_78/README.md`。
- **80 Hz 高通**：`rumble_ratio` 是 0.0000，40 Hz 以下没有可删的东西，高通只会带走音乐。

| 量 | 值 |
|---|---|
| `hum_prominence` 前 → 后 | 33.88 → 1.19 |
| 裂纹修复 / 保护 | 7 / 0 |
| 标记 | 无 |
| 移除 RMS，哼声 / 裂纹 | 0.00006 / 0.000359 |
| 泄漏，哼声 | share 0.0027，occupied 0.0000，未回退 |
| 泄漏，裂纹 | share 0.0214，occupied 0.0001，未回退 |

`hum_prominence` 掉了 28 倍，而移除能量只有 6e-05 RMS——这就是陷波级的可听主张：
它取走谱线，几乎不碰别的。哼声级的泄漏 share 0.0027 从另一侧说了同一件事。

```text
python -m discrest verify examples/surface
```

`expected.yaml` 的哈希记录于 win32、Python 3.12.4、NumPy 2.0.0、SciPy 1.17.1，五个示例一致。
