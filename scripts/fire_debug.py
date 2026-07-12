"""
火焰检测调试脚本。
用法: python fire_debug.py <图片路径>

生成 4 张中间结果图，帮助诊断 HSV 阈值是否匹配你的火焰图片。
"""
import sys
import cv2
import numpy as np

# 当前配置
HSV_RANGES = [
    ("Range1 红/橙/黄", (0, 50, 60), (40, 255, 255)),
    ("Range2 深红/品红", (150, 50, 60), (180, 255, 255)),
    ("Range3 白热核心", (15, 15, 180), (45, 130, 255)),
]

AREA_THRESHOLD = 0.01   # 1%
MIN_CONTOUR = 60


def debug_fire(image_path: str):
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"无法读取图片: {image_path}")
        sys.exit(1)

    h, w = frame.shape[:2]
    print(f"图片尺寸: {w}x{h}, 总面积: {w*h}px")

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 1. 分别看每个颜色掩码
    combined = np.zeros((h, w), dtype=np.uint8)
    for name, lower, upper in HSV_RANGES:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        area = cv2.countNonZero(mask)
        ratio = area / (w * h)
        print(f"  {name}: {area}px ({ratio:.2%})")
        combined = cv2.bitwise_or(combined, mask)
        cv2.imwrite(f"debug_fire_{name}.png", mask)

    total_before = cv2.countNonZero(combined)
    print(f"  合并后: {total_before}px ({total_before/(w*h):.2%})")

    # 2. 形态滤波
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_small, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large, iterations=2)
    after_morph = cv2.countNonZero(mask)
    print(f"  形态滤波后: {after_morph}px ({after_morph/(w*h):.2%})")

    # 3. 连通域过滤
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    clean_mask = np.zeros_like(mask)
    kept = 0
    for label_id in range(1, num_labels):
        area = stats[label_id, cv2.CC_STAT_AREA]
        if area >= MIN_CONTOUR:
            clean_mask[labels == label_id] = 255
            kept += 1
    final_area = cv2.countNonZero(clean_mask)
    print(f"  连通域过滤后: {final_area}px ({final_area/(w*h):.2%}), 保留 {kept} 个连通域")

    # 4. 判断
    ratio = final_area / (w * h)
    if ratio >= AREA_THRESHOLD:
        print(f"\n✅ 火焰检测成功! 占比 {ratio:.2%} >= {AREA_THRESHOLD:.1%}")
        # 提取最大连通域
        contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, fw, fh = cv2.boundingRect(largest)
            result = frame.copy()
            cv2.rectangle(result, (x, y), (x + fw, y + fh), (0, 0, 255), 2)
            cv2.putText(result, f"FIRE {ratio:.1%}", (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.imwrite("debug_fire_result.png", result)
            print("标注结果已保存: debug_fire_result.png")
    else:
        print(f"\n❌ 火焰检测失败! 占比 {ratio:.2%} < {AREA_THRESHOLD:.1%}")
        if final_area < MIN_CONTOUR:
            print(f"   原因: 总火焰面积 {final_area}px < 最小连通域 {MIN_CONTOUR}px")
        else:
            print(f"   原因: 占比不足（可能需要进一步降低阈值或调整 HSV 范围）")

    # 保存合并掩码
    cv2.imwrite("debug_fire_combined.png", combined)
    cv2.imwrite("debug_fire_clean.png", clean_mask)
    print("\n中间结果已保存:")
    for name, _, _ in HSV_RANGES:
        print(f"  debug_fire_{name}.png")
    print("  debug_fire_combined.png (三通道合并)")
    print("  debug_fire_clean.png (形态滤波+连通域后)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fire_debug.py <火焰图片路径>")
        sys.exit(1)
    debug_fire(sys.argv[1])
