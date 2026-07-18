"""
出海八字短视频生成入口。

三种玩法：
1. 个人命盘（默认）：出生日期 -> 排盘 -> 多语言文案 -> TTS -> 竖屏成片 + 发布素材
2. 批量模式（--batch）：CSV 每行一条命盘，一次跑一批（评论区收集的生日直接喂进来）
3. 生肖系列（--series zodiac）：一次生成 12 生肖当日运势，日更系列内容

用法示例:
    python main_bazi.py                                       # 交互式
    python main_bazi.py --date 1995-08-17 --time 14:30 --gender female
    python main_bazi.py --date 1995-08-17 --tz -5             # 纽约出生（冬令时）
    python main_bazi.py --date 1995-08-17 --lang es           # 西班牙语（拉美市场）
    python main_bazi.py --date 1995-08-17 --offline           # 不调 LLM，纯离线
    python main_bazi.py --batch birthdays.csv                 # 批量
    python main_bazi.py --series zodiac --lang pt             # 12 生肖每日运势（葡语）
    python main_bazi.py --date 1995-08-17 --script-only       # 只出文案+发布素材

批量 CSV 格式（表头必需，date 必填其余可省）:
    date,time,tz,gender,lang,voice
    1995-08-17,14:30,8,female,en,Ava
    2001-03-02,,-5,male,es,
"""

import argparse
import csv
from datetime import date as date_type, datetime
from pathlib import Path

from bazi import calculate_bazi, generate_bazi_script
from bazi.calculator import BRANCH_ANIMAL
from bazi.locales import SUPPORTED_LANGS, check_lang
from bazi.publish_kit import (build_chart_publish_kit, build_zodiac_publish_kit,
                              save_publish_kit)
from bazi.script_writer import generate_zodiac_script
from tts_generator import createAudio, lang_voice_dicts

ROOT_DIR = Path(__file__).parent
RESOURCE_DIR = ROOT_DIR / "resource"
FONT_PATH = RESOURCE_DIR / "fonts" / "msyh.ttc"

DEFAULT_VOICES = {"en": "Ava（美国）-女", "es": "Dalia（墨西哥）-女", "pt": "Francisca（巴西）-女"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="BaZi overseas short-video generator",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", help="出生日期 YYYY-MM-DD")
    parser.add_argument("--time", default="12:00", help="出生时间 HH:MM（默认 12:00）")
    parser.add_argument("--tz", type=float, default=8.0,
                        help="出生地时区（相对 UTC 小时数，默认 +8 中国；纽约冬令时 -5）")
    parser.add_argument("--gender", choices=["male", "female"], help="性别（提供后计算大运）")
    parser.add_argument("--lang", default="en", choices=SUPPORTED_LANGS,
                        help="文案/配音语言（默认 en；es=西语拉美，pt=葡语巴西）")
    parser.add_argument("--voice", help="语音名称关键词（按 --lang 对应语音表模糊匹配）")
    parser.add_argument("--offline", action="store_true", help="不调用 LLM，使用内置母语模板")
    parser.add_argument("--zoom", type=int, default=150,
                        help="渲染缩放：100=1080x1920 原尺寸，越大越快分辨率越低（默认 150）")
    parser.add_argument("--script-only", action="store_true", help="只生成文案+发布素材，不渲染视频")
    parser.add_argument("--batch", help="批量模式：CSV 文件路径（见文件头注释的格式）")
    parser.add_argument("--series", choices=["zodiac"], help="系列模式：zodiac=12 生肖每日运势")
    parser.add_argument("--series-date", help="系列模式的日期 YYYY-MM-DD（默认今天）")
    return parser.parse_args()


def pick_voice(lang: str, keyword: str = None) -> str:
    """按语言选择语音；关键词模糊匹配，未命中用该语言默认语音"""
    voices = lang_voice_dicts[lang]
    if keyword:
        for name, voice_id in voices.items():
            if keyword.lower() in name.lower() or keyword.lower() in voice_id.lower():
                return voice_id
        print(f"未找到语音 '{keyword}'，使用默认语音 {DEFAULT_VOICES[lang]}")
    return voices[DEFAULT_VOICES[lang]]


def _tts_and_render(script: str, out_dir: Path, lang: str, voice_keyword: str,
                    zoom: int, render) -> bool:
    """TTS -> 渲染。render 为接收 out_dir 的回调；返回是否成功出片"""
    print("正在生成语音...")
    voice = pick_voice(lang, voice_keyword)
    audio_path = out_dir / "narration.mp3"
    result = createAudio(script, audio_path, voice)
    if result != True:
        print(f"TTS 生成失败（需要联网访问 Edge-TTS 服务）。文案已保存到 {out_dir}，可稍后重试。")
        return False
    render(out_dir)
    return True


def run_chart(date_str: str, time_str: str, tz: float, gender, lang: str,
              voice_keyword, offline: bool, zoom: int, script_only: bool) -> Path:
    """单条个人命盘流水线，返回输出目录"""
    check_lang(lang)
    birth = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    chart = calculate_bazi(birth, tz_hours=tz, gender=gender)
    print(chart.summary_text())

    print("\n正在生成文案..." + ("（离线模板模式）" if offline else ""))
    script = generate_bazi_script(chart, use_llm=not offline, lang=lang)
    print("\n---- 文案 ----\n" + script + "\n--------------\n")

    out_dir = ROOT_DIR / "appdata" / f"bazi_{birth:%Y%m%d_%H%M}_{lang}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.txt").write_text(script, encoding="utf-8")
    save_publish_kit(build_chart_publish_kit(chart, lang), out_dir)
    print(f"文案与发布素材已保存到: {out_dir}")

    if not script_only:
        from bazi_video import make_bazi_movie
        _tts_and_render(
            script, out_dir, lang, voice_keyword, zoom,
            lambda d: make_bazi_movie(chart, RESOURCE_DIR, d, FONT_PATH, zoom=zoom))
    return out_dir


def run_batch(csv_path: Path, args) -> None:
    """批量模式：逐行跑个人命盘流水线，单条失败不影响其余"""
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    print(f"批量模式：共 {len(rows)} 条")
    done, failed = 0, 0
    for i, row in enumerate(rows, 1):
        date_str = (row.get("date") or "").strip()
        if not date_str:
            print(f"[{i}] 跳过：缺少 date 列")
            failed += 1
            continue
        try:
            print(f"\n===== [{i}/{len(rows)}] {date_str} =====")
            run_chart(
                date_str=date_str,
                time_str=(row.get("time") or "").strip() or "12:00",
                tz=float((row.get("tz") or "").strip() or 8),
                gender=(row.get("gender") or "").strip() or None,
                lang=(row.get("lang") or "").strip() or args.lang,
                voice_keyword=(row.get("voice") or "").strip() or args.voice,
                offline=args.offline,
                zoom=args.zoom,
                script_only=args.script_only,
            )
            done += 1
        except Exception as e:
            print(f"[{i}] 失败: {e}")
            failed += 1
    print(f"\n批量完成：成功 {done} 条，失败 {failed} 条")


def run_zodiac_series(day: date_type, lang: str, args) -> None:
    """生肖系列：12 条当日运势（文案+发布素材，默认渲染视频）"""
    check_lang(lang)
    series_dir = ROOT_DIR / "appdata" / f"zodiac_{day:%Y%m%d}_{lang}"
    print(f"生肖每日运势系列：{day} / {lang}，输出到 {series_dir}")
    for i, animal in enumerate(BRANCH_ANIMAL, 1):
        print(f"\n===== [{i}/12] {animal} =====")
        out_dir = series_dir / animal.lower()
        out_dir.mkdir(parents=True, exist_ok=True)
        script = generate_zodiac_script(animal, day, use_llm=not args.offline, lang=lang)
        print(script)
        (out_dir / "script.txt").write_text(script, encoding="utf-8")
        save_publish_kit(build_zodiac_publish_kit(animal, day, lang), out_dir)
        if not args.script_only:
            from bazi_video import make_zodiac_movie
            _tts_and_render(
                script, out_dir, lang, args.voice, args.zoom,
                lambda d, a=animal: make_zodiac_movie(
                    a, day, lang, RESOURCE_DIR, d, FONT_PATH, zoom=args.zoom))
    print(f"\n系列完成，输出目录: {series_dir}")


def main():
    args = parse_args()

    if args.batch:
        run_batch(Path(args.batch), args)
        return

    if args.series == "zodiac":
        day = (datetime.strptime(args.series_date, "%Y-%m-%d").date()
               if args.series_date else date_type.today())
        run_zodiac_series(day, args.lang, args)
        return

    date_str = args.date or input("请输入出生日期 (YYYY-MM-DD): ").strip()
    time_str = args.time if args.date else (
        input("请输入出生时间 (HH:MM，直接回车默认 12:00): ").strip() or "12:00")
    run_chart(date_str, time_str, args.tz, args.gender, args.lang,
              args.voice, args.offline, args.zoom, args.script_only)


if __name__ == "__main__":
    main()
