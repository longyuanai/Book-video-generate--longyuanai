"""
生成品牌头像「Dragon Abyss / 龙渊」（神秘学风格，1080x1080 圆形安全区）。

程序化绘制：深色星云底 + 金色八卦罗盘环 + 中央发光「龙」字 + 星光。
默认输出品牌主视觉（龙字 + 三种配色），另附生肖/太极候选。
输出到 resource/avatars/，挑一个用即可。
"""

import math
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SIZE = 1080
rng = np.random.default_rng(20)

GOLD = (120, 190, 235)      # BGR 金色
GOLD_DIM = (90, 150, 195)
WHITE = (245, 245, 248)


def radial_background(top, bottom):
    """径向渐变底（中心亮四周暗）"""
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    d = np.sqrt(((x - SIZE / 2)) ** 2 + ((y - SIZE / 2)) ** 2) / (SIZE / 2)
    d = np.clip(d, 0, 1)[:, :, None]
    top = np.array(top, np.float32)[None, None, :]
    bottom = np.array(bottom, np.float32)[None, None, :]
    return top * (1 - d) + bottom * d


def add_nebula(img, tint, strength=0.5):
    noise = rng.random((16, 16)).astype(np.float32)
    noise = cv2.resize(noise, (SIZE, SIZE), interpolation=cv2.INTER_CUBIC)
    noise = cv2.GaussianBlur(noise, (0, 0), 60)
    noise = (noise - noise.min()) / (np.ptp(noise) + 1e-6)
    return img + noise[:, :, None] * np.array(tint, np.float32)[None, None, :] * strength


def add_stars(img, n=90):
    for _ in range(n):
        x, y = int(rng.integers(0, SIZE)), int(rng.integers(0, SIZE))
        b = rng.uniform(0.3, 1.0)
        r = 1 if rng.random() > 0.15 else 2
        cv2.circle(img, (x, y), r, tuple(c * b for c in WHITE), -1)
    return img


def draw_ring(img, radius, color, thickness, dashes=None):
    center = (SIZE // 2, SIZE // 2)
    if dashes:
        for i in range(dashes):
            a0 = 2 * math.pi * i / dashes
            a1 = a0 + math.pi / dashes * 0.9
            cv2.ellipse(img, center, (radius, radius),
                        0, math.degrees(a0), math.degrees(a1), color, thickness, cv2.LINE_AA)
    else:
        cv2.circle(img, center, radius, color, thickness, cv2.LINE_AA)


def draw_trigrams(img, radius):
    """八卦：八个方位画三爻符号（阴爻断、阳爻连）"""
    center = SIZE / 2
    # 先天八卦阴阳爻（1=阳连, 0=阴断），从上方顺时针
    trigrams = [
        [1, 1, 1], [1, 1, 0], [1, 0, 1], [1, 0, 0],
        [0, 0, 0], [0, 0, 1], [0, 1, 0], [0, 1, 1],
    ]
    bar_w, bar_h, gap = int(SIZE * 0.052), int(SIZE * 0.011), int(SIZE * 0.007)
    for i, tri in enumerate(trigrams):
        ang = -math.pi / 2 + 2 * math.pi * i / 8
        cx = center + radius * math.cos(ang)
        cy = center + radius * math.sin(ang)
        for j, yao in enumerate(tri):
            yy = int(cy + (j - 1) * (bar_h + gap) * 2.2)
            if yao:  # 阳爻：整条
                cv2.rectangle(img, (int(cx - bar_w / 2), yy - bar_h),
                              (int(cx + bar_w / 2), yy + bar_h), GOLD, -1, cv2.LINE_AA)
            else:    # 阴爻：断开两段
                seg = int(bar_w * 0.4)
                cv2.rectangle(img, (int(cx - bar_w / 2), yy - bar_h),
                              (int(cx - bar_w / 2 + seg), yy + bar_h), GOLD, -1, cv2.LINE_AA)
                cv2.rectangle(img, (int(cx + bar_w / 2 - seg), yy - bar_h),
                              (int(cx + bar_w / 2), yy + bar_h), GOLD, -1, cv2.LINE_AA)


def draw_center_glyph(img, text, font_scale, color=GOLD, thickness=6):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    org = ((SIZE - tw) // 2, (SIZE + th) // 2)
    # 光晕
    glow = np.zeros_like(img)
    cv2.putText(glow, text, org, font, font_scale, color, thickness + 10, cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), 12)
    img += glow * 0.6
    cv2.putText(img, text, org, font, font_scale, color, thickness, cv2.LINE_AA)


def vignette(img, strength=0.6):
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    d = np.sqrt((x - SIZE / 2) ** 2 + (y - SIZE / 2) ** 2) / (SIZE / 2)
    mask = 1 - strength * np.clip(d - 0.5, 0, 1) ** 1.5
    return img * mask[:, :, None]


def compose(variant: str) -> np.ndarray:
    if variant == "purple":
        img = radial_background((60, 20, 40), (18, 8, 14))
        img = add_nebula(img, (150, 60, 110), 0.55)
    elif variant == "teal":
        img = radial_background((70, 45, 15), (14, 10, 6))
        img = add_nebula(img, (140, 90, 25), 0.5)
    else:  # ink
        img = radial_background((40, 36, 32), (10, 9, 12))
        img = add_nebula(img, (60, 60, 70), 0.4)

    img = add_stars(img)
    draw_ring(img, int(SIZE * 0.46), GOLD_DIM, 3)
    draw_ring(img, int(SIZE * 0.42), GOLD, 2, dashes=48)
    draw_trigrams(img, int(SIZE * 0.36))
    draw_ring(img, int(SIZE * 0.25), GOLD_DIM, 2)
    return img


def finish_and_save(img, path):
    img = vignette(img)
    out = np.clip(img, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), out)
    print(f"  生成 {path.name}")


def main():
    out_dir = ROOT / "resource" / "avatars"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("生成头像候选...")

    # 品牌主视觉：中央「龙」字（对应 Dragon Abyss / 龙渊），三种配色
    for variant in ("purple", "teal", "ink"):
        img = compose(variant)
        img = draw_cjk_center(img, "龙", 12.0)
        finish_and_save(img, out_dir / f"brand_dragon_{variant}.png")

    # 备选：太极 / 生肖字 / 繁体龙，供对比挑选
    alternatives = {
        "taiji": ("☯", 9.0),
        "horse": ("午", 11.0),      # 2026 马年应景
        "dragon_trad": ("龍", 11.0),  # 繁体龙，更古意
    }
    for variant in ("purple",):
        for gname, (glyph, scale) in alternatives.items():
            img = compose(variant)
            if gname == "taiji":
                draw_taiji(img, int(SIZE * 0.16))
            else:
                img = draw_cjk_center(img, glyph, scale)
            finish_and_save(img, out_dir / f"alt_{gname}_{variant}.png")


def draw_taiji(img, r):
    """绘制阴阳鱼太极符号（金色描边）"""
    cx = cy = SIZE // 2
    cv2.circle(img, (cx, cy), r, GOLD, 3, cv2.LINE_AA)
    # 上白下暗的 S 形分割用两个半圆近似
    cv2.ellipse(img, (cx, cy - r // 2), (r // 2, r // 2), 0, 0, 360, GOLD, 2, cv2.LINE_AA)
    cv2.ellipse(img, (cx, cy + r // 2), (r // 2, r // 2), 0, 0, 360, GOLD, 2, cv2.LINE_AA)
    cv2.circle(img, (cx, cy - r // 2), max(3, r // 12), GOLD, -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy + r // 2), max(3, r // 12), GOLD, -1, cv2.LINE_AA)


def draw_cjk_center(img, text, scale):
    """用 PIL + 项目字体渲染中文/英文并居中叠加（带金色光晕）"""
    from PIL import Image, ImageDraw, ImageFont
    font_path = ROOT / "resource" / "fonts" / "msyh.ttc"
    size = int(SIZE * 0.028 * scale)
    font = ImageFont.truetype(str(font_path), size)
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((SIZE - tw) // 2 - bbox[0], (SIZE - th) // 2 - bbox[1])
    d.text(pos, text, font=font, fill=(235, 190, 120, 255))  # RGBA 金
    layer_np = np.array(layer).astype(np.float32)
    alpha = layer_np[:, :, 3:4] / 255
    rgb = layer_np[:, :, 2::-1]  # RGB->BGR
    glow = cv2.GaussianBlur(rgb * alpha, (0, 0), 10) * 0.7
    return img * (1 - alpha) + rgb * alpha + glow


if __name__ == "__main__":
    main()
    print("头像生成完成 ✓  在 resource/avatars/ 中挑选")
