"""
出海八字竖屏短视频渲染器（9:16，适配 TikTok / YouTube Shorts / Reels）。

相比书籍视频的 make_movie 做了两项优化：
1. 支持无显示器环境（服务器/CI）渲染：无 DISPLAY 时自动使用 SDL dummy 驱动；
2. 离线逐帧渲染：不实时播放音频等待，视频时长由字幕/音频时长推算，
   渲染速度只取决于机器性能，不受视频时长限制。
"""

import os
import re
import subprocess
import sys

# 无显示器环境下自动切换 dummy 驱动（必须在 import pygame 前设置）
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
import pygame

from app import Background, Subtitle, get_screen_size
from bazi.calculator import BaziChart, ELEMENT_CN
from video_processor import merge_audio_video

# 五行配色（RGB）
ELEMENT_COLOR = {
    "Wood": (102, 187, 106),
    "Fire": (239, 83, 80),
    "Earth": (255, 183, 77),
    "Metal": (224, 224, 224),
    "Water": (79, 195, 247),
}

GOLD = (230, 195, 120)
WHITE = (245, 245, 245)
DIM = (200, 200, 200)


def _srt_duration_seconds(subtitle_path: Path, tail: float = 1.5) -> Optional[float]:
    """从 SRT 文件推算音频时长（最后一条字幕的结束时间 + 收尾时间）"""
    if not subtitle_path or not subtitle_path.exists():
        return None
    text = subtitle_path.read_text(encoding="utf-8")
    times = re.findall(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", text)
    if not times:
        return None
    h, m, s, ms = map(int, times[-1])
    return h * 3600 + m * 60 + s + ms / 1000 + tail


def _ffprobe_duration_seconds(audio_path: Path) -> Optional[float]:
    """用 ffprobe 读取音频时长（SRT 不可用时的兜底）"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except (FileNotFoundError, ValueError):
        pass
    return None


class WrappedSubtitle(Subtitle):
    """英文字幕：按屏幕宽度自动换行（英文句子普遍比中文长）"""

    def __init__(self, *args, max_width_ratio: float = 0.88, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_width_ratio = max_width_ratio

    def _wrap(self, text: str) -> List[str]:
        max_width = int(self.screen_w * self.max_width_ratio)
        lines = []
        for raw_line in text.split("\n"):
            words = raw_line.split()
            if not words:
                continue
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if self.font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def update(self, screen: pygame.Surface, p: int):
        current_time_ms = (p / self.fps) * 1000
        current_text = self._get_current_subtitle(current_time_ms)
        if not current_text:
            return

        lines = self._wrap(current_text)
        rendered = [(self.font.render(line, True, self.color),
                     self.font.render(line, True, (0, 0, 0))) for line in lines]
        if not rendered:
            return

        line_spacing = 8
        total_height = sum(s.get_height() for s, _ in rendered) + line_spacing * (len(rendered) - 1)
        margin_bottom = int(self.screen_h * 0.12)
        y = self.screen_h - margin_bottom - total_height
        for surface, shadow in rendered:
            x = (self.screen_w - surface.get_width()) // 2
            # 黑色阴影偏移一层，保证浅色背景上也可读
            screen.blit(shadow, (x + 2, y + 2))
            screen.blit(surface, (x, y))
            y += surface.get_height() + line_spacing


class PillarBoard:
    """四柱展示板：YEAR/MONTH/DAY/HOUR 四列，汉字 + 拼音 + 五行"""

    def __init__(self, chart: BaziChart, font_path: Path, screen_w: int, screen_h: int):
        self.chart = chart
        self.screen_w = screen_w
        self.screen_h = screen_h
        scale = screen_h / 1920
        self.label_font = pygame.font.Font(str(font_path), max(int(34 * scale), 12))
        self.hanzi_font = pygame.font.Font(str(font_path), max(int(110 * scale), 24))
        self.small_font = pygame.font.Font(str(font_path), max(int(30 * scale), 10))
        self.title_font = pygame.font.Font(str(font_path), max(int(64 * scale), 18))
        self.subtitle_font = pygame.font.Font(str(font_path), max(int(36 * scale), 12))

    def _blit_center(self, screen, surface, cx, y):
        screen.blit(surface, (cx - surface.get_width() // 2, y))
        return y + surface.get_height()

    def update(self, screen: pygame.Surface, p: int, fade_in_time: float = 1.0, fps: int = 30):
        # 整体淡入
        alpha = min(255, int(255 * p / (fade_in_time * fps)))

        board = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)

        # 标题
        title_y = int(self.screen_h * 0.08)
        title = self.title_font.render("YOUR BAZI CHART", True, GOLD)
        y = self._blit_center(board, title, self.screen_w // 2, title_y)
        date_line = self.subtitle_font.render(
            self.chart.birth_time.strftime("%B %d, %Y · %H:%M"), True, DIM)
        self._blit_center(board, date_line, self.screen_w // 2, y + int(8 * self.screen_h / 1920))

        # 四柱列
        col_w = self.screen_w // 4
        top = int(self.screen_h * 0.17)
        for i, (name, pillar) in enumerate(self.chart.pillars.items()):
            cx = col_w * i + col_w // 2
            y = top
            label = self.label_font.render(name.upper(), True, DIM)
            y = self._blit_center(board, label, cx, y) + int(10 * self.screen_h / 1920)

            stem_color = ELEMENT_COLOR[pillar.stem_element]
            branch_color = ELEMENT_COLOR[pillar.branch_element]
            stem = self.hanzi_font.render(pillar.hanzi[0], True, stem_color)
            y = self._blit_center(board, stem, cx, y)
            branch = self.hanzi_font.render(pillar.hanzi[1], True, branch_color)
            y = self._blit_center(board, branch, cx, y) + int(8 * self.screen_h / 1920)

            pinyin = self.small_font.render(pillar.pinyin, True, WHITE)
            y = self._blit_center(board, pinyin, cx, y)
            element = self.small_font.render(
                f"{ELEMENT_CN[pillar.stem_element]} {pillar.stem_element}", True, stem_color)
            self._blit_center(board, element, cx, y)

        # 日主一行
        dm_y = int(self.screen_h * 0.40)
        dm = self.subtitle_font.render(
            f"Day Master: {self.chart.day_master_english}", True, GOLD)
        self._blit_center(board, dm, self.screen_w // 2, dm_y)

        board.set_alpha(alpha)
        screen.blit(board, (0, 0))


def make_bazi_movie(
    chart: BaziChart,
    resource_dir: Path,
    out_dir: Path,
    font_path: Path,
    zoom: int = 150,
    fps: int = 30,
) -> Optional[Path]:
    """
    渲染八字竖屏视频并合成音频。

    out_dir 中需要已有 TTS 生成的 .mp3（可选 .srt 字幕）。
    zoom: 缩放比例，100=1080x1920 原尺寸，数值越大分辨率越低、渲染越快。
    """
    audio_path = next(out_dir.glob("*.mp3"), None)
    if not audio_path:
        raise FileNotFoundError(f"未找到音频文件在 {out_dir} 中，请先生成 TTS 音频")
    subtitle_path = next(out_dir.glob("*.srt"), None)

    duration = _srt_duration_seconds(subtitle_path) or _ffprobe_duration_seconds(audio_path)
    if not duration:
        raise RuntimeError("无法确定视频时长：SRT 缺失且 ffprobe 不可用")

    bgm_files = list((resource_dir / "bgm").glob("*.mp3"))
    if not bgm_files:
        raise FileNotFoundError(f"未找到背景音乐在 {resource_dir / 'bgm'} 中")
    import random
    bgm_path = random.choice(bgm_files)

    pygame.init()
    pygame.font.init()
    screen_w, screen_h = get_screen_size("9:16", zoom)
    screen = pygame.display.set_mode((screen_w, screen_h))

    background = Background(
        backgrounds_dir=resource_dir / "backgrounds",
        screen_w=screen_w, screen_h=screen_h, fps=fps, switch_time=10,
    )
    overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    overlay.fill((10, 8, 20, 165))  # 暗色蒙层，保证文字可读

    board = PillarBoard(chart, font_path, screen_w, screen_h)

    subtitle = None
    if subtitle_path:
        subtitle = WrappedSubtitle(
            font_path=font_path, subtitle_path=subtitle_path,
            screen_w=screen_w, screen_h=screen_h, fps=fps,
        )
        subtitle.font_size = max(int(40 * screen_h / 1920), 14)
        subtitle.font = pygame.font.Font(str(font_path), subtitle.font_size)

    video_path = out_dir / "video.mp4"
    video_out = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (screen_w, screen_h))

    total_frames = int(duration * fps)
    print(f"开始渲染: {screen_w}x{screen_h} @{fps}fps, 共 {total_frames} 帧 ({duration:.1f}s)")

    for p in range(total_frames):
        # dummy 驱动下也要清事件队列，防止溢出
        pygame.event.pump()

        screen.fill((10, 8, 20))
        background.update(screen, p)
        screen.blit(overlay, (0, 0))
        board.update(screen, p, fps=fps)
        if subtitle:
            subtitle.update(screen, p)

        pygame.display.flip()
        frame = pygame.surfarray.array3d(screen)
        frame = np.transpose(frame, (1, 0, 2))
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        video_out.write(frame)

        if (p + 1) % (fps * 10) == 0:
            print(f"  已渲染 {p + 1}/{total_frames} 帧")

    video_out.release()
    pygame.quit()

    print("开始合成音视频...")
    final_video_path = out_dir / "final_video.mp4"
    success = merge_audio_video(
        video_path=video_path,
        audio_path=audio_path,
        bgm_path=bgm_path,
        effect_path=None,
        output_path=final_video_path,
        bgm_volume=0.35,
    )
    if success:
        print(f"最终视频已保存到: {final_video_path}")
        return final_video_path
    print("音视频合成失败！已保留无音频视频: ", video_path)
    return None
