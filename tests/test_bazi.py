"""bazi 模块单元测试（不依赖 pygame/opencv，CI 可轻量运行）"""

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from bazi.calculator import BRANCHES, calculate_bazi, ten_god_of
from bazi.compatibility import analyze_compatibility, generate_compat_script
from bazi.locales import SUPPORTED_LANGS
from bazi.publish_kit import (build_chart_publish_kit, build_compat_publish_kit,
                              build_zodiac_publish_kit)
from bazi.script_writer import _TEMPLATES, _template_zodiac, generate_bazi_script
from bazi.solar_terms import jie_moment_utc


class TestSolarTerms:
    @pytest.mark.parametrize("solar_year,jie,expected_bj", [
        (2024, 0, datetime(2024, 2, 4, 16, 27)),   # 立春 2024
        (2024, 11, datetime(2025, 1, 5, 10, 33)),  # 小寒 2025
        (2000, 0, datetime(2000, 2, 4, 20, 40)),   # 立春 2000
    ])
    def test_against_almanac(self, solar_year, jie, expected_bj):
        got = jie_moment_utc(solar_year, jie) + timedelta(hours=8)
        assert abs((got - expected_bj).total_seconds()) < 3600  # 1 小时容差


class TestCalculator:
    def test_known_chart(self):
        c = calculate_bazi(datetime(2000, 1, 1, 0, 30))
        assert [p.hanzi for p in c.pillars.values()] == ["己卯", "丙子", "戊午", "壬子"]

    def test_lichun_boundary(self):
        assert calculate_bazi(datetime(2024, 2, 4, 15, 0)).year.hanzi == "癸卯"
        assert calculate_bazi(datetime(2024, 2, 4, 17, 0)).year.hanzi == "甲辰"

    def test_timezone(self):
        assert calculate_bazi(datetime(2000, 1, 1, 0, 30), tz_hours=-5).year.hanzi == "己卯"

    def test_ten_gods(self):
        assert ten_god_of(6, 0) == ("偏财", "Indirect Wealth")
        assert ten_god_of(6, 2) == ("七杀", "Seven Killings")
        assert ten_god_of(6, 6) == ("比肩", "Friend")

    def test_luck_pillars_direction(self):
        male = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="male")
        female = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="female")
        assert male.luck_pillars[0].pillar.hanzi == "癸未"    # 阴年男逆排
        assert female.luck_pillars[0].pillar.hanzi == "乙酉"  # 阴年女顺排

    def test_hidden_stems_and_shensha(self):
        c = calculate_bazi(datetime(1995, 8, 17, 14, 30))
        assert c.hidden_stems()["Year"] == ["壬", "甲"]
        stars = [en for _, en, _ in c.shensha()]
        assert "Nobleman Star" in stars and "Canopy Star" in stars

    def test_true_solar_time(self):
        # 乌鲁木齐（东经 87.6）钟表 15:30 ≈ 真太阳时 13:20 -> 未时
        c = calculate_bazi(datetime(1995, 8, 17, 15, 30), longitude=87.6)
        assert BRANCHES[c.hour.branch_index] == "未"


class TestScripts:
    def test_chart_templates_all_langs(self):
        c = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="female")
        for lang in SUPPORTED_LANGS:
            script = _TEMPLATES[lang](c)
            assert len(script.split()) > 80
        assert "Canopy Star" in _TEMPLATES["en"](c)

    def test_offline_generate(self):
        c = calculate_bazi(datetime(2000, 1, 1, 0, 30))
        assert "January 01, 2000" in generate_bazi_script(c, use_llm=False)

    def test_zodiac_daily_engine(self):
        from bazi.script_writer import generate_zodiac_script
        d = date(2026, 7, 18)
        s1 = generate_zodiac_script("Dragon", d, use_llm=False, lang="en")
        assert s1 == generate_zodiac_script("Dragon", d, use_llm=False, lang="en")  # 确定性
        assert s1 != generate_zodiac_script("Rat", d, use_llm=False, lang="en")
        assert "July 18, 2026" in s1


class TestCompatibility:
    def test_score_and_script(self):
        a = calculate_bazi(datetime(1995, 8, 17, 14, 30))
        b = calculate_bazi(datetime(1997, 2, 11, 8, 0))
        r = analyze_compatibility(a, b)
        assert 8 <= r.score <= 98
        for lang in SUPPORTED_LANGS:
            assert str(r.score) in generate_compat_script(r, lang)

    def test_liuhe_bonus(self):
        # 鼠(子)+牛(丑) 六合年支应加分
        rat = calculate_bazi(datetime(1996, 6, 1, 12, 0))   # 丙子年
        ox = calculate_bazi(datetime(1997, 6, 1, 12, 0))    # 丁丑年
        r = analyze_compatibility(rat, ox)
        assert "zodiac_liuhe" in r.facts


class TestPublishKit:
    def test_all_kits(self):
        c = calculate_bazi(datetime(1995, 8, 17, 14, 30))
        r = analyze_compatibility(c, calculate_bazi(datetime(1997, 2, 11, 8, 0)))
        for lang in SUPPORTED_LANGS:
            for kit in (build_chart_publish_kit(c, lang),
                        build_zodiac_publish_kit("Dragon", date(2026, 7, 18), lang),
                        build_compat_publish_kit(r, lang)):
                assert kit["title"] and kit["description"] and kit["hashtags"]


def _make_chart(pillars_str):
    """从 '甲寅 丙寅 甲寅 乙亥' 构造命盘（测试用）"""
    from bazi.calculator import BaziChart, Pillar, STEMS as S, BRANCHES as B
    ps = [Pillar(S.index(x[0]), B.index(x[1])) for x in pillars_str.split()]
    c = BaziChart(birth_time=datetime(2000, 1, 1))
    c.year, c.month, c.day, c.hour = ps
    return c


class TestStrength:
    def test_obviously_strong(self):
        from bazi.strength import analyze_strength
        r = analyze_strength(_make_chart("甲寅 丙寅 甲寅 乙亥"))
        assert r.verdict == "strong"
        assert "Wood" not in r.favorable_elements  # 身强不喜比劫

    def test_obviously_weak(self):
        from bazi.strength import analyze_strength
        r = analyze_strength(_make_chart("庚申 甲申 甲申 庚午"))
        assert r.verdict == "weak"
        assert r.favorable_elements == ["Water", "Wood"]  # 印 + 比劫
        assert r.useful_god == "Water"

    def test_favorable_sentence_all_langs(self):
        from bazi.strength import favorable_sentence
        c = calculate_bazi(datetime(1995, 8, 17, 14, 30))
        for lang in SUPPORTED_LANGS:
            assert len(favorable_sentence(c, lang)) > 40

    def test_in_chart_templates(self):
        c = calculate_bazi(datetime(1995, 8, 17, 14, 30))
        assert "lucky element" in _TEMPLATES["en"](c)


class TestDaily:
    def test_day_pillar_anchor(self):
        from bazi.daily import day_pillar_of
        assert day_pillar_of(date(2000, 1, 1)).hanzi == "戊午"

    def test_relations(self):
        from bazi.daily import daily_relation
        d = date(2000, 1, 1)  # 戊午日
        assert daily_relation("Horse", d) == "same"    # 午值日
        assert daily_relation("Rat", d) == "chong"     # 子午冲
        assert daily_relation("Goat", d) == "liuhe"    # 午未合
        assert daily_relation("Tiger", d) == "sanhe"   # 寅午戌

    def test_script_all_langs(self):
        from bazi.daily import generate_daily_script
        for lang in SUPPORTED_LANGS:
            s = generate_daily_script("Horse", date(2000, 1, 1), lang)
            assert len(s.split()) > 40

    def test_english_article(self):
        from bazi.daily import generate_daily_script
        # 戊午为 Earth 日 -> "an Earth ... day"
        s = generate_daily_script("Horse", date(2000, 1, 1), "en")
        assert "an Earth" in s


class TestAnnual:
    def test_2026_fire_horse(self):
        from bazi.annual import generate_year_script, year_pillar, year_relation
        assert year_pillar(2026).hanzi == "丙午"
        assert year_relation(2026, "Horse") == "tai_sui"
        assert year_relation(2026, "Rat") == "chong"
        assert year_relation(2026, "Goat") == "liuhe"
        assert year_relation(2026, "Tiger") == "sanhe"
        for lang in SUPPORTED_LANGS:
            assert "2026" in generate_year_script("Horse", 2026, lang, use_llm=False)

    def test_year_publish_kit(self):
        from bazi.annual import build_year_publish_kit
        kit = build_year_publish_kit("Dragon", 2026, "en")
        assert "2026" in kit["title"] and "#2026" in kit["hashtags"]


class TestReport:
    def test_pdf_generation(self, tmp_path):
        pytest.importorskip("fpdf")
        from bazi.report import generate_report
        chart = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="female")
        font = Path(__file__).parent.parent / "resource" / "fonts" / "msyh.ttc"
        out = generate_report(chart, tmp_path / "report.pdf", font, "en")
        assert out.exists() and out.stat().st_size > 15000


class TestLLMClient:
    def test_normalize_openai_style(self):
        from llm import LLMClient
        data = {"choices": [{"message": {"content": "hello"}}]}
        assert LLMClient._normalize_response(data)["content"] == "hello"

    def test_normalize_aggregate_style(self):
        from llm import LLMClient
        assert LLMClient._normalize_response({"content": "hi"})["content"] == "hi"

    def test_normalize_bad(self):
        from llm import LLMClient
        assert LLMClient._normalize_response({"foo": 1}).get("error")
