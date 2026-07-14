"""把 GitHub Network 多张横向截图拼成一张长图。

用法：
1. 在浏览器打开 Network，Ctrl+- 缩到约 67%
2. 用 Win+Shift+S 截当前可见图，保存为 part-01.png
3. 在图上按住左键向右拖（露出更早提交），再截 part-02.png、part-03.png …
4. 把 part-*.png 放进下方 INPUT_DIR，运行本脚本

  python scripts/stitch_network_screenshots.py

输出：docs/项目管理/结题截图/第5部分/02-network.png
"""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except ImportError as e:
    raise SystemExit("需要 Pillow：pip install Pillow") from e

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "docs" / "项目管理" / "结题截图" / "第5部分" / "network-parts"
OUTPUT = ROOT / "docs" / "项目管理" / "结题截图" / "第5部分" / "02-network.png"

# 横向拼接时去掉每张右侧重叠区（像素）。重叠少就调小，接缝明显就调大。
OVERLAP_CROP_RIGHT = 80


def main() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    parts = sorted(
        [
            *INPUT_DIR.glob("part-*.png"),
            *INPUT_DIR.glob("part-*.jpg"),
            *INPUT_DIR.glob("part-*.jpeg"),
            *INPUT_DIR.glob("part-*.webp"),
        ]
    )
    if len(parts) < 2:
        print(f"请在目录中放入至少 2 张截图：\n  {INPUT_DIR}")
        print("命名示例：part-01.png  part-02.png  part-03.png")
        print("（按时间从新→旧，或从右→左，保持同一顺序即可）")
        raise SystemExit(1)

    images = [Image.open(p).convert("RGB") for p in parts]
    heights = [im.height for im in images]
    h = min(heights)
    # 统一高度（以最矮的为准，顶部对齐裁剪）
    cropped = []
    for i, im in enumerate(images):
        if im.height != h:
            im = im.crop((0, 0, im.width, h))
        # 中间段去掉左侧一点重叠，首张保留全宽
        if i == 0:
            cropped.append(im)
        else:
            left = min(OVERLAP_CROP_RIGHT, im.width // 5)
            cropped.append(im.crop((left, 0, im.width, h)))

    total_w = sum(im.width for im in cropped)
    out = Image.new("RGB", (total_w, h), (255, 255, 255))
    x = 0
    for im in cropped:
        out.paste(im, (x, 0))
        x += im.width

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUTPUT, "PNG")
    print(f"已拼接 {len(parts)} 张 → {OUTPUT}")
    print(f"尺寸：{out.width} x {out.height}")


if __name__ == "__main__":
    main()
