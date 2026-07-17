"""
八字（四柱）排盘计算模块 —— 面向海外受众，输出中英双语信息。

BaZi (Four Pillars of Destiny) calculator.
Given a birth date & time, computes the Year / Month / Day / Hour pillars
(Heavenly Stem + Earthly Branch), the Day Master, five-element distribution
and the Chinese zodiac animal, with English translations suitable for
overseas short-video content.

注意 / Accuracy notes:
- 年柱与月柱以「节气」为界。本模块使用近似节气日期（误差 ±1 天），
  出生在节气交接日附近的排盘可能偏差一柱，用于短视频内容足够，
  专业排盘请使用天文历法库校准。
- 日柱锚点：1949-10-01 为甲子日（60 天一循环）。
- 默认采用「晚子时换日」规则：23:00 之后按次日排日柱。
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List

# 十天干 Heavenly Stems
STEMS = "甲乙丙丁戊己庚辛壬癸"
STEM_PINYIN = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
STEM_ELEMENT = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
STEM_POLARITY = ["Yang", "Yin", "Yang", "Yin", "Yang", "Yin", "Yang", "Yin", "Yang", "Yin"]

# 十二地支 Earthly Branches
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
BRANCH_PINYIN = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
BRANCH_ELEMENT = ["Water", "Earth", "Wood", "Wood", "Earth", "Fire", "Fire", "Earth", "Metal", "Metal", "Earth", "Water"]
BRANCH_ANIMAL = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]

ELEMENT_EMOJI = {"Wood": "🌳", "Fire": "🔥", "Earth": "⛰️", "Metal": "⚔️", "Water": "🌊"}
ELEMENT_CN = {"Wood": "木", "Fire": "火", "Earth": "土", "Metal": "金", "Water": "水"}

# 近似节气日（每月的「节」，用于确定月柱边界，误差 ±1 天）
# (month, day) -> 该日起进入的月支序号（寅=0）
_JIE_QI_APPROX = [
    (2, 4),   # 立春 -> 寅月
    (3, 6),   # 惊蛰 -> 卯月
    (4, 5),   # 清明 -> 辰月
    (5, 6),   # 立夏 -> 巳月
    (6, 6),   # 芒种 -> 午月
    (7, 7),   # 小暑 -> 未月
    (8, 8),   # 立秋 -> 申月
    (9, 8),   # 白露 -> 酉月
    (10, 8),  # 寒露 -> 戌月
    (11, 7),  # 立冬 -> 亥月
    (12, 7),  # 大雪 -> 子月
    (1, 6),   # 小寒 -> 丑月
]

# 日柱锚点：1949-10-01 为甲子日
_DAY_ANCHOR = date(1949, 10, 1)


@dataclass
class Pillar:
    """一柱：天干 + 地支"""
    stem_index: int
    branch_index: int

    @property
    def hanzi(self) -> str:
        return STEMS[self.stem_index] + BRANCHES[self.branch_index]

    @property
    def pinyin(self) -> str:
        return f"{STEM_PINYIN[self.stem_index]} {BRANCH_PINYIN[self.branch_index]}"

    @property
    def stem_element(self) -> str:
        return STEM_ELEMENT[self.stem_index]

    @property
    def branch_element(self) -> str:
        return BRANCH_ELEMENT[self.branch_index]

    @property
    def animal(self) -> str:
        return BRANCH_ANIMAL[self.branch_index]

    def english(self) -> str:
        return (f"{STEM_POLARITY[self.stem_index]} {self.stem_element} over "
                f"{BRANCH_ANIMAL[self.branch_index]} ({self.branch_element})")


@dataclass
class BaziChart:
    birth_time: datetime
    year: Pillar = field(default=None)
    month: Pillar = field(default=None)
    day: Pillar = field(default=None)
    hour: Pillar = field(default=None)

    @property
    def pillars(self) -> Dict[str, Pillar]:
        return {"Year": self.year, "Month": self.month, "Day": self.day, "Hour": self.hour}

    @property
    def day_master(self) -> str:
        """日主（日元）：日柱天干，是整张命盘的核心"""
        return STEMS[self.day.stem_index]

    @property
    def day_master_english(self) -> str:
        i = self.day.stem_index
        return f"{STEM_POLARITY[i]} {STEM_ELEMENT[i]} ({STEM_PINYIN[i]} {STEMS[i]})"

    @property
    def zodiac_animal(self) -> str:
        """生肖（按年支）"""
        return BRANCH_ANIMAL[self.year.branch_index]

    def element_counts(self) -> Dict[str, int]:
        """统计八字中五行出现次数（天干+地支各一，共 8 字）"""
        counts = {"Wood": 0, "Fire": 0, "Earth": 0, "Metal": 0, "Water": 0}
        for p in self.pillars.values():
            counts[p.stem_element] += 1
            counts[p.branch_element] += 1
        return counts

    def dominant_element(self) -> str:
        counts = self.element_counts()
        return max(counts, key=counts.get)

    def missing_elements(self) -> List[str]:
        return [e for e, c in self.element_counts().items() if c == 0]

    def summary_text(self) -> str:
        """终端友好的排盘摘要（中英双语）"""
        lines = ["=" * 46]
        lines.append(f"  BaZi Chart · 八字命盘  ({self.birth_time:%Y-%m-%d %H:%M})")
        lines.append("=" * 46)
        for name, p in self.pillars.items():
            lines.append(f"  {name:<6} {p.hanzi}  {p.pinyin:<10} {p.english()}")
        lines.append("-" * 46)
        lines.append(f"  Day Master 日主: {self.day_master_english}")
        lines.append(f"  Zodiac 生肖: {self.zodiac_animal}")
        counts = self.element_counts()
        dist = "  ".join(f"{ELEMENT_CN[e]}{ELEMENT_EMOJI[e]}x{c}" for e, c in counts.items())
        lines.append(f"  Five Elements 五行: {dist}")
        missing = self.missing_elements()
        if missing:
            lines.append(f"  Missing 所缺: {', '.join(missing)}")
        lines.append("=" * 46)
        return "\n".join(lines)


def _solar_year_start(year: int) -> date:
    """该公历年八字意义上的岁首（立春，近似 2 月 4 日）"""
    return date(year, 2, 4)


def _month_order(d: date) -> int:
    """
    返回节气月序：0=寅月（立春起）... 11=丑月（小寒起）。
    使用近似节气日期，误差 ±1 天。
    """
    if d.month == 1:
        # 小寒（约 1 月 6 日）之前仍是上一循环的子月
        return 11 if d.day >= _JIE_QI_APPROX[11][1] else 10
    if (d.month, d.day) < _JIE_QI_APPROX[0]:
        # 2 月立春之前，属上一年的丑月
        return 11
    order = 0
    for i, (m, day_) in enumerate(_JIE_QI_APPROX[:11]):
        if (d.month, d.day) >= (m, day_):
            order = i
    return order


def calculate_bazi(birth: datetime, late_zi_next_day: bool = True) -> BaziChart:
    """
    根据公历出生时间排四柱。

    Args:
        birth: 公历出生日期时间
        late_zi_next_day: 晚子时（23:00 后）是否按次日排日柱（默认按主流排法：是）
    """
    chart = BaziChart(birth_time=birth)

    # ---- 年柱：以立春为界 ----
    solar_year = birth.year if birth.date() >= _solar_year_start(birth.year) else birth.year - 1
    chart.year = Pillar((solar_year - 4) % 10, (solar_year - 4) % 12)

    # ---- 月柱：以节气为界，五虎遁月 ----
    month_order = _month_order(birth.date())  # 0=寅月 ... 11=丑月
    month_branch = (month_order + 2) % 12  # 寅在 BRANCHES 中下标为 2
    # 五虎遁：甲己之年丙作首
    month_stem = (chart.year.stem_index % 5 * 2 + 2 + month_order) % 10
    chart.month = Pillar(month_stem, month_branch)

    # ---- 日柱：甲子日锚点 + 晚子时换日 ----
    day_for_pillar = birth.date()
    if late_zi_next_day and birth.hour == 23:
        day_for_pillar += timedelta(days=1)
    day_index = (day_for_pillar - _DAY_ANCHOR).days % 60
    chart.day = Pillar(day_index % 10, day_index % 12)

    # ---- 时柱：五鼠遁时 ----
    hour_branch = ((birth.hour + 1) // 2) % 12
    hour_stem = (chart.day.stem_index * 2 + hour_branch) % 10
    chart.hour = Pillar(hour_stem, hour_branch)

    return chart


if __name__ == "__main__":
    # 自检：2000-01-01 00:30 应为 己卯年 丙子月 戊午日 壬子时
    chart = calculate_bazi(datetime(2000, 1, 1, 0, 30))
    print(chart.summary_text())
    assert chart.year.hanzi == "己卯", chart.year.hanzi
    assert chart.month.hanzi == "丙子", chart.month.hanzi
    assert chart.day.hanzi == "戊午", chart.day.hanzi
    assert chart.hour.hanzi == "壬子", chart.hour.hanzi
    print("self-check passed ✓")
