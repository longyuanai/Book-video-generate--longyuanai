"""
出海八字竖屏短视频渲染器（9:16，适配 TikTok / YouTube Shorts / Reels）。

特性：
- 无显示器环境（服务器/CI）自动使用 SDL dummy 驱动渲染；
- 离线逐帧渲染：时长由字幕/音频推算，渲染速度不受视频时长限制；
- 逐词高亮（卡拉OK式）字幕：读取 TTS 词级时间戳 *.words.json，
  无词级数据时自动降级为整句字幕；
- 预渲染缓存：四柱板/字幕行只渲染一次，逐帧仅做贴图，批量出片更快；
- 片头动画：标题淡入 + 四柱逐列滑入；
- 自动导出发布用缩略图 thumbnail.png；
- 优先使用玄学风格素材目录 backgrounds_bazi / bgm_bazi（可用
  tools/generate_assets.py 生成），缺失时回退到书籍模式素材。
"""

import json
import os
import random
import re
import subprocess
import sys

# 无显示器环境下自动切换 dummy 驱动（必须在 import pygame 前设置）
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from datetime import date as date_type, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pygame

from app import Background, Subtitle, get_screen_size
from bazi.calculator import (BRANCH_ELEMENT, BRANCHES, BaziChart, ELEMENT_CN)
from bazi.locales import ANIMAL_NAMES, ELEMENT_NAMES
from bazi.script_writer import format_date, zodiac_branch_index
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
FUTURE = (140, 140, 150)  # 卡拉OK未读词颜色


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


def _pick_asset_dir(resource_dir: Path, preferred: str, fallback: str) -> Path:
    """优先使用八字专用素材目录，为空则回退书籍模式素材"""
    p = resource_dir / preferred
    if p.is_dir() and any(p.iterdir()):
        return p
    return resource_dir / fallback


class WrappedSubtitle(Subtitle):
    """整句字幕（降级方案）：按屏幕宽度自动换行 + 阴影描边 + 行级缓存"""

    def __init__(self, *args, max_width_ratio: float = 0.88, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_width_ratio = max_width_ratio
        self._cache: Dict[str, List[Tuple[pygame.Surface, pygame.Surface]]] = {}

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

    def _render_lines(self, text: str) -> List[Tuple[pygame.Surface, pygame.Surface]]:
        if text not in self._cache:
            self._cache[text] = [
                (self.font.render(line, True, self.color),
                 self.font.render(line, True, (0, 0, 0)))
                for line in self._wrap(text)]
        return self._cache[text]

    def update(self, screen: pygame.Surface, p: int):
        current_time_ms = (p / self.fps) * 1000
        current_text = self._get_current_subtitle(current_time_ms)
        if not current_text:
            return
        rendered = self._render_lines(current_text)
        if not rendered:
            return
        line_spacing = 8
        total_height = sum(s.get_height() for s, _ in rendered) + line_spacing * (len(rendered) - 1)
        y = self.screen_h - int(self.screen_h * 0.12) - total_height
        for surface, shadow in rendered:
            x = (self.screen_w - surface.get_width()) // 2
            screen.blit(shadow, (x + 2, y + 2))
            screen.blit(surface, (x, y))
            y += surface.get_height() + line_spacing


class KaraokeSubtitle:
    """
    逐词高亮字幕：已读词白色、当前词金色、未读词暗灰。

    数据来自 TTS 词级时间戳（*.words.json），按屏幕宽度分行；
    每个 (行, 词进度) 状态只渲染一次并缓存。
    """

    def __init__(self, font_path: Path, words_path: Path, screen_w: int, screen_h: int,
                 fps: int, font_size: int, max_width_ratio: float = 0.88):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.fps = fps
        self.font = pygame.font.Font(str(font_path), font_size)
        self.space_w = self.font.size(" ")[0]
        words = json.loads(words_path.read_text(encoding="utf-8"))
        self.lines = self._build_lines(words, int(screen_w * max_width_ratio))
        self._cache: Dict[Tuple[int, int], Tuple[pygame.Surface, pygame.Surface]] = {}

    def _build_lines(self, words: List[dict], max_width: int) -> List[dict]:
        """把词序列贪心分行；句末标点处强制断行，行首起止时间取词边界"""
        lines = []
        current: List[dict] = []
        width = 0
        for w in words:
            w_width = self.font.size(w["text"])[0]
            candidate = width + (self.space_w if current else 0) + w_width
            if current and candidate > max_width:
                lines.append(current)
                current, width = [w], w_width
            else:
                current.append(w)
                width = candidate
            if w["text"] and w["text"][-1] in ".!?…":
                lines.append(current)
                current, width = [], 0
        if current:
            lines.append(current)

        result = []
        for i, ws in enumerate(lines):
            result.append({"words": ws, "start": ws[0]["start"], "end": ws[-1]["end"]})
        # 行显示到下一行开始，最后一行多留 800ms
        for i, line in enumerate(result):
            line["until"] = result[i + 1]["start"] if i + 1 < len(result) else line["end"] + 800
        return result

    def _find_line(self, t_ms: float) -> Optional[int]:
        for i, line in enumerate(self.lines):
            if line["start"] <= t_ms < line["until"]:
                return i
        return None

    def _render_line(self, line_idx: int, word_idx: int) -> Tuple[pygame.Surface, pygame.Surface]:
        key = (line_idx, word_idx)
        if key not in self._cache:
            words = self.lines[line_idx]["words"]
            surfaces = []
            for i, w in enumerate(words):
                color = WHITE if i < word_idx else (GOLD if i == word_idx else FUTURE)
                surfaces.append(self.font.render(w["text"], True, color))
            total_w = sum(s.get_width() for s in surfaces) + self.space_w * (len(surfaces) - 1)
            h = max(s.get_height() for s in surfaces)
            line_surf = pygame.Surface((total_w, h), pygame.SRCALPHA)
            shadow_surf = pygame.Surface((total_w, h), pygame.SRCALPHA)
            x = 0
            for i, (w, s) in enumerate(zip(words, surfaces)):
                shadow = self.font.render(w["text"], True, (0, 0, 0))
                shadow_surf.blit(shadow, (x, 0))
                line_surf.blit(s, (x, 0))
                x += s.get_width() + self.space_w
            self._cache[key] = (line_surf, shadow_surf)
        return self._cache[key]

    def update(self, screen: pygame.Surface, p: int):
        t_ms = (p / self.fps) * 1000
        line_idx = self._find_line(t_ms)
        if line_idx is None:
            return
        line = self.lines[line_idx]
        word_idx = sum(1 for w in line["words"] if w["start"] <= t_ms) - 1
        word_idx = max(word_idx, 0)
        line_surf, shadow_surf = self._render_line(line_idx, word_idx)
        x = (self.screen_w - line_surf.get_width()) // 2
        y = self.screen_h - int(self.screen_h * 0.14) - line_surf.get_height()
        screen.blit(shadow_surf, (x + 2, y + 2))
        screen.blit(line_surf, (x, y))


class PillarBoard:
    """
    四柱展示板：YEAR/MONTH/DAY/HOUR 四列，汉字 + 拼音 + 五行。

    每列预渲染为独立 Surface（只渲染一次），片头做逐列滑入动画，
    之后逐帧仅贴图，渲染开销极小。
    """

    STAGGER = 0.22   # 每列入场间隔（秒）
    SLIDE = 0.45     # 单列入场时长（秒）

    def __init__(self, chart: BaziChart, font_path: Path, screen_w: int, screen_h: int):
        self.chart = chart
        self.screen_w = screen_w
        self.screen_h = screen_h
        scale = screen_h / 1920
        self.scale = scale
        self.label_font = pygame.font.Font(str(font_path), max(int(34 * scale), 12))
        self.hanzi_font = pygame.font.Font(str(font_path), max(int(110 * scale), 24))
        self.small_font = pygame.font.Font(str(font_path), max(int(30 * scale), 10))
        self.title_font = pygame.font.Font(str(font_path), max(int(64 * scale), 18))
        self.subtitle_font = pygame.font.Font(str(font_path), max(int(36 * scale), 12))

        self.header = self._render_header()
        self.columns = [self._render_column(name, p)
                        for name, p in chart.pillars.items()]
        self.footer = self._render_footer()

    def _render_header(self) -> pygame.Surface:
        title = self.title_font.render("YOUR BAZI CHART", True, GOLD)
        date_line = self.subtitle_font.render(
            self.chart.birth_time.strftime("%B %d, %Y · %H:%M"), True, DIM)
        gap = int(8 * self.scale)
        surf = pygame.Surface(
            (self.screen_w, title.get_height() + gap + date_line.get_height()),
            pygame.SRCALPHA)
        surf.blit(title, ((self.screen_w - title.get_width()) // 2, 0))
        surf.blit(date_line, ((self.screen_w - date_line.get_width()) // 2,
                              title.get_height() + gap))
        return surf

    def _render_column(self, name: str, pillar) -> pygame.Surface:
        col_w = self.screen_w // 4
        parts = []
        parts.append((self.label_font.render(name.upper(), True, DIM), 10))
        stem_color = ELEMENT_COLOR[pillar.stem_element]
        branch_color = ELEMENT_COLOR[pillar.branch_element]
        parts.append((self.hanzi_font.render(pillar.hanzi[0], True, stem_color), 0))
        parts.append((self.hanzi_font.render(pillar.hanzi[1], True, branch_color), 8))
        parts.append((self.small_font.render(pillar.pinyin, True, WHITE), 0))
        parts.append((self.small_font.render(
            f"{ELEMENT_CN[pillar.stem_element]} {pillar.stem_element}", True, stem_color), 0))
        total_h = sum(s.get_height() + int(g * self.scale) for s, g in parts)
        surf = pygame.Surface((col_w, total_h), pygame.SRCALPHA)
        y = 0
        for s, gap in parts:
            surf.blit(s, ((col_w - s.get_width()) // 2, y))
            y += s.get_height() + int(gap * self.scale)
        return surf

    def _render_footer(self) -> pygame.Surface:
        dm = self.subtitle_font.render(
            f"Day Master: {self.chart.day_master_english}", True, GOLD)
        surf = pygame.Surface((self.screen_w, dm.get_height()), pygame.SRCALPHA)
        surf.blit(dm, ((self.screen_w - dm.get_width()) // 2, 0))
        return surf

    @staticmethod
    def _ease(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return 1 - (1 - t) ** 3  # ease-out cubic

    def update(self, screen: pygame.Surface, p: int, fps: int = 30):
        t = p / fps
        # 标题淡入
        header_alpha = int(255 * self._ease(t / 0.5))
        self.header.set_alpha(header_alpha)
        screen.blit(self.header, (0, int(self.screen_h * 0.08)))

        # 四柱逐列从下方浮入（避免入场过程压到标题）
        col_w = self.screen_w // 4
        top = int(self.screen_h * 0.17)
        slide_px = int(70 * self.scale)
        for i, col in enumerate(self.columns):
            progress = self._ease((t - 0.35 - i * self.STAGGER) / self.SLIDE)
            if progress <= 0:
                continue
            col.set_alpha(int(255 * progress))
            offset = int((1 - progress) * slide_px)
            screen.blit(col, (col_w * i, top + offset))

        # 日主行最后淡入
        footer_alpha = int(255 * self._ease((t - 0.35 - 4 * self.STAGGER) / 0.5))
        if footer_alpha > 0:
            self.footer.set_alpha(footer_alpha)
            screen.blit(self.footer, (0, int(self.screen_h * 0.42)))


class ZodiacBoard:
    """生肖每日运势展示板：大字地支 + 生肖名 + 日期（系列内容用）"""

    HEADINGS = {"en": "DAILY FORTUNE", "es": "HORÓSCOPO DEL DÍA", "pt": "HORÓSCOPO DO DIA"}

    def __init__(self, animal: str, day: date_type, lang: str,
                 font_path: Path, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        scale = screen_h / 1920
        branch = zodiac_branch_index(animal)
        element = BRANCH_ELEMENT[branch]
        color = ELEMENT_COLOR[element]

        title_font = pygame.font.Font(str(font_path), max(int(56 * scale), 16))
        hanzi_font = pygame.font.Font(str(font_path), max(int(230 * scale), 40))
        name_font = pygame.font.Font(str(font_path), max(int(72 * scale), 20))
        small_font = pygame.font.Font(str(font_path), max(int(36 * scale), 12))

        heading = title_font.render(self.HEADINGS.get(lang, self.HEADINGS["en"]), True, GOLD)
        hanzi = hanzi_font.render(BRANCHES[branch], True, color)
        name = name_font.render(ANIMAL_NAMES[lang][animal].upper(), True, WHITE)
        date_line = small_font.render(
            format_date(datetime(day.year, day.month, day.day), lang), True, DIM)
        element_line = small_font.render(
            f"{ELEMENT_CN[element]} · {ELEMENT_NAMES[lang][element]}", True, color)

        parts = [(heading, 26), (hanzi, 6), (name, 10), (element_line, 8), (date_line, 0)]
        total_h = sum(s.get_height() + int(g * scale) for s, g in parts)
        self.board = pygame.Surface((screen_w, total_h), pygame.SRCALPHA)
        y = 0
        for s, gap in parts:
            self.board.blit(s, ((screen_w - s.get_width()) // 2, y))
            y += s.get_height() + int(gap * scale)

    def update(self, screen: pygame.Surface, p: int, fps: int = 30):
        alpha = min(255, int(255 * (p / fps) / 0.8))
        self.board.set_alpha(alpha)
        screen.blit(self.board, (0, int(self.screen_h * 0.09)))


def _render_movie(board_factory, resource_dir: Path, out_dir: Path, font_path: Path,
                  zoom: int, fps: int) -> Optional[Path]:
    """通用渲染流程：背景 + 展示板 + 字幕 -> video.mp4 + thumbnail.png -> 合成"""
    audio_path = next(out_dir.glob("*.mp3"), None)
    if not audio_path:
        raise FileNotFoundError(f"未找到音频文件在 {out_dir} 中，请先生成 TTS 音频")
    subtitle_path = next(out_dir.glob("*.srt"), None)
    words_path = next(out_dir.glob("*.words.json"), None)

    duration = _srt_duration_seconds(subtitle_path) or _ffprobe_duration_seconds(audio_path)
    if not duration:
        raise RuntimeError("无法确定视频时长：SRT 缺失且 ffprobe 不可用")

    bg_dir = _pick_asset_dir(resource_dir, "backgrounds_bazi", "backgrounds")
    bgm_dir = _pick_asset_dir(resource_dir, "bgm_bazi", "bgm")
    bgm_files = list(bgm_dir.glob("*.mp3"))
    if not bgm_files:
        raise FileNotFoundError(f"未找到背景音乐在 {bgm_dir} 中")
    bgm_path = random.choice(bgm_files)

    pygame.init()
    pygame.font.init()
    screen_w, screen_h = get_screen_size("9:16", zoom)
    screen = pygame.display.set_mode((screen_w, screen_h))

    background = Background(
        backgrounds_dir=bg_dir,
        screen_w=screen_w, screen_h=screen_h, fps=fps, switch_time=10,
    )
    overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    overlay.fill((10, 8, 20, 150))  # 暗色蒙层，保证文字可读

    # 展示板此时才实例化（需要 display 初始化后加载字体）
    board = board_factory(font_path, screen_w, screen_h)

    subtitle = None
    subtitle_font_size = max(int(42 * screen_h / 1920), 14)
    if words_path:
        subtitle = KaraokeSubtitle(
            font_path=font_path, words_path=words_path,
            screen_w=screen_w, screen_h=screen_h, fps=fps,
            font_size=subtitle_font_size)
    elif subtitle_path:
        subtitle = WrappedSubtitle(
            font_path=font_path, subtitle_path=subtitle_path,
            screen_w=screen_w, screen_h=screen_h, fps=fps)
        subtitle.font_size = subtitle_font_size
        subtitle.font = pygame.font.Font(str(font_path), subtitle_font_size)

    video_path = out_dir / "video.mp4"
    video_out = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (screen_w, screen_h))

    total_frames = int(duration * fps)
    thumbnail_frame = min(int(2.2 * fps), total_frames - 1)
    print(f"开始渲染: {screen_w}x{screen_h} @{fps}fps, 共 {total_frames} 帧 ({duration:.1f}s), "
          f"字幕: {'逐词高亮' if words_path else ('整句' if subtitle_path else '无')}")

    for p in range(total_frames):
        pygame.event.pump()  # dummy 驱动下也要清事件队列

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

        if p == thumbnail_frame:
            cv2.imwrite(str(out_dir / "thumbnail.png"), frame)

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
        bgm_volume=0.3,
    )
    if success:
        print(f"最终视频已保存到: {final_video_path}")
        return final_video_path
    print("音视频合成失败！已保留无音频视频: ", video_path)
    return None


def make_bazi_movie(chart: BaziChart, resource_dir: Path, out_dir: Path,
                    font_path: Path, zoom: int = 150, fps: int = 30) -> Optional[Path]:
    """渲染个人命盘视频（out_dir 中需已有 TTS 生成的 .mp3，可选 .srt/.words.json）"""
    return _render_movie(
        lambda fp, w, h: PillarBoard(chart, fp, w, h),
        resource_dir, out_dir, font_path, zoom, fps)


def make_zodiac_movie(animal: str, day: date_type, lang: str,
                      resource_dir: Path, out_dir: Path, font_path: Path,
                      zoom: int = 150, fps: int = 30) -> Optional[Path]:
    """渲染生肖每日运势视频（系列内容）"""
    return _render_movie(
        lambda fp, w, h: ZodiacBoard(animal, day, lang, fp, w, h),
        resource_dir, out_dir, font_path, zoom, fps)
