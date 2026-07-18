"""
程序化生成出海八字模式的视觉与音频素材（离线，无需下载）。

- resource/backgrounds_bazi/  4 张 1080x1920 神秘学风格竖屏背景（星云/星空/金粉）
- resource/bgm_bazi/          2 段 ambient 冥想背景音乐（约 64 秒，可循环）

用法: python tools/generate_assets.py
"""

import math
import subprocess
import wave
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
SR = 44100

rng = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# 背景图
# ---------------------------------------------------------------------------

def vertical_gradient(top_rgb, bottom_rgb):
    t = np.linspace(0, 1, H)[:, None, None]
    top = np.array(top_rgb, dtype=np.float32)[None, None, :]
    bottom = np.array(bottom_rgb, dtype=np.float32)[None, None, :]
    return (top * (1 - t) + bottom * t) * np.ones((H, W, 3), dtype=np.float32)


def nebula_layer(tint_rgb, scale=8, strength=1.0):
    """多倍频模糊噪声着色成星云"""
    noise = np.zeros((H, W), dtype=np.float32)
    for octave, weight in [(scale, 0.6), (scale * 3, 0.3), (scale * 9, 0.1)]:
        small = rng.random((octave * 16 // 9, octave)).astype(np.float32)
        layer = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)
        noise += weight * layer
    noise = cv2.GaussianBlur(noise, (0, 0), 25)
    noise = np.clip((noise - noise.mean()) / (noise.std() + 1e-6) * 0.35 + 0.35, 0, 1)
    tint = np.array(tint_rgb, dtype=np.float32)[None, None, :]
    return noise[:, :, None] * tint * strength


def star_layer(n_stars=420, big_ratio=0.06):
    img = np.zeros((H, W, 3), dtype=np.float32)
    xs = rng.integers(0, W, n_stars)
    ys = rng.integers(0, H, n_stars)
    brightness = rng.uniform(60, 255, n_stars)
    for x, y, b in zip(xs, ys, brightness):
        if rng.random() < big_ratio:
            cv2.circle(img, (int(x), int(y)), 2, (b, b, b), -1)
        else:
            img[y, x] = (b, b, b)
    img = cv2.GaussianBlur(img, (0, 0), 0.8)
    # 少量亮星加光晕
    for _ in range(14):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        glow = np.zeros((H, W, 3), dtype=np.float32)
        cv2.circle(glow, (x, y), 3, (255, 255, 255), -1)
        img += cv2.GaussianBlur(glow, (0, 0), 6) * 0.9
    return img


def vignette(strength=0.55):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    mask = 1 - strength * np.clip(d - 0.45, 0, 1) ** 1.6
    return mask[:, :, None]


def gold_dust(n=260):
    img = np.zeros((H, W, 3), dtype=np.float32)
    for _ in range(n):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        b = rng.uniform(0.35, 1.0)
        color = (np.array([120, 190, 235], dtype=np.float32) * b)  # BGR 金色
        cv2.circle(img, (x, y), int(rng.integers(1, 3)), color.tolist(), -1)
    return cv2.GaussianBlur(img, (0, 0), 1.2)


def save_bg(path: Path, img: np.ndarray):
    out = np.clip(img, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), out, [cv2.IMWRITE_PNG_COMPRESSION, 8])
    print(f"  生成 {path.name} ({out.shape[1]}x{out.shape[0]})")


def generate_backgrounds(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    print("生成背景图...")

    # 1. 深紫星云（BGR）
    img = vertical_gradient((36, 10, 18), (10, 4, 6))
    img += nebula_layer((120, 40, 90), strength=0.9)       # 紫
    img += nebula_layer((90, 50, 30), scale=5, strength=0.4)  # 蓝
    img += star_layer()
    img *= vignette()
    save_bg(out_dir / "nebula_purple.png", img)

    # 2. 靛青夜空
    img = vertical_gradient((48, 26, 8), (12, 8, 4))
    img += nebula_layer((110, 70, 20), strength=0.7)       # 青
    img += star_layer(500)
    img *= vignette()
    save_bg(out_dir / "night_teal.png", img)

    # 3. 墨色金粉
    img = vertical_gradient((22, 20, 18), (6, 6, 8))
    img += nebula_layer((40, 45, 55), scale=4, strength=0.5)   # 暖灰云雾
    img += gold_dust()
    img += star_layer(120)
    img *= vignette(0.5)
    save_bg(out_dir / "ink_gold.png", img)

    # 4. 午夜蓝极光
    img = vertical_gradient((60, 30, 14), (14, 6, 10))
    img += nebula_layer((130, 90, 30), scale=6, strength=0.8)  # 青绿光带
    img += nebula_layer((80, 30, 70), scale=10, strength=0.35)
    img += star_layer(380)
    img *= vignette()
    save_bg(out_dir / "midnight_aurora.png", img)


# ---------------------------------------------------------------------------
# Ambient BGM
# ---------------------------------------------------------------------------

def _pad_chord(freqs, duration, sr=SR):
    """柔和的正弦叠加和弦，带慢速呼吸式包络"""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    out = np.zeros_like(t)
    for i, f in enumerate(freqs):
        vib = 1 + 0.002 * np.sin(2 * np.pi * 0.13 * t + i)
        partial = (np.sin(2 * np.pi * f * vib * t)
                   + 0.35 * np.sin(2 * np.pi * 2 * f * t + 0.5)
                   + 0.12 * np.sin(2 * np.pi * 3 * f * t + 1.1))
        out += partial / len(freqs)
    breath = 0.75 + 0.25 * np.sin(2 * np.pi * t / duration * 2 - math.pi / 2)
    return out * breath


def _crossfaded_progression(chords, seg_seconds, fade_seconds=4.0):
    sr = SR
    seg_n = int(seg_seconds * sr)
    fade_n = int(fade_seconds * sr)
    total = seg_n * len(chords)
    out = np.zeros(total)
    for i, freqs in enumerate(chords):
        seg = _pad_chord(freqs, seg_seconds + fade_seconds)
        start = i * seg_n
        end = min(start + len(seg), total)
        seg = seg[:end - start]
        env = np.ones(len(seg))
        env[:fade_n] = np.linspace(0, 1, fade_n)
        env[-fade_n:] = np.linspace(1, 0, fade_n)
        out[start:end] += seg * env
    return out


def _air_noise(n, cutoff_smooth=400):
    """低通白噪声做「空气感」铺底"""
    noise = rng.standard_normal(n)
    kernel = np.ones(cutoff_smooth) / cutoff_smooth
    return np.convolve(noise, kernel, mode="same")


def _write_wav(path: Path, data: np.ndarray):
    data = data / (np.abs(data).max() + 1e-9) * 0.72
    pcm = (data * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def generate_bgm(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    print("生成 ambient BGM...")

    tracks = {
        # A 小调 i–VI–III–VII，冥想氛围
        "mystic_pad": [
            [110.0, 164.81, 220.0, 329.63],   # Am
            [87.31, 130.81, 174.61, 261.63],  # F
            [65.41, 130.81, 196.0, 261.63],   # C
            [98.0, 146.83, 196.0, 293.66],    # G
        ],
        # D 小调更暗的进行
        "deep_meditation": [
            [73.42, 110.0, 146.83, 220.0],    # Dm
            [58.27, 87.31, 116.54, 174.61],   # Bb
            [65.41, 98.0, 130.81, 196.0],     # C(low)
            [55.0, 82.41, 110.0, 164.81],     # Am(low)
        ],
    }

    for name, chords in tracks.items():
        audio = _crossfaded_progression(chords, seg_seconds=16.0)
        air = _air_noise(len(audio))
        audio = audio + 0.05 * air / (np.abs(air).max() + 1e-9)
        # 整体淡入淡出，便于循环
        fade = int(3 * SR)
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)

        wav_path = out_dir / f"{name}.wav"
        _write_wav(wav_path, audio)
        mp3_path = out_dir / f"{name}.mp3"
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-b:a", "128k", str(mp3_path)],
            capture_output=True)
        if result.returncode == 0:
            wav_path.unlink()
            print(f"  生成 {mp3_path.name} ({mp3_path.stat().st_size // 1024} KB)")
        else:
            print(f"  ffmpeg 转码失败，保留 {wav_path.name}")


if __name__ == "__main__":
    generate_backgrounds(ROOT / "resource" / "backgrounds_bazi")
    generate_bgm(ROOT / "resource" / "bgm_bazi")
    print("素材生成完成 ✓")
