"""
火焰检测调试脚本 v2。
用法: python fire_debug.py <图片路径>

输出:
  1. HSV 直方图分析（告诉你图片里有什么颜色）
  2. 每个 Range 的匹配像素数
  3. RGB warm color 兜底掩码
  4. 形态滤波和连通域过滤后的结果
  5. 最终判定
"""
import sys
import cv2
import numpy as np

# ---- 检测参数（与 services.py 同步）----
HSV_RANGES = [
    ("Range1 红/橙/黄", (0, 50, 60), (40, 255, 255)),
    ("Range2 深红/品红", (150, 50, 60), (180, 255, 255)),
    ("Range3 白热核心", (15, 15, 180), (45, 130, 255)),
]
RGB_WARM = True           # 是否开启 RGB 暖色兜底
AREA_THRESHOLD = 0.01     # 1%
MIN_CONTOUR = 60


def _warm_rgb_mask(bgr):
    """RGB 暖色像素：R 通道明显大于 G 和 B（火焰特征）。"""
    r = bgr[:, :, 2].astype(np.float32)
    g = bgr[:, :, 1].astype(np.float32)
    b = bgr[:, :, 0].astype(np.float32)
    # 红色主导 + 有一定亮度
    mask = (r > g * 1.15) & (r > b * 1.3) & (r > 60)
    return (mask * 255).astype(np.uint8)


def debug_fire(image_path: str):
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"无法读取图片: {image_path}")
        sys.exit(1)

    h, w = frame.shape[:2]
    total_px = w * h
    print(f"图片尺寸: {w}x{h}, 总像素: {total_px}")
    print()

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ---- 1. HSV 颜色分布分析 ----
    print("=" * 55)
    print("HSV 颜色分布")
    print("=" * 55)
    # 只分析非暗像素 (V > 40)
    bright_mask = hsv[:, :, 2] > 40
    bright_h = hsv[:, :, 0][bright_mask]
    bright_s = hsv[:, :, 1][bright_mask]
    bright_v = hsv[:, :, 2][bright_mask]
    bright_count = np.count_nonzero(bright_mask)

    if bright_count > 0:
        print(f"  非暗像素 (V>40): {bright_count} ({bright_count/total_px:.2%})")
        print(f"  H 范围: {bright_h.min()}..{bright_h.max()}  (均值 {bright_h.mean():.0f})")
        print(f"  S 范围: {bright_s.min()}..{bright_s.max()}  (均值 {bright_s.mean():.0f})")
        print(f"  V 范围: {bright_v.min()}..{bright_v.max()}  (均值 {bright_v.mean():.0f})")

        # 按色调区间统计
        warm_h = bright_h[(bright_h <= 50) | (bright_h >= 150)]
        warm_pct = len(warm_h) / bright_count * 100 if bright_count > 0 else 0
        print(f"  暖色调像素(H≤50或H≥150): {len(warm_h)} ({warm_pct:.1f}% 的非暗像素)")

        # 暖色调中高饱和的
        warm_high_s = bright_count and np.count_nonzero(
            ((hsv[:, :, 0] <= 50) | (hsv[:, :, 0] >= 150))
            & (hsv[:, :, 1] > 50) & (hsv[:, :, 2] > 40)
        )
        print(f"  暖色+中高饱和(H≤50或≥150, S>50, V>40): {warm_high_s}")
    else:
        print("  ⚠️ 图片几乎全黑 (V>40 像素不足)")
    print()

    # ---- 2. 各 Range 匹配测试 ----
    print("=" * 55)
    print("HSV Range 匹配测试")
    print("=" * 55)
    combined = np.zeros((h, w), dtype=np.uint8)
    for name, lower, upper in HSV_RANGES:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        area = cv2.countNonZero(mask)
        ratio = area / total_px
        status = "✓" if ratio >= 0.005 else "✗"
        print(f"  {status} {name} ({lower}~{upper}): {area}px ({ratio:.2%})")
        combined = cv2.bitwise_or(combined, mask)
        cv2.imwrite(f"debug_fire_{name}.png", mask)

    hsv_total = cv2.countNonZero(combined)
    print(f"  → HSV 合并: {hsv_total}px ({hsv_total/total_px:.2%})")

    # ---- 3. RGB 暖色兜底 ----
    if RGB_WARM:
        rgb_mask = _warm_rgb_mask(frame)
        rgb_area = cv2.countNonZero(rgb_mask)
        print(f"  → RGB 暖色兜底: {rgb_area}px ({rgb_area/total_px:.2%})")
        combined = cv2.bitwise_or(combined, rgb_mask)
        cv2.imwrite("debug_fire_rgb_warm.png", rgb_mask)
    else:
        rgb_area = 0

    total_combined = cv2.countNonZero(combined)
    print(f"  → 总合并: {total_combined}px ({total_combined/total_px:.2%})")
    cv2.imwrite("debug_fire_combined.png", combined)
    print()

    # ---- 4. 形态滤波 ----
    print("=" * 55)
    print("形态滤波")
    print("=" * 55)
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_small, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large, iterations=2)
    morph_area = cv2.countNonZero(mask)
    print(f"  开运算+闭运算后: {morph_area}px ({morph_area/total_px:.2%})")

    # ---- 5. 连通域过滤 ----
    print()
    print("=" * 55)
    print("连通域过滤 (min={}px)".format(MIN_CONTOUR))
    print("=" * 55)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    clean_mask = np.zeros_like(mask)
    kept = 0
    largest_area = 0
    for label_id in range(1, num_labels):
        area = stats[label_id, cv2.CC_STAT_AREA]
        if area >= MIN_CONTOUR:
            clean_mask[labels == label_id] = 255
            kept += 1
            if area > largest_area:
                largest_area = area
    final_area = cv2.countNonZero(clean_mask)
    print(f"  保留 {kept} 个连通域, 最大: {largest_area}px")
    print(f"  最终面积: {final_area}px ({final_area/total_px:.2%})")
    cv2.imwrite("debug_fire_clean.png", clean_mask)
    print()

    # ---- 6. 最终判定 ----
    ratio = final_area / total_px
    print("=" * 55)
    if ratio >= AREA_THRESHOLD:
        print(f"✅ 检测成功! {ratio:.2%} >= {AREA_THRESHOLD:.1%}")
        contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, fw, fh = cv2.boundingRect(largest)
            result = frame.copy()
            cv2.rectangle(result, (x, y), (x + fw, y + fh), (0, 0, 255), 2)
            cv2.putText(result, f"FIRE {ratio:.1%}", (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.imwrite("debug_fire_result.png", result)
            print("标注结果: debug_fire_result.png")
    else:
        print(f"❌ 检测失败! {ratio:.2%} < {AREA_THRESHOLD:.1%}")
        if hsv_total == 0:
            print("   根因: HSV 三个 Range 匹配像素 = 0")
            print("   → 火焰颜色不在任何 HSV Range 内，需要扩大范围")
        elif final_area == 0:
            print("   根因: 形态滤波或连通域过滤后像素归零")
            print(f"   → 形态滤波前={total_combined}px, 后={morph_area}px")
        elif ratio < AREA_THRESHOLD:
            print(f"   根因: 面积不足 ({ratio:.2%} < {AREA_THRESHOLD:.1%})")
            print(f"   → 降低 AREA_THRESHOLD 或 MIN_CONTOUR")
    print("=" * 55)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fire_debug.py <火焰图片路径>")
        print("输出: debug_fire_Range*.png / combined.png / clean.png / result.png")
        print("     终端显示 HSV 分布 + 每步像素统计")
        sys.exit(1)
    debug_fire(sys.argv[1])
