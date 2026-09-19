# 动态表情包制作 · Animated Sticker

把角色参考、九宫格或动作序列制作成可下载的循环 GIF 表情包，也能针对已有动图的转头、遮挡、探头等动作补充中间姿势。

这个仓库包含一个 **Codex Skill** 和一个可独立运行的 **Python 合成工具**。Skill 负责组织创作、补帧和检查流程；Python 工具负责裁切、编码与成品核验，**不会自行生成新的动作图片**。

## 效果示例

![不想上班动态表情](examples/dont-want-to-work.gif)

“不想上班”示例从九宫格开始，经动作补帧与节奏调整形成完整循环：醒来 → 看闹钟 → 闭眼 → 躲进被窝 → 再探头。

| 属性 | 已验证结果 |
| --- | --- |
| 时间轴帧数 | 65 帧 |
| 不同解码画面 | 58 张，部分转回动作复用已有角度 |
| 尺寸 | 240 × 240 像素 |
| 每轮时长 | 5.32 秒 |
| 循环 | 无限循环，`loop=0` |
| 文件大小 | 1,539,307 字节，约 1.47 MiB |

[下载示例 GIF](examples/dont-want-to-work.gif)。示例仍有轻微画面位置变化；这些数据是文件核验结果，不代表已在微信客户端实测发送。

## 能做什么

- **原图裁帧**：从九宫格、规则网格或明确的裁切框提取独立画面，去除分隔线并统一画幅。
- **动作补帧**：借助环境中可用的图像生成工具，补齐相邻姿势，优先处理明显跳变。
- **节奏与循环**：单独设置每帧时长，保留关键表情停顿，检查首尾衔接。
- **固定字幕与体积控制**：可选固定字幕、输出尺寸和统一调色板。
- **成品验证**：重新解码 GIF，核验实际帧数、不同画面数、循环属性、时长和文件大小，输出可视化帧联系表。

补帧增加的是动作姿势。简单渐变可能出现叠影，不能代替真正的动作变化；更多帧也不自动等于更流畅。

## 安装为 Codex Skill

将仓库克隆到个人技能目录中的 `animated-sticker` 文件夹。若配置了 `CODEX_HOME`，使用其下的 `skills` 目录；否则通常使用用户目录下的 `.codex/skills`。

### Windows PowerShell

```powershell
$skillRoot = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $env:USERPROFILE '.codex/skills' }
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
git clone https://github.com/que-yaodong/animated-sticker.git (Join-Path $skillRoot 'animated-sticker')
```

### macOS / Linux

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/que-yaodong/animated-sticker.git "${CODEX_HOME:-$HOME/.codex}/skills/animated-sticker"
```

如果同名技能已经存在，先保留现有版本，再决定更新方式，避免覆盖自己的修改。安装后在可发现该技能的任务中使用 `$animated-sticker`。

### 调用示例

```text
使用 $animated-sticker，把这张九宫格裁成动态表情，保留原画面，输出无限循环 GIF。
```

```text
使用 $animated-sticker，这个动图转头太突然，请补齐转头和转回的中间角度，保留其余动作。
```

```text
使用 $animated-sticker，参考这只猫做一个“收到”的动态表情，镜头固定，字幕固定，控制文件大小。
```

仅裁帧与合成不需要图像生成服务。需要从零绘制或补充新姿势时，运行环境须提供可用的图像生成能力；其账号、费用与限制由对应服务决定。本仓库不捆绑模型或 API 密钥。

## 独立使用合成工具

需要 Python 3.10+ 和 Pillow。以下命令在仓库根目录运行；请将 `python` 替换为机器上实际可用的 Python 命令。

```bash
python -m pip install -r requirements.txt
python scripts/sticker.py build work/animation.json --output outputs/sticker-v1.gif
```

将原图放到 `work/source.png`，并在 `work/animation.json` 中写入清单。以下示例假定图片是**无分隔线、尺寸均匀的 3×3 网格**；有白边或不规则边界时应使用实测裁切框。

```json
{
  "size": [240, 240],
  "colors": 128,
  "default_duration_ms": 90,
  "sources": {
    "original": {
      "path": "source.png",
      "grid": {"columns": 3, "rows": 3}
    }
  },
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

源路径相对清单文件解析，索引从 0 开始。生成结果包括：

```text
outputs/sticker-v1.gif          动态表情
outputs/sticker-v1.report.json  解码核验报告
outputs/sticker-v1.frames.png   带帧号和时长的联系表
```

单独核验已有 GIF：

```bash
python scripts/sticker.py verify examples/dont-want-to-work.gif
```

工具拒绝覆盖已有输出；修改后使用新的文件名。相同连续帧可能被编码器合并，报告会记录请求帧数和实际帧数。完整清单选项、网格间距、裁切框、GIF 输入和字幕设置见 [合成工具说明](references/build.md)。

## 如何改善连贯性

先看最明显的断点，再决定补多少图。例如，转头要有连续角度；盖被子需要逐步遮住额头、眼睛、鼻子；探头则要补齐鼻子、眼睛、头部和爪子的出现过程。背景、角色大小和相机位置尽量保持一致。

建议把长动作拆成短片段，用起点和终点作为生成参考。生成完检查真实行列布局与姿势递进，再裁切合成。补图后要重新分配每帧时长，避免只把动画拉长。详细方法见 [动作补帧指南](references/motion.md)。

## 使用边界

- 240×240、128/256 色是便于制作小表情的起点，不是微信官方限制，也不保证所有客户端均可保存。
- 工具默认将透明输入合到背景色，不输出透明 GIF。
- 当前脚本不执行光流补帧、视频生成或自动语义动作评分。
- 相邻像素差异只用于定位候选跳变，不能代替播放检查和平台实测。
- 生成服务仍可能产生身份漂移、构图变化或不完整网格，需要视觉检查。

## 仓库结构

```text
SKILL.md                 技能入口与工作原则
agents/openai.yaml       技能名称与默认调用提示
references/motion.md     补帧策略与经验边界
references/build.md      清单格式和工具说明
scripts/sticker.py       裁帧、合成与验证工具
examples/                已完成的动态表情示例
requirements.txt         本地工具依赖
```

改进建议和问题可通过 [Issues](https://github.com/que-yaodong/animated-sticker/issues) 提交。描述问题时附上具体跳变位置、尺寸、帧数及可分享的参考画面，会更容易复现。
