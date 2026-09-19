# GIF 合成脚本

依赖 Python 3.10+、Pillow。无需图像生成 API 或网络。脚本支持图片、规则网格、明确裁切框与 GIF 解码帧；不自动推断动作顺序或白边。

```text
python scripts/sticker.py build work/animation.json --output outputs/sticker-v2.gif
python scripts/sticker.py verify outputs/sticker-v2.gif --report work/verified.json
```

路径相对清单文件解析；绝对路径也可用。输出文件已存在时拒绝覆盖，改用版本名。`build` 同时创建 `*.report.json`、`*.frames.png`（成品解码联系表）。

## 清单例子

```json
{
  "size": [240, 240],
  "colors": 128,
  "background": "#ffffff",
  "default_duration_ms": 70,
  "sources": {
    "sheet": {
      "path": "../input/grid.png",
      "grid": {"columns": 3, "rows": 3, "inset": 2}
    },
    "patch": {
      "path": "../input/inbetweens.png",
      "boxes": [[0, 0, 400, 400], [406, 0, 806, 400]]
    }
  },
  "sequence": [
    {"source": "sheet", "index": 0, "duration_ms": 300},
    {"source": "patch", "index": 0},
    {"source": "patch", "index": 1},
    {"source": "sheet", "index": 1, "duration_ms": 220}
  ]
}
```

`grid.inset` 对每格四边统一内缩，是像素数，不会自动检测白边。规则网格可另指定 `bounds: [left, top, right, bottom]` 与 `gap: [horizontal, vertical]`。已知每格精确边界时，优先用 `boxes`，右、下边界不包含在裁切内。

源没有 `grid`/`boxes` 时，静态图产生一帧，GIF 产生其所有解码帧。源帧时长不自动继承，时间轴逐项明确控制。`index` 从 0 开始，显式重复条目可用来倒序复用动作。

非正方形帧按比例缩放并用 `background` 填充，不拉伸。透明输入默认合到背景色；脚本不保留透明 GIF，透明表情需求需采用适合透明边缘的独立编码方案并检查边缘。

可选固定字幕：

```json
"caption": {
  "text": "不想上班…",
  "font": "C:/Windows/Fonts/msyhbd.ttc",
  "font_size": 25,
  "xy": [15, 15],
  "fill": "white",
  "stroke_width": 1,
  "stroke_fill": "#413a36"
}
```

字体路径只作示例，选择当前机器可用且包含所需字符的字体。脚本不会清除图片已有文字；已有字幕需要保留或处理，应在上游明确决定。

`max_bytes` 可设期望大小。超出时报告 `size_target_met=false`，保留结果用于调整；不会静默删帧或降尺寸。时长须至少 20 ms 且是 10 ms 的倍数，避免过短时长在常见播放器中被钳制。限制是本脚本的兼容性选择，不是平台官方规定。

报告中的 `unique_decoded_frames` 是逐帧像素哈希去重数，不保证动作不同；`largest_changes` 列出包含末帧回首帧在内的像素差异，供定位候选断点。它不等于光流、感知质量或流畅度评分。联系表需人工视觉检查。
