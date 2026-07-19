"""
出海八字短视频生成入口。

四种玩法：
1. 个人命盘（默认）：出生日期 -> 排盘 -> 多语言文案 -> TTS -> 竖屏成片 + 发布素材
2. 合婚配对（--compat）：两个生日 -> 契合度评分 + 解读视频（互动性最强的形态）
3. 批量模式（--batch）：CSV 每行一条命盘，支持 --jobs 并行渲染
4. 生肖系列（--series zodiac）：一次生成 12 生肖当日运势，支持 --jobs 并行

用法示例:
    python main_bazi.py --date 1995-08-17 --time 14:30 --gender female
    python main_bazi.py --date 1995-08-17 --tz -5 --longitude -74.0   # 纽约+真太阳时
    python main_bazi.py --date 1995-08-17 --lang es --variants 3      # 西语+3版钩子
    python main_bazi.py --compat 1995-08-17,14:30 1997-02-11          # 合婚
    python main_bazi.py --batch birthdays.csv --jobs 4                # 批量并行
    python main_bazi.py --series zodiac --lang pt --jobs 4            # 生肖系列并行

批量 CSV 格式（表头必需，date 必填其余可省）:
    date,time,tz,gender,lang,voice
    1995-08-17,14:30,8,female,en,Ava
    2001-03-02,,-5,male,es,
"""

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date as date_type, datetime
from pathlib import Path

from bazi import calculate_bazi, generate_bazi_script
from bazi.calculator import BRANCH_ANIMAL
from bazi.compatibility import analyze_compatibility, generate_compat_content
from bazi.locales import SUPPORTED_LANGS, check_lang
from bazi.publish_kit import (build_chart_publish_kit, build_compat_publish_kit,
                              build_zodiac_publish_kit, save_publish_kit)
from bazi.script_writer import generate_zodiac_script
from tts_generator import createAudio, lang_voice_dicts

ROOT_DIR = Path(__file__).parent
RESOURCE_DIR = ROOT_DIR / "resource"
FONT_PATH = RESOURCE_DIR / "fonts" / "msyh.ttc"

DEFAULT_VOICES = {"en": "Ava（美国）-女", "es": "Dalia（墨西哥）-女", "pt": "Francisca（巴西）-女"}

VARIANT_HOOK_STYLES = [
    "a bold, surprising claim",
    "a direct question to the viewer",
    "a tiny story or scene (two sentences max)",
    "a myth-busting statement (\"everyone gets this wrong\")",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="BaZi overseas short-video generator",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", help="出生日期 YYYY-MM-DD")
    parser.add_argument("--time", default="12:00", help="出生时间 HH:MM（默认 12:00）")
    parser.add_argument("--tz", type=float, default=8.0,
                        help="出生地时区（相对 UTC 小时数，默认 +8 中国；纽约冬令时 -5）")
    parser.add_argument("--longitude", type=float,
                        help="出生地经度（东正西负，如北京 116.4、纽约 -74.0）。"
                             "提供后按真太阳时校正日柱/时柱")
    parser.add_argument("--gender", choices=["male", "female"], help="性别（提供后计算大运）")
    parser.add_argument("--lang", default="en", choices=SUPPORTED_LANGS,
                        help="文案/配音语言（默认 en；es=西语拉美，pt=葡语巴西）")
    parser.add_argument("--voice", help="语音名称关键词（按 --lang 对应语音表模糊匹配）")
    parser.add_argument("--offline", action="store_true", help="不调用 LLM，使用内置母语模板")
    parser.add_argument("--variants", type=int, default=1,
                        help="生成 N 版不同钩子的文案做 A/B 测试（需 LLM，默认 1）")
    parser.add_argument("--zoom", type=int, default=150,
                        help="渲染缩放：100=1080x1920 原尺寸，越大越快分辨率越低（默认 150）")
    parser.add_argument("--script-only", action="store_true", help="只生成文案+发布素材，不渲染视频")
    parser.add_argument("--compat", nargs=2, metavar="DATE[,HH:MM]",
                        help="合婚模式：两人出生日期（可带时间），如 1995-08-17,14:30 1997-02-11")
    parser.add_argument("--batch", help="批量模式：CSV 文件路径（见文件头注释的格式）")
    parser.add_argument("--series", choices=["zodiac", "year"],
                        help="系列模式：zodiac=12 生肖每日运势，year=12 生肖流年运势")
    parser.add_argument("--series-date", help="zodiac 系列的日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--year", type=int, help="year 系列的目标年份（默认今年）")
    parser.add_argument("--report", action="store_true",
                        help="个人命盘模式额外生成 PDF 命书报告（report.pdf，付费交付物）")
    parser.add_argument("--jobs", type=int, default=1,
                        help="批量/系列模式的并行进程数（默认 1；TTS 并发过高可能被限流，建议 ≤4）")
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


def _parse_birth(spec: str, default_time: str = "12:00") -> datetime:
    """解析 'YYYY-MM-DD' 或 'YYYY-MM-DD,HH:MM'"""
    if "," in spec:
        date_str, time_str = spec.split(",", 1)
    else:
        date_str, time_str = spec, default_time
    return datetime.strptime(f"{date_str.strip()} {time_str.strip()}", "%Y-%m-%d %H:%M")


def _tts_and_render(script: str, out_dir: Path, lang: str, voice_keyword, render) -> bool:
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
              voice_keyword, offline: bool, zoom: int, script_only: bool,
              longitude=None, variants: int = 1, report: bool = False) -> Path:
    """单条个人命盘流水线，返回输出目录"""
    check_lang(lang)
    birth = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    chart = calculate_bazi(birth, tz_hours=tz, gender=gender, longitude=longitude)
    print(chart.summary_text())

    print("\n正在生成文案..." + ("（离线模板模式）" if offline else ""))
    script = generate_bazi_script(chart, use_llm=not offline, lang=lang)
    print("\n---- 文案 ----\n" + script + "\n--------------\n")

    out_dir = ROOT_DIR / "appdata" / f"bazi_{birth:%Y%m%d_%H%M}_{lang}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.txt").write_text(script, encoding="utf-8")

    # A/B 钩子变体（仅 LLM 模式有意义；模板输出是确定性的）
    if variants > 1:
        if offline:
            print("提示：--variants 需要 LLM（--offline 下跳过变体生成）")
        else:
            for i in range(2, variants + 1):
                style = VARIANT_HOOK_STYLES[(i - 2) % len(VARIANT_HOOK_STYLES)]
                v = generate_bazi_script(
                    chart, use_llm=True, lang=lang,
                    extra_instruction=f"Variant #{i}: open with {style}. "
                                      f"Make the hook completely different from a plain "
                                      f"'if you were born on...' opening.")
                (out_dir / f"script_v{i}.txt").write_text(v, encoding="utf-8")
            print(f"已生成 {variants} 版钩子文案（script.txt, script_v2.txt ...）")

    save_publish_kit(build_chart_publish_kit(chart, lang), out_dir)
    print(f"文案与发布素材已保存到: {out_dir}")

    if report:
        from bazi.report import generate_report
        pdf_path = generate_report(chart, out_dir / "report.pdf", FONT_PATH, lang)
        print(f"PDF 命书已生成: {pdf_path}")

    if not script_only:
        from bazi_video import make_bazi_movie
        _tts_and_render(
            script, out_dir, lang, voice_keyword,
            lambda d: make_bazi_movie(chart, RESOURCE_DIR, d, FONT_PATH, zoom=zoom))
    return out_dir


def run_compat(spec_a: str, spec_b: str, args) -> Path:
    """合婚配对流水线"""
    check_lang(args.lang)
    birth_a = _parse_birth(spec_a)
    birth_b = _parse_birth(spec_b)
    chart_a = calculate_bazi(birth_a, tz_hours=args.tz)
    chart_b = calculate_bazi(birth_b, tz_hours=args.tz)
    result = analyze_compatibility(chart_a, chart_b)
    print(f"契合度: {result.score}/100  关系: {', '.join(result.facts)}")

    print("\n正在生成文案..." + ("（离线模板模式）" if args.offline else ""))
    script = generate_compat_content(result, use_llm=not args.offline, lang=args.lang)
    print("\n---- 文案 ----\n" + script + "\n--------------\n")

    out_dir = (ROOT_DIR / "appdata" /
               f"compat_{birth_a:%Y%m%d}_{birth_b:%Y%m%d}_{args.lang}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.txt").write_text(script, encoding="utf-8")
    save_publish_kit(build_compat_publish_kit(result, args.lang), out_dir)
    print(f"文案与发布素材已保存到: {out_dir}")

    if not args.script_only:
        from bazi_video import make_compat_movie
        _tts_and_render(
            script, out_dir, args.lang, args.voice,
            lambda d: make_compat_movie(result, args.lang, RESOURCE_DIR, d,
                                        FONT_PATH, zoom=args.zoom))
    return out_dir


# ---------------------------------------------------------------------------
# 并行 worker（必须是模块顶层函数才能被子进程序列化）
# ---------------------------------------------------------------------------

def _chart_job(params: dict) -> str:
    run_chart(**params)
    return params["date_str"]


def _zodiac_job(params: dict) -> str:
    animal = params["animal"]
    day = date_type.fromisoformat(params["day"])
    lang, offline = params["lang"], params["offline"]
    out_dir = Path(params["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    script = generate_zodiac_script(animal, day, use_llm=not offline, lang=lang)
    (out_dir / "script.txt").write_text(script, encoding="utf-8")
    save_publish_kit(build_zodiac_publish_kit(animal, day, lang), out_dir)
    if not params["script_only"]:
        from bazi_video import make_zodiac_movie
        _tts_and_render(
            script, out_dir, lang, params["voice"],
            lambda d: make_zodiac_movie(animal, day, lang, RESOURCE_DIR, d,
                                        FONT_PATH, zoom=params["zoom"]))
    return animal


def _year_job(params: dict) -> str:
    from bazi.annual import build_year_publish_kit, generate_year_script
    animal, year = params["animal"], params["year"]
    lang = params["lang"]
    out_dir = Path(params["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    script = generate_year_script(animal, year, lang=lang, use_llm=not params["offline"])
    (out_dir / "script.txt").write_text(script, encoding="utf-8")
    save_publish_kit(build_year_publish_kit(animal, year, lang), out_dir)
    if not params["script_only"]:
        from bazi_video import make_year_movie
        _tts_and_render(
            script, out_dir, lang, params["voice"],
            lambda d: make_year_movie(animal, year, lang, RESOURCE_DIR, d,
                                      FONT_PATH, zoom=params["zoom"]))
    return animal


def _run_jobs(job_fn, job_list, jobs: int, label: str):
    """串行或并行执行任务列表，汇总成功/失败"""
    done, failed = 0, 0
    if jobs <= 1:
        for i, params in enumerate(job_list, 1):
            try:
                print(f"\n===== [{i}/{len(job_list)}] =====")
                job_fn(params)
                done += 1
            except Exception as e:
                print(f"[{i}] 失败: {e}")
                failed += 1
    else:
        print(f"并行模式：{jobs} 进程")
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(job_fn, params): params for params in job_list}
            for future in as_completed(futures):
                try:
                    name = future.result()
                    done += 1
                    print(f"✓ 完成 {name} ({done + failed}/{len(job_list)})")
                except Exception as e:
                    failed += 1
                    print(f"✗ 失败: {e}")
    print(f"\n{label}完成：成功 {done} 条，失败 {failed} 条")


def run_batch(csv_path: Path, args) -> None:
    """批量模式：逐行跑个人命盘流水线（--jobs 并行）"""
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    job_list = []
    for row in rows:
        date_str = (row.get("date") or "").strip()
        if not date_str:
            print(f"跳过一行：缺少 date 列")
            continue
        job_list.append(dict(
            date_str=date_str,
            time_str=(row.get("time") or "").strip() or "12:00",
            tz=float((row.get("tz") or "").strip() or 8),
            gender=(row.get("gender") or "").strip() or None,
            lang=(row.get("lang") or "").strip() or args.lang,
            voice_keyword=(row.get("voice") or "").strip() or args.voice,
            offline=args.offline,
            zoom=args.zoom,
            script_only=args.script_only,
        ))
    print(f"批量模式：共 {len(job_list)} 条")
    _run_jobs(_chart_job, job_list, args.jobs, "批量")


def run_zodiac_series(day: date_type, lang: str, args) -> None:
    """生肖系列：12 条当日运势（--jobs 并行）"""
    check_lang(lang)
    series_dir = ROOT_DIR / "appdata" / f"zodiac_{day:%Y%m%d}_{lang}"
    print(f"生肖每日运势系列：{day} / {lang}，输出到 {series_dir}")
    job_list = [dict(
        animal=animal, day=day.isoformat(), lang=lang,
        offline=args.offline, script_only=args.script_only,
        voice=args.voice, zoom=args.zoom,
        out_dir=str(series_dir / animal.lower()),
    ) for animal in BRANCH_ANIMAL]
    _run_jobs(_zodiac_job, job_list, args.jobs, "系列")


def main():
    args = parse_args()

    if args.compat:
        run_compat(args.compat[0], args.compat[1], args)
        return

    if args.batch:
        run_batch(Path(args.batch), args)
        return

    if args.series == "zodiac":
        day = (datetime.strptime(args.series_date, "%Y-%m-%d").date()
               if args.series_date else date_type.today())
        run_zodiac_series(day, args.lang, args)
        return

    if args.series == "year":
        year = args.year or date_type.today().year
        series_dir = ROOT_DIR / "appdata" / f"year_{year}_{args.lang}"
        print(f"生肖流年运势系列：{year} / {args.lang}，输出到 {series_dir}")
        job_list = [dict(
            animal=animal, year=year, lang=args.lang,
            offline=args.offline, script_only=args.script_only,
            voice=args.voice, zoom=args.zoom,
            out_dir=str(series_dir / animal.lower()),
        ) for animal in BRANCH_ANIMAL]
        _run_jobs(_year_job, job_list, args.jobs, "系列")
        return

    date_str = args.date or input("请输入出生日期 (YYYY-MM-DD): ").strip()
    time_str = args.time if args.date else (
        input("请输入出生时间 (HH:MM，直接回车默认 12:00): ").strip() or "12:00")
    run_chart(date_str, time_str, args.tz, args.gender, args.lang,
              args.voice, args.offline, args.zoom, args.script_only,
              longitude=args.longitude, variants=args.variants, report=args.report)


if __name__ == "__main__":
    main()
