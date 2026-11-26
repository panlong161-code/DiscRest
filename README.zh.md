# DiscRest

DiscRest 是处理已数字化唱片的本地工作台。五步都可以单独关闭：去咔嗒、去裂纹、隆隆声高通、交流哼声陷波、去嘶声。每次运行写出修复结果、整段残差、每一级单独拿走的声音、带理由的咔嗒区间和一份冻结配置。音频只在本机处理。

版本 0.8.1，许可 MIT。三档产品模式和本机工作台与命令行共用同一套参数。修复之前可以用 `profile` 看这段声音更接近哪一档；测量接近分界时，画像会标明不确定。`examples/archive_78` 是一段 1919 年未修复唱筒的 20 秒，并和 Audacity 2.1.0 的去咔嗒算法放在同一段上计数。这是算法重算，不是 Audacity 界面里的一次操作。

英文说明见 `README.md`。投稿论文不包含在代码仓库中。

## 安装

```text
pip install -e ".[dev]"
```

只运行示例时，安装 NumPy、SciPy 和 PyYAML 后使用 `python -m discrest`。

## 产品模式

| 模式 | 适合 | 打开的步骤 |
| --- | --- | --- |
| `isolated` 孤立咔嗒 | 爆点隔得开 | 去咔嗒、去嘶声 |
| `protect` 密集保护 | 鼓点或密裂纹可能被当成咔嗒 | 只去咔嗒，过密的窗不替换 |
| `surface` 表面噪声 | 转盘隆隆声、交流哼声、细裂纹 | 去咔嗒、去裂纹、高通、陷波 |

```text
python -m discrest presets
python -m discrest profile --input examples/public_cyl/input.wav
python -m discrest run --preset isolated --input examples/public_cyl/input.wav --output-dir out
python -m discrest ui
```

`profile` 只测量、不写音频。它报告每秒咔嗒数、40 Hz 以下的能量占比、50 Hz 或 60 Hz 谐波有多突出，并建议 `isolated`、`protect` 或 `surface`。建议和测量一起写进随后那次运行的 `run.yaml`。

`ui` 只监听本机。页面上可以换模式、载入对应的合成示例、试听原声、修复结果、整段残差和某一级拿走的声音，并下载冻结配置。修复之后会给出声音结构，一键把表单改成建议的模式。咔嗒表写出处理、理由和误差倍数，并另存一份 Praat 能打开的 `clicks.textgrid`。超过 180 秒的文件用命令行处理。

## 复现示例

四个示例输入来自历史录音：`archive_78` 是 1919 年未修复唱筒的 20 秒，`public_cyl`、`dense_transient` 是美国加州大学圣塔芭芭拉分校圆柱档案的两条，`surface` 是一条真实 78 转。`loc_victor_78` 以美国国会图书馆转录为底稿，并通过 `overlay.py` 叠加可控的合成退化，用于已知真值测试；其他构造信号位于 `discrest/synthetic.py`。

```text
python -m discrest run --config examples/public_cyl/run.yaml
python -m discrest verify examples/public_cyl
python -m discrest verify examples/dense_transient
python -m discrest verify examples/surface
python -m discrest verify examples/archive_78
python -m discrest verify examples/loc_victor_78
```

`verify` 在每台机器上核对输出文件、咔嗒数和标记。只有平台、Python、NumPy、SciPy 版本都与记录哈希的环境完全一致（Windows、Python 3.12.4、NumPy 2.0.0、SciPy 1.17.1）时才比对 SHA-256；否则仍核对计数和标记。

`examples/public_cyl` 是 1910 年 Edison Amberol 473《My south polar expedition》的 20 秒，UCSB 圆柱 1859。只开去咔嗒。档案馆的访问副本已在 40 Hz 以下滤过，所以这次运行把 14 个区间全部修复，没有标记；低频几级改在 `examples/loc_victor_78` 上演示。

`examples/dense_transient` 是 1906 年 Columbia 圆柱《'Tis but a dream》的 17.4 秒，UCSB 13692，一张磨损很重的唱片。检测列出 552 个区间，其中 485 个落在 45 个密集窗里被保护，67 个被修复；另有 28 个长于 3 ms 的区间没有替换。日志是 `dense-transient`。

`examples/surface` 是一条真实 78 转转录的 20 秒，交流哼声很强，Freesound 18627，CC0。运行打开 50 Hz 陷波与去裂纹：`hum_prominence` 从 33.88 降到 1.19，修复 7 处裂纹，没有标记。高通没开，因为这份文件 40 Hz 以下没有可删的东西。

`examples/archive_78` 列出 149 个区间：82 个修复，66 个因为过密留下，1 个因为起音留下。

`examples/loc_victor_78` 用美国国会图书馆 Victor 73978（matrix B-28269）的真实转录跑隆隆声、哼声、嘶声三级，取 38–68 秒。交付的文件是母带，低频早已被滤掉，所以 `overlay.py` 在它上面按已知量叠加低频、工频和宽带噪声，并把未叠加的基底一起保留，这样才能算出真 SNR。`profile` 报 `low-frequency, mains-hum`。这次运行把 `rumble_ratio` 从 0.1781 降到 0.0006，`hum_prominence` 从 11.96 降到 1.60，哼声的泄漏守卫因 `occupied = 0.0000` 未触发回退。嘶声级在这段材料上是负结果：SNR 从 20.00 dB 降到 15.32 dB，原因是整段没有安静帧可用来估计噪声。详见该目录的 README。

更换 `input.wav` 之后，先 `run`，再把 `out/run.yaml` 里的哈希和点击数抄进 `expected.yaml`，并写上当时的 `recorded_platform`。

## 输出

| 文件 | 内容 |
| --- | --- |
| `restored.wav` | 16-bit 修复结果 |
| `residual.wav` | 输入减输出，五步合在一起的残差 |
| `removed_declick.wav` 等五份 | 每一级单独拿走的声音，可单独试听 |
| `clicks.csv` | 声道、区间、起点时间、`repaired` 或 `protected`、理由、误差倍数 |
| `clicks.textgrid` | 同一批区间的 Praat 间隔层，空白处是空标注 |
| `run.yaml` | 输入哈希、采样率、全部参数、声音结构、每级乐音泄漏、每步移除 RMS、输出哈希 |
| `log.txt` | 点击数、保护数、裂纹数、长区间数、标记 |

采样率策略：`native` 保持文件原来的采样率，`require` 在与 `expected_sample_rate` 不一致时停止，`resample` 变到该采样率并在记录里保留原始采样率。

## 试听被移除的声音

听不出修复效果有两个原因，都不是运行出错：

1. `removed_*.wav` 五份都会写，**包括没有打开的那几级**。没运行的级写的是整段 0，所以 `examples/archive_78` 里的 `removed_hum.wav` 是静音，含义是"这一级没开"，不是"录音里没有交流声"。
2. 真正被移走的量相对音乐很小。`examples/archive_78` 的去咔嗒只改了 0.49% 的样本、电平 −47 dBFS，`restored.wav` 与 `input.wav` 整体只差 0.02 dB。`examples/loc_victor_78` 的隆隆声移除 RMS 是 0.064，输出整体低 2.5 dB，但差值集中在 80 Hz 以下，笔记本扬声器放不出来。

`audition` 为单个示例生成试听包：把移除量峰值归一化、截最大一处修复前后各 0.8 秒、再画一张频谱图。

```text
python -m discrest audition examples/archive_78
```

结果写到 `examples/archive_78/listen/`：运行过的每一级一份 `4_removed_<stage>_boosted.wav`，`5`–`7` 是片段（原声、修复、移除量），`8_spectrum.png` 是图，`index.html` 带播放器和各级读数。放大倍数写在页面上，波形除增益外未作改动。

`audition` 是唯一带额外依赖的命令，需要 `soundfile`，用 `pip install "discrest[audition]"` 安装。五级处理本身只依赖 NumPy、SciPy、PyYAML。

## 技术路线

处理顺序是：去咔嗒 → 去裂纹 → 隆隆声高通 → 哼声陷波 → 去嘶声。

这里的零相位高通和陷波会把一个脉冲展成振铃，自回归检测会把振铃再当成咔嗒。DiscRest 因此先修脉冲，再做滤波。年代均衡、音色处理和带宽延拓不在这条链路里。

| 来源 | 采纳的部分 | 实现 |
| --- | --- | --- |
| Godsill 与 Rayner，1998 | 自回归检测，缺失样本用 LSAR 插值 | `declick.py`、`lsar.py` |
| NeedledroppersDeclick | 鼓点会被当成咔嗒 | 过密的窗只登记，不替换 |
| Gtk Wave Cleaner | 灵敏度可调 | `threshold` |
| PD-Cleaner | 分步、界面里可听被删掉的部分 | 每步一个开关；每一级写成单独文件；每个咔嗒带理由和误差倍数 |
| Moliner 两级 U-Net | 可选的神经网络去噪 | `neural` 开关；没有本地权重就停止 |
| Praat TextGrid、pyannote 的时间层 | 把自动判断写成别人能打开的标注 | `clicks.textgrid` |
| 语音前端对噪声分类后再开模块 | 先看脉冲、低频、哼声，再选已有模式 | `profile` |
| 语音增强里检查噪声估计是否含目标 | 隆隆声、哼声、去嘶声若带走乐音则整级退回 | `leakage` |
| RESTORE、BEHM-GAN、groovedsp | 分轨、带宽延拓、实时播放 | 不实现 |

去咔嗒在短帧上估计预测误差，阈值是稳健标准差的倍数。捆绑示例用 16。中心两侧 `half_width_ms` 用 LSAR 填上；解不稳定时退回两端连线。长于 `max_click_ms` 的区间保持原样。

去裂纹看信号和短时中值的差，只处理很短的尖峰，并把幅度收到中值附近。过密时标记 `dense-crackle` 并留下原样本。它接在去咔嗒之后，用来处理没有超过咔嗒阈值的小尖峰。

隆隆声是巴特沃斯高通。哼声是基频及其谐波上的陷波，`mains_hz` 取 50 或 60。去嘶声用较安静帧的幅度谱做谱减法。这三步默认关闭。

`neural.enabled: true` 需要本地检查点。本版本不附带 Moliner 或 BEHM-GAN 的权重，缺少文件时命令停止。

## 使用边界

密集脉冲、鼓点和齿音会进入检测列表。过密的窗记为 `protected`，理由是 `dense-transient`。稀疏的敲击如果后面跟着明显更响的衰减，理由是 `sustained-onset`，这一下也不替换。隆隆声、哼声或去嘶声若把乐音频点一并拿走，这一级会整段退回，日志写 `leakage-reverted`。分轨和带宽延拓仍分别属于 RESTORE 与 BEHM-GAN。

## 支持

问题咨询与技术支持可联系作者 Long Pan（`540432274@qq.com`），或在 https://github.com/panlong161-code/DiscRest/issues 提交。

0.8.1 的代码见 https://github.com/panlong161-code/DiscRest/tree/v0.8.1 。

Godsill SJ, Rayner PJW. Digital Audio Restoration. Springer; 1998. https://doi.org/10.1007/978-1-4471-1561-8

Moliner E, Välimäki V. A two-stage U-Net for high-fidelity denoising of historical recordings. IEEE ICASSP; 2022. https://doi.org/10.1109/ICASSP43922.2022.9746977

## 测试

```text
pytest
```
