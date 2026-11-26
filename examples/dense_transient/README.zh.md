# 磨损圆柱上的密集瞬态

这个示例在真实的磨损材料上演示密集窗规则，而不是在构造出来的脉冲串上。

## 来源

UCSB Cylinder Audio Archive，圆柱 13692：《'Tis but a dream》，Henry Burr 男高音独唱配乐队，
Columbia Phonograph Co. 33041，1906 年发行。持久链接
<http://www.library.ucsb.edu/OBJID/Cylinder13692>。档案馆提供的是访问文件
`cusb-cyl13692d.mp3`，解码为 44 100 Hz、16 bit、单声道、17.425 秒，写成 `input.wav`。

该录音 1906 年发行，在美国属于公有领域（17 U.S.C. § 1401）。本仓库不对美国以外的
版权状态作任何主张。

访问副本的低频已处理过，`rumble_ratio` 为 0.0131、`hum_prominence` 为 2.10。表面磨损
没有处理：这是一张放得很旧的圆柱。

## 这次运行做了什么

`profile` 报每秒 31.68 次咔嗒，preset 为 `protect`，理由是 `dense-impulses`，`confident: true`。
`run.yaml` 只开去咔嗒，`protect_dense` 打开。

| 量 | 值 |
|---|---|
| 区间 | 552 |
| 修复（`isolated-click`） | 67（12.1%） |
| 保护（`dense-transient`） | 485（87.9%） |
| 密集窗 | 45 |
| 长于 3 ms 未替换 | 28 |
| 标记 | `dense-transient` |
| 去咔嗒移除 RMS | 0.011232 |
| 泄漏 | share 0.0320，occupied 0.0043，未回退 |

这个示例要说的就是那 87.9%：磨损到这个程度，局部规则会把检测到的大部分保护起来，
而运行记录如实写出来，而不是照着改。在这份文件上关掉 `protect_dense`，552 个区间会
全部被修复，移除能量成倍上升——默认值之所以保留这些区间，原因就在这。

```text
python -m discrest verify examples/dense_transient
```

`expected.yaml` 的哈希记录于 win32、Python 3.12.4、NumPy 2.0.0、SciPy 1.17.1，五个示例一致。
