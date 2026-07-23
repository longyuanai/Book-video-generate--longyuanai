"""
八字（四柱）排盘计算模块 —— 面向海外受众，输出中英双语信息。

BaZi (Four Pillars of Destiny) calculator.
Given a birth date & time, computes the Year / Month / Day / Hour pillars,
the Day Master, Ten Gods, Luck Pillars (大运), five-element distribution
and the Chinese zodiac animal, with English translations suitable for
overseas short-video content.

精度说明：
- 年柱/月柱以「节气」为界，节气时刻由天文算法计算（误差约 ±15 分钟），
  见 solar_terms.py；
- 支持出生地时区（tz_hours，相对 UTC），海外出生排盘必备；
- 日柱锚点：1949-10-01 为甲子日；默认「晚子时换日」（23:00 后按次日排日柱）。
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .solar_terms import jie_moment_utc, month_order_and_boundaries, solar_year_of

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
# 地支本气天干（用于地支十神）
BRANCH_MAIN_STEM = [9, 5, 0, 1, 4, 2, 3, 5, 6, 7, 4, 8]
# 地支藏干全表（本气在前）
BRANCH_HIDDEN_STEMS = [
    [9],        # 子: 癸
    [5, 9, 7],  # 丑: 己癸辛
    [0, 2, 4],  # 寅: 甲丙戊
    [1],        # 卯: 乙
    [4, 1, 9],  # 辰: 戊乙癸
    [2, 6, 4],  # 巳: 丙庚戊
    [3, 5],     # 午: 丁己
    [5, 3, 1],  # 未: 己丁乙
    [6, 8, 4],  # 申: 庚壬戊
    [7],        # 酉: 辛
    [4, 7, 3],  # 戌: 戊辛丁
    [8, 0],     # 亥: 壬甲
]

ELEMENT_EMOJI = {"Wood": "🌳", "Fire": "🔥", "Earth": "⛰️", "Metal": "⚔️", "Water": "🌊"}
ELEMENT_CN = {"Wood": "木", "Fire": "火", "Earth": "土", "Metal": "金", "Water": "水"}
_ELEMENT_INDEX = {"Wood": 0, "Fire": 1, "Earth": 2, "Metal": 3, "Water": 4}

# 十神（中文, 英文）
TEN_GOD_NAMES = {
    "friend": ("比肩", "Friend"),
    "rob_wealth": ("劫财", "Rob Wealth"),
    "eating_god": ("食神", "Eating God"),
    "hurting_officer": ("伤官", "Hurting Officer"),
    "indirect_wealth": ("偏财", "Indirect Wealth"),
    "direct_wealth": ("正财", "Direct Wealth"),
    "seven_killings": ("七杀", "Seven Killings"),
    "direct_officer": ("正官", "Direct Officer"),
    "indirect_resource": ("偏印", "Indirect Resource"),
    "direct_resource": ("正印", "Direct Resource"),
}

# 日柱锚点：1949-10-01 为甲子日
_DAY_ANCHOR = date(1949, 10, 1)

# 神煞（中文, 英文, 一句话英文含义）
SHENSHA_INFO = {
    "peach_blossom": ("桃花", "Peach Blossom", "romance and personal charm"),
    "travel_horse": ("驿马", "Travel Horse", "movement, travel and change"),
    "canopy": ("华盖", "Canopy Star", "solitude, wisdom and artistry"),
    "nobleman": ("天乙贵人", "Nobleman Star", "helpful people appearing in hard times"),
}

# 三合局组 -> (桃花, 驿马, 华盖) 对应地支下标
# 申子辰->酉寅辰  寅午戌->卯申戌  巳酉丑->午亥丑  亥卯未->子巳未
_TRINE_STARS = {
    frozenset([8, 0, 4]): (9, 2, 4),
    frozenset([2, 6, 10]): (3, 8, 10),
    frozenset([5, 9, 1]): (6, 11, 1),
    frozenset([11, 3, 7]): (0, 5, 7),
}

# 天乙贵人：日干 -> 贵人地支（甲戊庚牛羊，乙己鼠猴乡，丙丁猪鸡位，壬癸兔蛇藏，六辛逢马虎）
_NOBLEMAN = {
    0: [1, 7], 4: [1, 7], 6: [1, 7],   # 甲戊庚 -> 丑未
    1: [0, 8], 5: [0, 8],              # 乙己 -> 子申
    2: [11, 9], 3: [11, 9],            # 丙丁 -> 亥酉
    8: [3, 5], 9: [3, 5],              # 壬癸 -> 卯巳
    7: [6, 2],                          # 辛 -> 午寅
}


def _trine_group(branch: int) -> frozenset:
    for group in _TRINE_STARS:
        if branch in group:
            return group
    raise ValueError(branch)


def _equation_of_time_minutes(d: date) -> float:
    """均时差（分钟）近似公式，误差约 ±0.5 分钟"""
    import math
    b = 2 * math.pi * (d.timetuple().tm_yday - 81) / 364
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def ten_god_of(day_stem: int, other_stem: int) -> Tuple[str, str]:
    """other_stem 相对 day_stem（日主）的十神，返回 (中文, 英文)"""
    de = _ELEMENT_INDEX[STEM_ELEMENT[day_stem]]
    te = _ELEMENT_INDEX[STEM_ELEMENT[other_stem]]
    same_polarity = STEM_POLARITY[day_stem] == STEM_POLARITY[other_stem]
    if te == de:
        key = "friend" if same_polarity else "rob_wealth"
    elif (de + 1) % 5 == te:      # 我生者：食伤
        key = "eating_god" if same_polarity else "hurting_officer"
    elif (de + 2) % 5 == te:      # 我克者：财
        key = "indirect_wealth" if same_polarity else "direct_wealth"
    elif (te + 2) % 5 == de:      # 克我者：官杀
        key = "seven_killings" if same_polarity else "direct_officer"
    else:                          # 生我者：印
        key = "indirect_resource" if same_polarity else "direct_resource"
    return TEN_GOD_NAMES[key]


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

    @property
    def sexagenary_index(self) -> int:
        """六十甲子序号（甲子=0）"""
        for x in range(60):
            if x % 10 == self.stem_index and x % 12 == self.branch_index:
                return x
        raise ValueError("非法干支组合")

    @classmethod
    def from_sexagenary(cls, x: int) -> "Pillar":
        x %= 60
        return cls(x % 10, x % 12)

    def english(self) -> str:
        return (f"{STEM_POLARITY[self.stem_index]} {self.stem_element} over "
                f"{BRANCH_ANIMAL[self.branch_index]} ({self.branch_element})")


@dataclass
class LuckPillar:
    """大运：起始年龄 + 干支"""
    start_age: float
    pillar: Pillar

    def age_range(self) -> str:
        a = int(round(self.start_age))
        return f"{a}-{a + 9}"


@dataclass
class BaziChart:
    birth_time: datetime
    tz_hours: float = 8.0
    gender: Optional[str] = None  # "male" / "female"
    year: Pillar = field(default=None)
    month: Pillar = field(default=None)
    day: Pillar = field(default=None)
    hour: Pillar = field(default=None)
    luck_pillars: List[LuckPillar] = field(default_factory=list)

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

    def hidden_stems(self) -> Dict[str, List[str]]:
        """各柱地支藏干：{"Year": ["壬", "甲"], ...}"""
        return {name: [STEMS[s] for s in BRANCH_HIDDEN_STEMS[p.branch_index]]
                for name, p in self.pillars.items()}

    def shensha(self) -> List[Tuple[str, str, str]]:
        """
        神煞（娱乐向精选 4 颗）：返回 [(中文, 英文, 英文含义), ...]。
        桃花/驿马/华盖 以年支与日支三合局查全盘地支；天乙贵人以日干查全盘地支。
        """
        branches = [p.branch_index for p in self.pillars.values()]
        found = {}
        for ref in (self.year.branch_index, self.day.branch_index):
            peach, horse, canopy = _TRINE_STARS[_trine_group(ref)]
            for key, star in (("peach_blossom", peach), ("travel_horse", horse),
                              ("canopy", canopy)):
                if star in branches:
                    found[key] = SHENSHA_INFO[key]
        if any(b in _NOBLEMAN[self.day.stem_index] for b in branches):
            found["nobleman"] = SHENSHA_INFO["nobleman"]
        return list(found.values())

    def ten_gods(self) -> Dict[str, Dict[str, Tuple[str, str]]]:
        """
        各柱十神：{"Year": {"stem": (中,英), "branch": (中,英)}, ...}
        日柱天干为日主本身，标记为 ("日主", "Day Master")。
        """
        result = {}
        for name, p in self.pillars.items():
            stem_god = (("日主", "Day Master") if name == "Day"
                        else ten_god_of(self.day.stem_index, p.stem_index))
            branch_god = ten_god_of(self.day.stem_index, BRANCH_MAIN_STEM[p.branch_index])
            result[name] = {"stem": stem_god, "branch": branch_god}
        return result

    def summary_text(self) -> str:
        """终端友好的排盘摘要（中英双语）"""
        gods = self.ten_gods()
        lines = ["=" * 56]
        tz = f"UTC{'+' if self.tz_hours >= 0 else ''}{self.tz_hours:g}"
        lines.append(f"  BaZi Chart · 八字命盘  ({self.birth_time:%Y-%m-%d %H:%M} {tz})")
        lines.append("=" * 56)
        for name, p in self.pillars.items():
            g = gods[name]
            lines.append(f"  {name:<6} {p.hanzi}  {p.pinyin:<10} "
                         f"[{g['stem'][0]}/{g['branch'][0]}]  {p.english()}")
        lines.append("-" * 56)
        lines.append(f"  Day Master 日主: {self.day_master_english}")
        lines.append(f"  Zodiac 生肖: {self.zodiac_animal}")
        counts = self.element_counts()
        dist = "  ".join(f"{ELEMENT_CN[e]}{ELEMENT_EMOJI[e]}x{c}" for e, c in counts.items())
        lines.append(f"  Five Elements 五行: {dist}")
        missing = self.missing_elements()
        if missing:
            lines.append(f"  Missing 所缺: {', '.join(missing)}")
        if self.luck_pillars:
            lp = "  ".join(f"{l.pillar.hanzi}({l.age_range()})" for l in self.luck_pillars[:6])
            lines.append(f"  Luck Pillars 大运: {lp}")
        stars = self.shensha()
        if stars:
            lines.append(f"  Stars 神煞: {'  '.join(f'{cn}({en})' for cn, en, _ in stars)}")
        from .strength import analyze_strength
        s = analyze_strength(self)
        lines.append(f"  Strength 旺衰: {s.verdict_cn} ({s.ratio:.0%})  "
                     f"用神: {ELEMENT_CN[s.useful_god]} {s.useful_god}  "
                     f"喜: {'/'.join(s.favorable_elements)}")
        lines.append("=" * 56)
        return "\n".join(lines)


def _calc_luck_pillars(chart: BaziChart, birth_utc: datetime,
                       month_start_utc: datetime, month_end_utc: datetime) -> List[LuckPillar]:
    """
    大运：阳年男/阴年女顺排，阴年女以外逆排；
    起运年龄 = 出生到下一个节（顺）或上一个节（逆）的天数 / 3。
    """
    if chart.gender not in ("male", "female"):
        return []
    year_is_yang = STEM_POLARITY[chart.year.stem_index] == "Yang"
    forward = (year_is_yang and chart.gender == "male") or \
              (not year_is_yang and chart.gender == "female")

    if forward:
        days = (month_end_utc - birth_utc).total_seconds() / 86400
    else:
        days = (birth_utc - month_start_utc).total_seconds() / 86400
    start_age = days / 3  # 3 天折 1 年

    base = chart.month.sexagenary_index
    step = 1 if forward else -1
    return [
        LuckPillar(start_age=start_age + i * 10,
                   pillar=Pillar.from_sexagenary(base + step * (i + 1)))
        for i in range(8)
    ]


def calculate_bazi(birth: datetime, tz_hours: float = 8.0,
                   gender: Optional[str] = None,
                   late_zi_next_day: bool = True,
                   longitude: Optional[float] = None) -> BaziChart:
    """
    根据公历出生时间排四柱。

    Args:
        birth: 公历出生日期时间（出生地当地时间）
        tz_hours: 出生地时区（相对 UTC 的小时数，默认 +8 中国；
                  纽约冬令时 -5、洛杉矶冬令时 -8、伦敦 0 等）
        gender: "male"/"female"，提供后计算大运
        late_zi_next_day: 晚子时（23:00 后）是否按次日排日柱（默认主流排法：是）
        longitude: 出生地经度（东经为正，如北京 116.4、纽约 -74.0）。
                   提供后按真太阳时校正日柱/时柱（钟表时 -> 当地真太阳时，
                   含经度差与均时差），传统排盘的严谨做法。
    """
    # 真太阳时校正（仅影响日柱/时柱的当地时刻；节气比较用绝对 UTC 不受影响）
    local_birth = birth
    if longitude is not None:
        offset_min = (longitude - tz_hours * 15) * 4 + _equation_of_time_minutes(birth.date())
        local_birth = birth + timedelta(minutes=offset_min)

    chart = BaziChart(birth_time=birth, tz_hours=tz_hours, gender=gender)
    birth_utc = birth - timedelta(hours=tz_hours)

    # ---- 年柱：以立春（精确时刻）为界 ----
    solar_year = solar_year_of(birth_utc)
    chart.year = Pillar((solar_year - 4) % 10, (solar_year - 4) % 12)

    # ---- 月柱：以节（精确时刻）为界，五虎遁月 ----
    month_order, month_start_utc, month_end_utc = month_order_and_boundaries(birth_utc)
    month_branch = (month_order + 2) % 12  # 寅在 BRANCHES 中下标为 2
    month_stem = (chart.year.stem_index % 5 * 2 + 2 + month_order) % 10
    chart.month = Pillar(month_stem, month_branch)

    # ---- 日柱：甲子日锚点 + 晚子时换日（按出生地当地/真太阳时间）----
    day_for_pillar = local_birth.date()
    if late_zi_next_day and local_birth.hour == 23:
        day_for_pillar += timedelta(days=1)
    day_index = (day_for_pillar - _DAY_ANCHOR).days % 60
    chart.day = Pillar(day_index % 10, day_index % 12)

    # ---- 时柱：五鼠遁时 ----
    hour_branch = ((local_birth.hour + 1) // 2) % 12
    hour_stem = (chart.day.stem_index * 2 + hour_branch) % 10
    chart.hour = Pillar(hour_stem, hour_branch)

    # ---- 大运 ----
    chart.luck_pillars = _calc_luck_pillars(chart, birth_utc, month_start_utc, month_end_utc)

    return chart


if __name__ == "__main__":
    # 自检 1：2000-01-01 00:30 北京时间 -> 己卯年 丙子月 戊午日 壬子时
    chart = calculate_bazi(datetime(2000, 1, 1, 0, 30))
    print(chart.summary_text())
    assert chart.year.hanzi == "己卯", chart.year.hanzi
    assert chart.month.hanzi == "丙子", chart.month.hanzi
    assert chart.day.hanzi == "戊午", chart.day.hanzi
    assert chart.hour.hanzi == "壬子", chart.hour.hanzi

    # 自检 2：十神关系（庚日主）
    assert ten_god_of(6, 0) == ("偏财", "Indirect Wealth")   # 庚 vs 甲
    assert ten_god_of(6, 1) == ("正财", "Direct Wealth")     # 庚 vs 乙
    assert ten_god_of(6, 2) == ("七杀", "Seven Killings")    # 庚 vs 丙
    assert ten_god_of(6, 3) == ("正官", "Direct Officer")    # 庚 vs 丁
    assert ten_god_of(6, 9) == ("伤官", "Hurting Officer")   # 庚 vs 癸
    assert ten_god_of(6, 6) == ("比肩", "Friend")            # 庚 vs 庚

    # 自检 3：大运方向（乙亥阴年，男逆排女顺排）
    c = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="male")
    print(c.summary_text())
    assert c.month.hanzi == "甲申"
    assert c.luck_pillars[0].pillar.hanzi == "癸未", c.luck_pillars[0].pillar.hanzi  # 逆排
    cf = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="female")
    assert cf.luck_pillars[0].pillar.hanzi == "乙酉", cf.luck_pillars[0].pillar.hanzi  # 顺排

    # 自检 4：立春边界（2024-02-04 16:27 北京时间交立春）
    before = calculate_bazi(datetime(2024, 2, 4, 15, 0))
    after = calculate_bazi(datetime(2024, 2, 4, 17, 0))
    assert before.year.hanzi == "癸卯" and after.year.hanzi == "甲辰"

    # 自检 5：时区（纽约 2000-01-01 00:30 UTC-5 = 北京 13:30，同为己卯年）
    ny = calculate_bazi(datetime(2000, 1, 1, 0, 30), tz_hours=-5)
    assert ny.year.hanzi == "己卯"

    # 自检 6：藏干与神煞（1995-08-17 庚辰日，四支 亥申辰未）
    hidden = c.hidden_stems()
    assert hidden["Year"] == ["壬", "甲"], hidden["Year"]      # 亥藏壬甲
    assert hidden["Day"] == ["戊", "乙", "癸"], hidden["Day"]  # 辰藏戊乙癸
    star_names = [en for _, en, _ in c.shensha()]
    assert "Nobleman Star" in star_names, star_names   # 庚日干见未
    assert "Canopy Star" in star_names, star_names     # 申子辰组见辰

    # 自检 7：真太阳时（乌鲁木齐经度 87.6 用北京时间，钟表 15:30 真太阳时约 13:20 -> 未时）
    urumqi = calculate_bazi(datetime(1995, 8, 17, 15, 30), longitude=87.6)
    assert BRANCHES[urumqi.hour.branch_index] == "未", urumqi.hour.hanzi

    print("calculator self-check passed ✓")
