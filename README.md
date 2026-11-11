# DiscRest

DiscRest 是处理已数字化唱片的本地工作台。五步都可以单独关闭：去咔嗒、去裂纹、隆隆声高通、交流哼声陷波、去嘶声。每次运行写出修复结果、整段残差、每一级单独拿走的声音、带理由的咔嗒区间和一份冻结配置。音频只在本机处理。

版本 0.7.0，许可 MIT。三档产品模式和本机工作台与命令行共用同一套参数。修复之前可以用 `profile` 看这段声音更接近哪一档；测量接近分界时，画像会标明不确定。`examples/archive_78` 是一段 1919 年未修复唱筒的 20 秒，并和 Audacity 2.1 的默认去咔嗒放在同一段上计数。

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
python -m discrest profile --input examples/public_78/input.wav
python -m discrest run --preset isolated --input examples/public_78/input.wav --output-dir out
python -m discrest ui
```

`profile` 只测量、不写音频。它报告每秒咔嗒数、40 Hz 以下的能量占比、50 Hz 或 60 Hz 谐波有多突出，并建议 `isolated`、`protect` 或 `surface`。建议和测量一起写进随后那次运行的 `run.yaml`。

`ui` 只监听本机。页面上可以换模式、载入对应的合成示例、试听原声、修复结果、整段残差和某一级拿走的声音，并下载冻结配置。修复之后会给出声音结构，一键把表单改成建议的模式。咔嗒表写出处理、理由和误差倍数，并另存一份 Praat 能打开的 `clicks.textgrid`。超过 180 秒的文件用命令行处理。

## 复现示例

三个示例都是合成信号，用来离线复现命令。

```text
python -m discrest run --config examples/public_78/run.yaml
python -m discrest verify examples/public_78
python -m discrest verify examples/dense_transient
python -m discrest verify examples/surface
python -m discrest verify examples/archive_78
```

`examples/public_78` 是 8 秒、44100 Hz 的三个乐音、轻微嘶声和 12 次孤立咔嗒。去咔嗒和去嘶声打开。这次运行修复 12 个区间，没有 `dense-transient`。

`examples/dense_transient` 在 1 秒内每 80 个样本放一个脉冲。检测列出 726 个短区间，其中 701 个落在过密的窗里，`action` 为 `protected`，样本留在原处；另外 25 个被修复。还有 13 个长于 3 ms 的区间没有替换。日志是 `dense-transient`。

`examples/surface` 同时含 30 Hz 隆隆声、50 Hz 与 150 Hz 哼声、3 次咔嗒和 3 次更小的裂纹，并带一层嘶声。这次运行修复 3 个咔嗒区间和 3 处裂纹。`out/run.yaml` 里隆隆声的移除 RMS 约为 0.094，哼声约为 0.021。

更换 `input.wav` 之后，先 `run`，再把 `out/run.yaml` 里的哈希和点击数抄进 `expected.yaml`。

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

## 技术路线

处理顺序是：去咔嗒 → 去裂纹 → 隆隆声高通 → 哼声陷波 → 去嘶声。

PD-Cleaner 把隆隆声和哼声放在去咔嗒之前。这里的零相位高通和陷波会把一个脉冲展成振铃，自回归检测会把振铃再当成咔嗒。DiscRest 因此先修脉冲，再做滤波。年代均衡、音色处理和带宽延拓不在这条链路里。

| 来源 | 采纳的部分 | 实现 |
| --- | --- | --- |
| Godsill 与 Rayner，1998 | 自回归检测，缺失样本用 LSAR 插值 | `declick.py`、`lsar.py` |
| NeedledroppersDeclick | 鼓点会被当成咔嗒 | 过密的窗只登记，不替换 |
| Gtk Wave Cleaner | 灵敏度可调 | `threshold` |
| PD-Cleaner | 分步、界面里可听被删掉的部分 | 每步一个开关；每一级写成单独文件；每个咔嗒带理由和误差倍数 |
| Moliner 两级 U-Net | 可选的神经网络去噪 | `neural` 开关；没有本地权重就停止 |
| Praat TextGrid、pyannote 的时间层 | 把自动判断写成别人能打开的标注 | `clicks.textgrid` |
| 语音前端对噪声分类后再开模块 | 先看脉冲、低频、哼声，再选已有模式 | `profile` |
| 语音增强里检查噪声估计是否含目标 | 每一级拿走的声音是否还带着留下来的乐音 | `leakage` |
| RESTORE、BEHM-GAN、groovedsp | 分轨、带宽延拓、实时播放 | 不实现 |

去咔嗒在短帧上估计预测误差，阈值是稳健标准差的倍数。捆绑示例用 16。中心两侧 `half_width_ms` 用 LSAR 填上；解不稳定时退回两端连线。长于 `max_click_ms` 的区间保持原样。

去裂纹看信号和短时中值的差，只处理很短的尖峰，并把幅度收到中值附近。过密时标记 `dense-crackle` 并留下原样本。它接在去咔嗒之后，用来处理没有超过咔嗒阈值的小尖峰。

隆隆声是巴特沃斯高通。哼声是基频及其谐波上的陷波，`mains_hz` 取 50 或 60。去嘶声用较安静帧的幅度谱做谱减法。这三步默认关闭。

`neural.enabled: true` 需要本地检查点。本版本不附带 Moliner 或 BEHM-GAN 的权重，缺少文件时命令停止。

## 使用边界

密集脉冲、鼓点和齿音会进入检测列表。过密的窗记为 `protected`，理由是 `dense-transient`。稀疏的敲击如果后面跟着明显更响的衰减，理由是 `sustained-onset`，这一下也不替换。隆隆声、哼声或去嘶声若把乐音频点一并拿走，这一级会整段退回，日志写 `leakage-reverted`。分轨和带宽延拓仍分别属于 RESTORE 与 BEHM-GAN。

Godsill SJ, Rayner PJW. Digital Audio Restoration. Springer; 1998. https://doi.org/10.1007/978-1-4471-1561-8

Moliner E, Välimäki V. A two-stage U-Net for high-fidelity denoising of historical recordings. IEEE ICASSP; 2022. https://doi.org/10.1109/ICASSP43922.2022.9746977

## 开发

```text
pytest
```
