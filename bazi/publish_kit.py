"""
发布素材生成：视频标题、简介、话题标签。

输出 publish.json（结构化）与 publish.txt（复制粘贴友好），
配合渲染器导出的 thumbnail.png 即为一套完整发布物料。
"""

import json
from datetime import date as date_type, datetime
from pathlib import Path
from typing import Dict, Optional

from .calculator import BaziChart
from .locales import ANIMAL_NAMES, ELEMENT_NAMES, PUBLISH, check_lang
from .script_writer import _day_master_phrase, format_date


def build_chart_publish_kit(chart: BaziChart, lang: str = "en") -> Dict[str, object]:
    """个人命盘视频的发布素材"""
    check_lang(lang)
    p = PUBLISH[lang]
    date_str = format_date(chart.birth_time, lang)
    title = p["title_chart"].format(date=date_str)
    description = p["description_chart"].format(
        date=date_str,
        day_master=_day_master_phrase(chart, lang),
        dominant=ELEMENT_NAMES[lang][chart.dominant_element()],
    )
    return {
        "type": "chart",
        "lang": lang,
        "title": title,
        "description": description,
        "hashtags": p["hashtags"],
    }


def build_zodiac_publish_kit(animal: str, day: date_type, lang: str = "en") -> Dict[str, object]:
    """生肖每日运势视频的发布素材"""
    check_lang(lang)
    p = PUBLISH[lang]
    animal_local = ANIMAL_NAMES[lang][animal]
    date_str = format_date(datetime(day.year, day.month, day.day), lang)
    return {
        "type": "zodiac",
        "lang": lang,
        "title": p["title_zodiac"].format(animal=animal_local, date=date_str),
        "description": p["description_zodiac"].format(animal=animal_local),
        "hashtags": p["hashtags"],
    }


def build_compat_publish_kit(result, lang: str = "en") -> Dict[str, object]:
    """合婚配对视频的发布素材（result 为 CompatResult）"""
    check_lang(lang)
    p = PUBLISH[lang]
    da = format_date(result.chart_a.birth_time, lang)
    db = format_date(result.chart_b.birth_time, lang)
    return {
        "type": "compat",
        "lang": lang,
        "title": p["title_compat"].format(da=da, db=db),
        "description": p["description_compat"].format(da=da, db=db, score=result.score),
        "hashtags": p["hashtags"] + (["#compatibility", "#couplegoals"] if lang == "en" else
                                     ["#compatibilidad"] if lang == "es" else
                                     ["#compatibilidade"]),
    }


def save_publish_kit(kit: Dict[str, object], out_dir: Path) -> Path:
    """保存 publish.json + publish.txt，返回 txt 路径"""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "publish.json").write_text(
        json.dumps(kit, ensure_ascii=False, indent=2), encoding="utf-8")
    txt = (f"TITLE:\n{kit['title']}\n\n"
           f"DESCRIPTION:\n{kit['description']}\n\n"
           f"HASHTAGS:\n{' '.join(kit['hashtags'])}\n")
    txt_path = out_dir / "publish.txt"
    txt_path.write_text(txt, encoding="utf-8")
    return txt_path
