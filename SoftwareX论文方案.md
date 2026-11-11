# DiscRest：老唱片音质修复系统的 SoftwareX 论文方案

SoftwareX 收的是可安装、可复现的软件，不是新的去噪网络。本文的主张应写成：数字化唱片的杂音要分开处理，而且使用者必须听得见被删掉的内容；DiscRest 把去咔嗒、去嘶声、残差试听和冻结配置收成一条本地命令。

建议英文题名：

**DiscRest: a local stepwise workbench for reproducible restoration of digitized disc recordings**

中文工作题名：DiscRest：面向数字化唱片的本地分步、可复现音质修复工作台

实现在本目录，版本 0.7.0。英文稿草稿是 `paper/softwarex-draft.md`，C2 指向 `https://github.com/panlong161-code/DiscRest/tree/v0.7.0`。合成示例仍用来离线复现三条受控链路。论文主示例是 `examples/archive_78`：1919 年爱迪生唱筒的未修复转录，取 98–118 秒。来源和截取方式写在该目录的 README。没有盲听。通讯邮箱和听感句仍由作者填写。

```text
python -m discrest verify examples/public_78
python -m discrest verify examples/dense_transient
python -m discrest verify examples/archive_78
```

## 1. 不要写成什么

- 不要声称提出了优于 Moliner 两级 U-Net 的新网络。该模型已有论文和仓库：[eloimoliner/denoising-historical-recordings](https://github.com/eloimoliner/denoising-historical-recordings)（MIT，ICASSP 2022）。
- 不要把“把噪声拆成瞬态和宽带”写成首创。[MelissaChen15/restore](https://github.com/MelissaChen15/restore) 已把 78 转录音拆成音乐、宽带噪声、瞬态、残差和高频延拓。
- 不要把分步 DSP 链路写成首创。[Visemannen/PD-Cleaner](https://github.com/Visemannen/PD-Cleaner) 已有隆隆声、哼声、咔嗒、裂纹、嘶声和年代均衡；[AlisterH/gwc](https://github.com/AlisterH/gwc) 已有可调灵敏度的桌面去咔嗒。
- 不要报告没有跑过的 SNR、PESQ 或听感分数。示例只写实际跑通的公开片段、参数和输出文件。

贡献句（摘要和结论都用这一句）：

DiscRest 不替换上述算法。它把去咔嗒、去裂纹、隆隆声、哼声和去嘶声分成可单独关闭的五步。每个被标出的咔嗒区间写明动作、理由和误差倍数；稀疏敲击后面如果跟着更响的衰减，这一下留下。每一级拿走的声音单独成文件；若滤波或去嘶声把乐音频点一并拿走，这一级退回。修复前先按脉冲、低频和哼声给声音画像，并据此建议已有的一档模式；测量接近分界时画像标明不确定。采样率、阈值、画像和这些输出的哈希写入一份可重跑的配置。同一命令在示例片段上能再次得到同一组输出。

## 2. 和现有仓库的对照

写在第 1 节末或第 4 节，四行就够。

| 软件 | 形态 | 已有能力 | DiscRest 不重复、而补上的部分 |
| --- | --- | --- | --- |
| Moliner U-Net | Python / CUDA / Colab | 唱机噪声上的联合去噪，并写出残差 | 默认路径不要求 GPU；咔嗒与嘶声可分开开关；配置被冻结 |
| RESTORE | 研究用推理脚本 | 六轨拆分后再拼接 | 面向已数字化母带的可试听工作流，而不是新的分离模型 |
| PD-Cleaner | VST3 / 独立程序，AGPL | 经典 DSP 全链路，界面里可单独听某一级 | 每一级删掉的声音写成文件并进入哈希；每个咔嗒写明理由和误差倍数 |
| Gtk Wave Cleaner | Linux 桌面，GPL | 波形上手工调节去咔嗒 | 不依赖 GTK；批处理和配置可进入论文示例 |

经典算法只引用，不重新发明：Godsill 与 Rayner，*Digital Audio Restoration*，Springer，1998。自回归去咔嗒的开源实现见 [gburlet/audio-restore](https://github.com/gburlet/audio-restore) 与 [keithhanlon/NeedledroppersDeclick](https://github.com/keithhanlon/NeedledroppersDeclick)。后者已写明鼓点会被当成咔嗒，本文必须把这条局限留在软件行为里。

带宽延拓（[eloimoliner/bwe_historical_recordings](https://github.com/eloimoliner/bwe_historical_recordings)）和树莓派实时播放（[dubyte/groovedsp](https://github.com/dubyte/groovedsp)）放进“不在本文范围内”。Audacity 作为通用编辑器一句带过。

语音文献只借工作方式，不借模型。Praat 的 TextGrid 是间隔层，pyannote 把语音活动写成一段时间标注；DiscRest 用同一种层写出咔嗒决定，文件名 `clicks.textgrid`。WebRTC 音频模块按高通、降噪、增益分别开关；`profile` 用脉冲密度、40 Hz 以下能量和 50/60 Hz 谐波突出程度，在已有三档里选一档。语音增强会检查噪声估计里还剩多少目标成分；`leakage` 用同一问题检查每一级拿走的声音是否还落在修复结果的乐音频点上，只记入 `run.yaml`。RNNoise（Valin，arXiv:1709.08243，https://github.com/xiph/rnnoise）的 Bark 带增益网络不接入。

## 3. 技术路线与软件边界

默认路径只用 NumPy / SciPy，本机处理 WAV，不上传音频。0.7.0 的顺序是：

1. 去咔嗒：自回归预测误差检测，短区间用 LSAR 插值。过密的窗记为 `protected`，不替换。
2. 去裂纹：短时中值残差上的小尖峰，向中值衰减。过密时标记 `dense-crackle` 并留下。
3. 隆隆声：巴特沃斯高通。默认关闭。
4. 哼声：电源频率及其谐波的陷波。默认关闭。
5. 去嘶声：谱减法。默认关闭。
6. 可选神经网络：配置里指出本地 Moliner 检查点才允许打开。没有权重就停止，论文示例不依赖这一步。

PD-Cleaner 把隆隆声和哼声放在脉冲之前。本实现的零相位滤波会把一个咔嗒展成振铃，所以脉冲两步在前。年代均衡、Character、带宽延拓、分轨和实时播放不做，分别留给 PD-Cleaner、BEHM-GAN、RESTORE 和 groovedsp。

每次运行写出修复结果、整段残差、五份分级残差（`removed_declick.wav` 至 `removed_dehiss.wav`）、咔嗒表、`log.txt` 和 `run.yaml`。咔嗒表的每一行有 `action`、`reason` 和 `score`：孤立区间的理由是 `isolated-click`，落在过密窗里的理由是 `dense-transient`，`score` 是该区间预测误差峰值相对稳健标准差的倍数。`run.yaml` 含输入哈希、采样率、解析后的参数、每步移除 RMS 和输出哈希。

## 4. 按 SoftwareX 栏目怎么写

全文英文，正文约 3000 词以内。草稿在 `paper/softwarex-draft.md`。图 2 张：流水线图；一段公开录音的波形，标出咔嗒和残差。

### 代码元数据（投稿表）

| 编号 | 内容 | 拟填写 |
| --- | --- | --- |
| C1 | 当前代码版本 | v0.7.0，与论文示例的 git 标签一致 |
| C2 | 代码永久链接 | https://github.com/panlong161-code/DiscRest/tree/v0.7.0 |
| C3 | 许可 | MIT。若调用 AGPL 的 PD-Cleaner 代码，不要把那段抄进仓库 |
| C4 | 版本管理 | git |
| C5 | 语言与工具 | 记录哈希的环境是 Python 3.12.7、NumPy 1.26.4、SciPy 1.16.3、PyYAML 6.0.3。可选神经网络后端不随仓库提供权重 |
| C6 | 运行环境 | 无 GPU 可完成示例。SHA-256 属于上述 Windows 环境；其他系统核对咔嗒数和标记 |
| C7 | 文档 | 仓库英文 README：安装、一条复现命令、输出文件说明 |
| C8 | 联系邮箱 | 通讯作者邮箱，投稿前填入，仓库里现在还没有 |

### 摘要（约 200 词）

四句，按这个顺序：

1. 数字化唱片同时含短时咔嗒和持续嘶声，现有网络一次去掉全部杂音，桌面工具又难于按配置重跑。
2. DiscRest 在本机分五步处理，每步都可关，并写出整段残差、每一级单独的残差、带理由的咔嗒表和 `run.yaml`。
3. 示例使用一段注明来源的公开唱机录音；给出检测到的咔嗒数、残差是否含明显乐音，以及重复运行是否得到相同输出。数字必须来自你自己的那次运行。
4. 软件面向档案整理和小规模复原实验，不替代商业母带系统，也不声称在打击乐上无误检。

### 1. Motivation and significance

三段。

第一段写缺陷本身。咔嗒、爆点是短脉冲；嘶声是持续底噪；鼓点也是短瞬态。引用 Godsill & Rayner 1998，说明分项处理是已有原则。

第二段写现有软件留下的使用缺口，对着第 2 节的四行表。Moliner 要 Python 和 CUDA，训练偏古典音乐。RESTORE 是推理脚本。PD-Cleaner 和 GWC 有调节，但论文作者无法用一条命令重现对方界面里的某次操作。

第三段写本文软件解决的使用问题，不要写新公式。实验设置就一句话：使用者对一段已数字化的 WAV 选择各步的开关和阈值，在本机得到结果、残差和配置。

### 2. Software description

#### 2.1 Software architecture

画一条直线：WAV → 重采样检查 → 去咔嗒 → 去裂纹 → 隆隆声 → 哼声 → 去嘶声 → 写出结果、残差、咔嗒表、`run.yaml`。可选神经网络放在去嘶声旁边的虚线框，标成 optional。

写清默认采样率策略。输入不是 44100 Hz 时拒绝或按配置重采样，并在 `run.yaml` 里记录原始采样率。不要静默改变音高。

#### 2.2 Software functionalities

五条，与摘要对应：

1. 分步开关。五步各自开或关，只开一步时残差就是这一步的结果。
2. 分级试听。整段残差 = 输入 − 输出。每一级另写一份 `removed_*.wav`。`run.yaml` 同时给出每步的移除 RMS。
3. 冻结配置。示例目录里的 yaml 在记录哈希的那台机器上能复现输出哈希；其他机器核对咔嗒数和标记。
4. 局限写进每一行。过密的窗日志写 `dense-transient`，对应区间 `action` 为 `protected`、`reason` 为 `dense-transient`，并记下误差倍数，样本留在原处。同一批区间另写 `clicks.textgrid`，Praat 可以直接打开。
5. 先画像再选档。`profile` 测量每秒咔嗒数、40 Hz 以下能量占比、50 Hz 或 60 Hz 谐波突出程度，建议 `isolated`、`protect` 或 `surface`。每次运行把这份画像和每一级的乐音泄漏写进 `run.yaml`。隆隆声、哼声和去嘶声若把乐音频点一并拿走，这一级整段退回，并记 leakage-reverted。去咔嗒和去裂纹只记录泄漏。

命令行示例放这里，并保证 README 里是同一条：

```text
discrest run --config examples/public_78/run.yaml
discrest verify examples/public_78
```

`verify` 在每台机器上检查输出文件、咔嗒数和标记。SHA-256 只在 `expected.yaml` 里的 `recorded_platform` 上比对。本机工作台负责试听；论文里的数字仍从 `verify` 抄，不要从一次界面操作里估。

### 3. Illustrative examples

示例 A 用 `examples/archive_78`。1919 年爱迪生 Blue Amberol 3639、Arthur Fields 演唱 Irving Berlin 的 *Oh! How I Hate to Get Up in the Morning*，取 Wikimedia Commons 上标注为 unrestored 的文件第 98–118 秒。许可证和 SHA-1 写在该目录 README。`profile` 给出 `protect`，`confident` 为真。`verify` 的结果是 149 个区间：82 个 `isolated-click` 被修复，66 个 `dense-transient` 和 1 个 `sustained-onset` 被留下。去咔嗒移除 RMS 约为 0.0043。被删能量落在留下来的乐音频点上的比例是 0.0335，没有触发 `leakage-reverted`。

同一段上，按 Audacity 2.1 `RemoveClicks` 的默认值（阈值 200、宽度 20）重算，只形成 1 个区间、改写 5 个样本。把阈值降到 40、宽度仍为 20，区间增到 5575，改写 64842 个样本，移除 RMS 约为 0.028。这是同一公开算法的两档参数，不是 Audacity 程序的界面操作。

听感一句先空着。作者听完 `out/restored.wav` 和 `out/residual.wav` 后，用自己的话写残差里还有没有乐句，并写明只有一名作者听过，不是盲听。软件不代写这句。

示例 B 用合成的 `examples/surface`：修复 3 个咔嗒和 3 处裂纹，隆隆声移除 RMS 约为 0.094，哼声约为 0.021。它补上主示例没有打开的滤波和裂纹。`examples/dense_transient` 另有 726 个短区间里 701 个被保护，用来说明过密时的行为。

示例 C 就是 `python -m discrest verify examples/archive_78`。咔嗒数和标记在每台机器上核对。SHA-256 与 `expected.yaml` 的一致限于记录哈希的 Windows 环境：Python 3.12.7、NumPy 1.26.4、SciPy 1.16.3。

### 4. Impact

档案员拿到一段已经数字化的唱筒，要留下哪些区间被删、哪些因为过密或像起音而留下。这段 20 秒的保护档把 67 个区间标成 `protected`，82 个标成修复，并把理由、误差倍数和分级残差放进同一次运行。下一次用 `verify` 核对。

研究上可以换参数再比残差。同一段里，Audacity 算法的阈值从 200 降到 40，改写的样本从 5 个增到 64842 个。DiscRest 这一档的去咔嗒移除 RMS 约为 0.0043。比较的是改了多少、记下了什么，不是听感优劣。

局限照实写：没有盲听；神经网络没有附带权重，打开会停止；默认去嘶声没有在这段上打开。不要写用户数量或下载量。

### 5. Conclusions

复述贡献句。然后两句限制：默认后端不是神经网络；密集瞬态仍会进入残差。最后一句将来工作：可选接入已发表的 U-Net 权重，以及带宽延拓。将来工作不要写成已经完成。

## 5. 参考文献（先放这些）

方法：

- Godsill SJ, Rayner PJW. Digital audio restoration: a statistical model-based approach. London: Springer; 1998. https://doi.org/10.1007/978-1-4471-1561-8
- Moliner E, Välimäki V. A two-stage U-Net for high-fidelity denoising of historical recordings. In: IEEE ICASSP; 2022. https://doi.org/10.1109/ICASSP43922.2022.9746977
- Moliner E, Välimäki V. BEHM-GAN: bandwidth extension of historical music. 对应仓库 [eloimoliner/bwe_historical_recordings](https://github.com/eloimoliner/bwe_historical_recordings)。正式投稿前核对期刊卷期。
- Diffusion-based denoising of historical recordings. J Audio Eng Soc. https://doi.org/10.17743/jaes.2022.0198

软件形态（你已有的 SoftwareX 译本，用来说明“本地、可复现的软件论文”这一写法，不要写成唱片修复的前身）：

- LQL-Equiv-web，本机计算、数据不上传。https://doi.org/10.1016/j.softx.2026.103085
- RespAnno，音频界面中人听模型结果并改正。https://doi.org/10.1016/j.softx.2026.103011
- GANSU Lite，免安装、运行留在用户侧。https://doi.org/10.1016/j.softx.2026.103046

自引规则：上述 SoftwareX 论文作者不是你本人时，只能作为相关工作。DiscRest 发表之后，下一篇才可以自引 DiscRest。

## 6. 仓库最小布局

```text
discrest/
  discrest/declick.py
  discrest/lsar.py
  discrest/chain.py
  discrest/dehiss.py
  discrest/cli.py
  examples/public_78/run.yaml
  examples/dense_transient/run.yaml
  examples/surface/run.yaml
  tests/test_declick_synthetic.py
  tests/test_chain.py
  README.md
  LICENSE
```

合成测试可以先做：在正弦波上叠加已知位置的脉冲，断言这些位置被标出，且残差能量集中在这些位置。这篇测试不代替示例 A，只保证去咔嗒没有把整段信号抹掉。

论文里的图和数字，都从 `examples/public_78` 的一次 `verify` 记录抄下来。记录改了，论文数字一起改。
