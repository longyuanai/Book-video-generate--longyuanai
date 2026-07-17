"""
出海八字短视频生成入口。

输入出生日期时间 -> 排四柱 -> 生成英文口播文案 -> 英文 TTS 配音+字幕
-> 渲染 9:16 竖屏视频 -> FFmpeg 合成，输出可直接发布到
TikTok / YouTube Shorts / Instagram Reels 的成片。

用法:
    python main_bazi.py                                    # 交互式输入
    python main_bazi.py --date 1995-08-17 --time 14:30     # 命令行参数
    python main_bazi.py --date 1995-08-17 --offline        # 不调用 LLM，用内置模板
    python main_bazi.py --date 1995-08-17 --voice Andrew   # 指定英文语音
"""

import argparse
from datetime import datetime
from pathlib import Path

from bazi import calculate_bazi, generate_bazi_script
from tts_generator import createAudio, en_voice_dict

DEFAULT_VOICE = "Ava（美国）-女"


def parse_args():
    parser = argparse.ArgumentParser(description="BaZi overseas short-video generator")
    parser.add_argument("--date", help="出生日期，格式 YYYY-MM-DD")
    parser.add_argument("--time", default="12:00", help="出生时间，格式 HH:MM（默认 12:00）")
    parser.add_argument("--voice", default=None,
                        help=f"英文语音名称关键词（可选：{', '.join(en_voice_dict)}）")
    parser.add_argument("--offline", action="store_true", help="不调用 LLM，使用内置英文模板")
    parser.add_argument("--zoom", type=int, default=150,
                        help="渲染缩放：100=1080x1920 原尺寸，越大越快、分辨率越低（默认 150）")
    parser.add_argument("--script-only", action="store_true", help="只生成文案，不渲染视频")
    return parser.parse_args()


def pick_voice(keyword: str) -> str:
    """按关键词模糊匹配英文语音，未命中则用默认语音"""
    if keyword:
        for name, voice_id in en_voice_dict.items():
            if keyword.lower() in name.lower() or keyword.lower() in voice_id.lower():
                return voice_id
        print(f"未找到语音 '{keyword}'，使用默认语音 {DEFAULT_VOICE}")
    return en_voice_dict[DEFAULT_VOICE]


def main():
    args = parse_args()

    date_str = args.date or input("请输入出生日期 (YYYY-MM-DD): ").strip()
    time_str = args.time if args.date else (
        input("请输入出生时间 (HH:MM，直接回车默认 12:00): ").strip() or "12:00")

    birth = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    # 1. 排盘
    chart = calculate_bazi(birth)
    print(chart.summary_text())

    # 2. 生成英文文案
    print("\n正在生成英文文案..." + ("（离线模板模式）" if args.offline else ""))
    script = generate_bazi_script(chart, use_llm=not args.offline)
    print("\n---- 文案 ----\n" + script + "\n--------------\n")

    root_dir = Path(__file__).parent
    out_dir = root_dir / "appdata" / f"bazi_{birth:%Y%m%d_%H%M}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.txt").write_text(script, encoding="utf-8")

    if args.script_only:
        print(f"文案已保存到: {out_dir / 'script.txt'}")
        return

    # 3. 英文 TTS 配音 + SRT 字幕
    print("正在生成英文语音...")
    voice = pick_voice(args.voice)
    audio_path = out_dir / "narration.mp3"
    result = createAudio(script, audio_path, voice)
    if result != True:
        print("TTS 生成失败（需要联网访问微软 Edge-TTS 服务），流程中止。")
        print(f"文案已保存到 {out_dir / 'script.txt'}，可稍后重试。")
        return

    # 4. 渲染竖屏视频并合成
    from bazi_video import make_bazi_movie
    resource_dir = root_dir / "resource"
    make_bazi_movie(
        chart=chart,
        resource_dir=resource_dir,
        out_dir=out_dir,
        font_path=resource_dir / "fonts" / "msyh.ttc",
        zoom=args.zoom,
    )


if __name__ == "__main__":
    main()
