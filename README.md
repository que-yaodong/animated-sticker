# 动态表情包制作 · Animated Sticker

把角色参考、九宫格或已有动作序列做成可下载的循环 GIF，也可修正已有表情的动作跳跃、背景闪烁与转向生硬。

本仓库包含 **Codex Skill**、基础裁帧合成工具，以及可选的小幅运动补间工具。先检查动作、节奏和背景，再决定补图或补间；不把“更多帧”直接当成“更流畅”。

## 效果示例

![不想上班动态表情](examples/dont-want-to-work.gif)

“不想上班”示例从九宫格开始，补充转头、遮挡与探头姿势后形成循环。已验证 240×240、65 个时间轴帧、58 张不同画面，每轮 5.32 秒，`loop=0`，1,539,307 字节。以上是文件验证，未做微信发送实测。

本技能还记录了“开心摆手”的用户反馈：回到用户选定的原版，分离固定背景，使用运动对齐补间和柔和的往返节奏后获得认可。该案例是 60 个时间轴帧、31 张不同画面、每轮 1.8 秒，**不是所有表情包的固定模板**。完整依据与限制见 [案例记录](references/case-studies.md)。

## 能做什么

- 测量九宫格或 sprite sheet 的实际边界，去除格间白边，裁帧并统一构图。
- 根据姿势缺口安排小段补图；新姿势需由运行环境中的图像工具提供。
- 对相近姿势做双向运动对齐补间，按适用条件添加往返缓动。
- 指导人物与固定背景分层，保护已认可人物，避免背景颜色闪烁。
- 编码后重新检查帧数、不同画面数、时长、循环、体积及指定背景区域，生成联系表。

## 安装为 Codex Skill

Windows PowerShell：

```powershell
$skillRoot = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $env:USERPROFILE '.codex/skills' }
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
git clone https://github.com/que-yaodong/animated-sticker.git (Join-Path $skillRoot 'animated-sticker')
```

macOS / Linux：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/que-yaodong/animated-sticker.git "${CODEX_HOME:-$HOME/.codex}/skills/animated-sticker"
```

同名技能已存在时先检查本地修改，再合并更新，避免覆盖定制内容。在可发现此技能的会话中调用 `$animated-sticker`。

```text
使用 $animated-sticker，把这张九宫格做成循环 GIF，保留原画面。
```

```text
使用 $animated-sticker，以我选中的 GIF 为基准，固定背景，改善动作转向与首尾衔接。
```

```text
使用 $animated-sticker，参考这段视频的手、头、表情配合，给这个角色制作动态表情。
```

技能不附带模型、服务账号或 API 密钥。需要新增画面时，使用所在环境已授权的图像能力；本地脚本不调用生成服务。

## 基础裁帧与合成

需要 Python 3.10+、Pillow。以下命令在仓库目录执行，`python` 应替换成环境中实际可用的运行时。

```bash
python -m pip install -r requirements.txt
python scripts/sticker.py build work/animation.json --output outputs/sticker-v1.gif
python scripts/sticker.py verify outputs/sticker-v1.gif
```

以下清单只适用于**无分隔线、等大格子**的 3×3 图片；有白边或不规则格子时使用实测 `boxes`：

```json
{
  "size": [240, 240],
  "colors": 128,
  "default_duration_ms": 90,
  "sources": {"original": {"path": "source.png", "grid": {"columns": 3, "rows": 3}}},
  "sequence": [
    {"source": "original", "index": 0, "duration_ms": 300},
    {"source": "original", "index": 1},
    {"source": "original", "index": 2},
    {"source": "original", "index": 3},
    {"source": "original", "index": 4},
    {"source": "original", "index": 5},
    {"source": "original", "index": 6, "duration_ms": 300},
    {"source": "original", "index": 7},
    {"source": "original", "index": 8, "duration_ms": 200}
  ]
}
```

路径相对清单文件，索引从 0 开始。工具输出 GIF、`.report.json` 和 `.frames.png`，拒绝覆盖已有结果。完整格式见 [合成说明](references/build.md)。

## 小幅运动补间（可选）

```bash
python -m pip install -r requirements-motion.txt
python scripts/smooth_loop.py work/motion.json --output outputs/smooth-v1.gif
```

适用于尺寸一致、已合成背景、轮廓差异较小的姿势。它按双向稠密光流对齐图像后补间，支持明确选择往返缓动或完整环形路径。清单示例、固定背景遮罩语义与时长限制见 [动作指南](references/motion.md)。

该工具不是新姿势生成器。大幅转头、显著遮挡、嘴型或手形结构变化可能出现变形，需要补画真实姿势。只调速与只去背景时，不应顺带重新计算人物动作。

## 质量与边界

- 先锁定用户认可的版本，后续编辑另存文件；参考视频要分析手、头、表情与身体的配合。
- 固定背景应使用同一底图和全局调色板，检查发丝、手部与新露出的背景。背景数值检测只证明指定区域稳定。
- 工具选择每帧至少 20 ms，使用 10 ms 的整数倍；帧数与目标速度冲突时明确取舍。
- 240×240、128/256 色只是体积起点，不是微信官方规定，也不能保证任何客户端都可保存。
- 基础工具和运动工具均不导出透明 GIF；透明 PNG 人物层需另行合成和检查边缘。
- 文件验证、静态视觉检查、实际播放、用户认可和平台发送实测分别记录，不相互替代。

细节见 [背景与验收](references/background-and-qa.md)。数值通过后仍要查看脸、手、转向和循环接缝；不能承诺所有素材一次通过。

## 仓库内容

| 文件 | 用途 |
| --- | --- |
| `SKILL.md` | 工作入口与处理路线 |
| `references/motion.md` | 补图、运动补间与节奏选择 |
| `references/background-and-qa.md` | 背景分层和验收 |
| `references/case-studies.md` | 用户反馈支持的案例与边界 |
| `references/build.md` | 基础合成清单说明 |
| `scripts/sticker.py` | 裁帧、编码、重新解码检查 |
| `scripts/smooth_loop.py` | 可选运动补间与固定区域校验 |
| `tests/test_smooth_loop.py` | 运动工具的行为验证 |
| `examples/` | 已有成品示例 |

运行可选工具测试：`python -m unittest discover -s tests`。反馈可通过 [Issues](https://github.com/que-yaodong/animated-sticker/issues) 提交，请附断点位置、文件参数和可分享的参考画面。
