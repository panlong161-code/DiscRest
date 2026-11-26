# Edison Amberol 473，1910 年，20 秒

这个示例在一条真实的圆柱转录上跑去咔嗒，咔嗒是稀疏的。

## 来源

UCSB Cylinder Audio Archive，圆柱 1859：《My south polar expedition》，Lieutenant E. H.
Shackleton，Edison Amberol 473，1910 年发行，William R. Moran collection。持久链接
<http://www.library.ucsb.edu/OBJID/Cylinder1859>。档案馆提供的是访问文件
`cusb-cyl1859d.mp3`，解码为 44 100 Hz、16 bit、单声道、20.000 秒，写成 `input.wav`。

该录音 1910 年发行，在美国属于公有领域（17 U.S.C. § 1401）。本仓库不对美国以外的
版权状态作任何主张。

档案馆发的是访问副本，不是原始转储：低频与宽带噪声底已经处理过，所以这份文件上
`rumble_ratio` 为 0.0000、`hum_prominence` 为 2.94。脉冲类损伤没有被处理，这个示例用的
正是这一部分。

## 这次运行做了什么

`profile` 报每秒 0.70 次咔嗒，preset 为 `isolated`，理由是 `sparse-clicks`，`confident: true`。
`run.yaml` 只开去咔嗒。

| 量 | 值 |
|---|---|
| 区间 | 14 个，全部 `repaired`，理由 `isolated-click` |
| 标记 | 无 |
| 去咔嗒移除 RMS | 0.003857 |
| 泄漏 | share 0.0103，occupied 0.0021，未回退 |
| 处理后每秒咔嗒 | 0.10（处理前 0.70） |

## 为什么关掉去裂纹

在这条转录上试过 `decrackle`（阈值 3.0），结果更差：修复 96 处裂纹、保护 662 处，
并抬起 `dense-crackle` 标记；**处理后的**咔嗒计数从 0.10 升到每秒 2.30 个——小阶跃改动
留下了新的预测误差。把阈值放到 10.0 只修 1 处，计数停在 0.15。两档都不值得发货，
所以这一级关掉，裂纹级改在 `examples/surface` 上演示。

```text
python -m discrest verify examples/public_cyl
```

`expected.yaml` 的哈希记录于 win32、Python 3.12.4、NumPy 2.0.0、SciPy 1.17.1，五个示例一致。
