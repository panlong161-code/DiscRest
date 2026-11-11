# 1919 年未修复唱筒，20 秒

这段是论文里的真实录音示例，不是合成信号。

来源是 Wikimedia Commons 文件 “Irving Berlin - Arthur Fields - Oh! How I Hate To Get Up In The Morning (unrestored).ogg”。Commons 记录它由 Adam Cuerden 于 2008-10-04 上传，内容来自加州大学圣塔芭芭拉分校唱筒数字化项目的未修复版本。曲目是 Irving Berlin 的 *Oh! How I Hate to Get Up in the Morning*，Arthur Fields 演唱，爱迪生 Blue Amberol 3639，模版号 6287，录音年份 1919。文件页：<https://commons.wikimedia.org/wiki/File:Irving_Berlin_-_Arthur_Fields_-_Oh!_How_I_Hate_To_Get_Up_In_The_Morning_(unrestored).ogg>。原文件 SHA-1 为 `7ce2e563c46b997496517f82bc39d77be3611af2`，与本仓库下载到的 ogg 一致。

美国法下，1926 年 1 月 1 日之前出版的录音属于公有领域（17 U.S.C. § 1401）。1918 年在美国出版的曲谱，其美国版权也已届满。Commons 同时写明，这段录音在美国以外未必处于公有领域。

仓库里的 `input.wav` 只保留原文件 98.000 秒到 118.000 秒。立体声先由 ffmpeg 混成单声道，采样率 44100 Hz，16-bit PCM。`profile` 对这 20 秒给出 `protect`，而且测量远离分界。因此 `run.yaml` 使用保护档：只做去咔嗒，过密的窗和起音不替换。

对照算法是 Audacity 2.1 的 Click Removal，按 Craig DeForest 的 `RemoveClicks` 实现，默认阈值 200、宽度 20。它不是 Audacity 程序本身。另记一档更敏感的阈值 40，用来说明把同一个算法调灵敏之后会改掉多少样本。数字在 `comparison.yaml`，由测试重算。

这里没有盲听，也没有代写“残差里还能听见乐句”。作者要听 `out/restored.wav` 和 `out/residual.wav` 之后，自己补那一句。
