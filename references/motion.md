# 动作衔接与补间

## 先定位问题，再选方法

把“不流畅”拆成可检查的现象：姿势突然跳变、手和头脱节、嘴型结构变化、遮挡穿帮、匀速运动突然折返、循环接缝或单纯播放太快。先看原始帧与时间线，不直接堆到某个帧数。

| 情况 | 处理 |
| --- | --- |
| 姿势已连续，只是太快/慢 | 调整时长，保留图像顺序；补帧不能替代调速 |
| 小幅位移，轮廓与纹理对应关系清楚 | 尝试双向稠密光流对齐补间，检查手指、嘴、头饰等细节 |
| 大转头、藏进被子再探头、手形明显变化 | 生成真实中间姿势，不用光流猜测新露出的部位 |
| 嘴从细线变成大开口、牙齿出现 | 先检查是否缺少嘴型；简单形变很容易拉坏嘴巴 |
| 往返像机械折返 | 在两个转向点前减速、后加速，检查运动方向与速度连续性 |
| 背景颜色跟着动 | 先处理背景分层与全局调色板，见 [背景指南](background-and-qa.md) |

双向运动对齐会使用两端图像的像素，仍可能有拉伸、双影或局部错误，不能描述成生成了新画的姿势。全图交叉淡化只叠加两张图，通常不能解决动作跳跃；不要把它当作默认补帧。

## 缓动与循环

对于已经确认适合对称往返的动作，设一程共有 `K` 个相近姿势、循环进度为 `u∈[0,1)`，可采用 `p=(K-1)*(1-cos(2πu))/2`。它让整体在两端减速并反向；不保证中间姿势边界的全部局部速度都连续，也不自动修复形变。

不要给每个小间隔都强行“停住再启动”，否则会产生多个小顿点。不要为了首尾相同把完整终点重复追加到结尾制造停顿；核对末帧到下一轮首帧的运动趋势。

自然的眨眼、笑、头发回弹、不同方向的摆手通常并非严格可逆。参考视频存在先后节奏或惯性时，保留独立回程姿势与原节拍，不用对称倒放替代。手、头、脸、身体应按参考共同表演；不要临时给已认可的人物新增大幅摇晃。

总时长和帧数分开决定。增加帧数后，在原定时长内分配新帧；用户未要求减速时不要自动拉长。小幅连续循环可试 20–40 ms/帧；有文字阅读、反应停顿的叙事表情另设关键帧时长。它们是起点，不是平台规范。工具不写入低于 20 ms 的帧；例如 60 帧、0.6 秒与此兼容性选择冲突，应说明改用较少帧或较长循环，而非悄悄改成 10 ms。

## 可复用的小幅运动工具

`scripts/smooth_loop.py` 适合已对齐、不透明的姿势序列。需要 Pillow、NumPy、OpenCV，基础裁帧工具仍只需 Pillow。

```bash
python -m pip install -r requirements-motion.txt
python scripts/smooth_loop.py work/motion.json --output outputs/smooth-v1.gif
```

清单路径以清单目录为基准。以下只是四姿势往返示例，帧数、时长、尺寸按实际任务选择：

```json
{
  "source": "selected.gif",
  "indices": [0, 1, 2, 3],
  "mode": "pingpong",
  "frames": 60,
  "duration_ms": 1800,
  "colors": 128,
  "static_mask": "always-visible-background.png",
  "require_exact_frames": true
}
```

- 输入可改为 `"sources": ["pose0.png", "pose1.png", "pose2.png"]`，与 `source` 二选一。尺寸必须一致，透明图先合成到选定底图。
- `pingpong` 只传单程姿势，不把返回段再传一次；`cycle` 传完整环形路径，工具也补最后姿势→第一个姿势，使用线性循环进度，不强加往返。两者都不恢复源 GIF 原有的非均匀停顿；需要精确节拍时使用自定义姿势/时间清单。
- `static_mask` 可省略；提供时必须为同尺寸二值图，白色表示确认始终静止的区域，黑色表示可能运动。这里与人物 alpha 语义相反，不能直接传人物抠图。白色区域恢复首个姿势的背景像素；它不是完整背景重建工具。
- 时长须为 10 ms 的整数倍，且至少 `frames×20 ms`。整数余量分配到各帧，保证总时长。相同帧数和姿势、更换总时长时保持图像顺序不变。
- 工具拒绝覆盖输出，生成 GIF、解码报告和完整联系表。GIF 可能合并相邻重复帧；`require_exact_frames` 为真时帧数不符会标记失败。不会加噪点强行凑帧。
- `max_bytes` 可选，仅报告是否达标，不擅自删姿势。数值检查不等于视觉通过或微信实测。

## 需要补画时

一次处理一个明确断点，例如转头可试 4–8 张中间角度，遮挡/露出可试 6–12 张分阶段姿势。数量取决于缺口，不是保底要求。提供已查看的起止图，先补最明显跳跃，再检查与原片段的衔接。

```text
Use reference 1 as the exact start and reference 2 as the exact end.
Create one [columns] by [rows] sprite sheet of equal square cells,
fully visible, no gutters, borders, numbering or captions.
Read left to right then top to bottom; never restart at row boundaries.
Preserve [identity, camera, scale, light, fixed scene anchors].
Only change [specified coordinated parts of the character].
Generate small monotonic intermediate steps: [pose progression].
Maintain physical occlusion and contact; no sudden pose jumps,
no duplicate poses, no double exposure, no crossfades.
Match the endpoints and keep background geometry fixed.
```

实际查看生成网格是否完整、每格是否等大、姿势是否递进；任何边界按真实尺寸裁切。不要凭空补全被截断的角色。固定字幕宜在合成阶段以统一字体、位置绘制；用户要变化字幕时保留意图。

每次只针对明确缺陷修正一轮，重新核对“原片段最后一帧→补片段→下一帧”和整个循环。仍有变形就更换方法或说明限制，不进行没有停止条件的反复生成。案例证据与适用边界见 [案例记录](case-studies.md)。
