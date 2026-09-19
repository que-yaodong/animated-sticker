# 补帧与连贯性

## 将“更顺滑”转换为具体动作

先定位断点：头部角度跳跃、身体或镜头位移、物体遮挡突然变化、文字闪动、节奏不均或首尾不匹配。只修复相关片段。总帧数是结果，不是质量门槛。

可采用的起步分配（不是固定要求）：

| 断点 | 可尝试的新姿势 | 要求 |
| --- | --- | --- |
| 正脸直接跳侧脸 | 4–8 个中间角度 | 眼睛先动，头部缓慢跟随；检查转回过程 |
| 脸突然被盖住 | 6–12 个遮挡阶段 | 遮挡边缘连续经过额头、眼睛、鼻子 |
| 从隐藏直接出现 | 6–12 个露出阶段 | 鼻、眼、头部、肢体依次出现 |
| 眨眼/闭眼 | 3–6 个眼睑状态 | 尽量固定头部位置和尺度 |
| 首尾跳动 | 2–4 个接回姿势，或选择更接近的首尾锚点 | 比较表情、位置及道具状态 |

双向转头可以倒序复用相同角度，但须调整停顿；毛发、呼吸和遮挡等不一定适合倒播。明确区分时间轴总帧数和不同画面数量。

## 生成小段而非盲目扩大网格

提供已查看过的起点与终点裁图。生成器可能忽略精确姿势、列数或锁定背景的要求，因此必须验图。2×2、4×2、4×4 等简单网格常便于裁切；任何布局均需检查实际尺寸。一次多个独立资产时，按工具要求分次调用。

提示词模板（替换变量，不绑定本案例）：

```text
Use reference 1 as the exact start and reference 2 as the exact end.
Create one [columns] by [rows] sprite sheet of equal square cells,
fully visible, no gutters, borders, numbering or captions.
Read left to right then top to bottom; never restart at row boundaries.
Preserve [identity, camera, scale, light, fixed scene anchors].
Only change [specific body part/object].
Generate small monotonic intermediate steps: [pose progression].
Maintain physical occlusion and contact; no sudden pose jumps,
no duplicate poses, no double exposure, no crossfades.
Match the endpoints and keep background geometry fixed.
```

除非用户需要，不把多个变化字幕一起交给生成器。需要固定字幕时可在合成阶段用固定字形与位置处理。不得将整张含多格图缩小当作动画帧。

## 验图与停止条件

- 先数实际格子，再检查姿势是否递进及端点是否匹配。部分格子截断时不能凭空补出内容。
- 用一致画幅裁切；逐帧独立居中会抵消真实动作或造成呼吸式缩放。
- 新增姿势之间也可能存在跳变。看“上一帧 → 新片段 → 下一帧”，不能只看新图本身好不好看。
- 背景固定或微小配准可改善漂移，但不要冻结会被角色遮挡的区域，也不要把几何变形、像素混合称作新生成动作。
- 有明确质量缺陷时可针对该段修正一轮；不能把一次成功案例的帧数变成无限补图目标。无法完全消除的漂移如实交付说明。

## 本技能的经验来源与边界

一次九宫格案例先做 9 帧，再尝试渐变，出现叠影；后续通过补充转头、遮挡和探头姿势，最终得到 65 个时间轴帧、58 个不同画面，用户接受定稿。这个结果说明针对动作断点补图有用，并不证明 65 帧是通用最优值。该案例仅核验 GIF 文件与视觉联系表，没有微信发送实测。生成过程中也遇到布局截断和新帧自身跳动，应作为验图依据而非对生成能力作保证。
