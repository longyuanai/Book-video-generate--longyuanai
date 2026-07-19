"""bazi 模块单元测试（不依赖 pygame/opencv，CI 可轻量运行）"""

from datetime import date, datetime, timedelta

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

    def test_zodiac_deterministic(self):
        d = date(2026, 7, 18)
        assert _template_zodiac("Dragon", d, "en") == _template_zodiac("Dragon", d, "en")
        assert _template_zodiac("Dragon", d, "en") != _template_zodiac("Rat", d, "en")


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
