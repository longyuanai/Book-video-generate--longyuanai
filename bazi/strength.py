"""
用神喜忌引擎：日主旺衰判定 + 喜用/忌讳五行。

采用通俗旺衰计分法（内容/报告级，非流派争议裁决器）：
- 八字中每个天干计 10 分；地支藏干按 本气10/中气5/余气3 计分；
- 月令（月支）权重 ×3 —— 「得令」是旺衰第一要素；
- 生我（印）与同我（比劫）计入「帮扶」，食伤/财/官杀计入「消耗」；
- 帮扶占比 > 0.55 判身强，< 0.45 判身弱，其间为中和（并给出偏向）。

用神规则（主流简化）：
- 身弱：喜 印（生我）与 比劫（同我），用神优先取盘中有根的印；
- 身强：喜 官杀（克我）、食伤（泄我）、财（耗我），用神取其中盘内最旺者；
- 中和：按偏向微调（偏强按强、偏弱按弱），格局评价为「平衡」。
"""

from dataclasses import dataclass, field
from typing import Dict, List

from .calculator import (BRANCH_HIDDEN_STEMS, BaziChart, STEM_ELEMENT,
                         _ELEMENT_INDEX)

_ELEMENTS = ["Wood", "Fire", "Earth", "Metal", "Water"]

# 藏干计分：本气/中气/余气
_HIDDEN_WEIGHTS = [10, 5, 3]
_MONTH_MULTIPLIER = 3  # 月令权重

# 十神五类（相对日主五行 de 的偏移）：0 比劫 1 食伤 2 财 3 官杀 4 印
_ROLE_NAMES = {
    0: ("比劫", "companions"),
    1: ("食伤", "output"),
    2: ("财", "wealth"),
    3: ("官杀", "authority"),
    4: ("印", "resource"),
}


def _role_of(day_element_idx: int, other_element_idx: int) -> int:
    """返回 other 相对日主的五类角色偏移：0比劫 1食伤 2财 3官杀 4印"""
    return (other_element_idx - day_element_idx) % 5


@dataclass
class StrengthResult:
    support: float                 # 帮扶得分（印 + 比劫）
    drain: float                   # 消耗得分（食伤 + 财 + 官杀）
    ratio: float                   # support / (support + drain)
    verdict: str                   # "strong" / "weak" / "balanced"
    lean: str                      # 中和时的偏向："strong" / "weak"
    favorable_elements: List[str]  # 喜用五行（英文名）
    unfavorable_elements: List[str]  # 忌讳五行
    useful_god: str                # 用神五行（单一，英文名）
    element_scores: Dict[str, float] = field(default_factory=dict)  # 各五行总分

    @property
    def verdict_cn(self) -> str:
        return {"strong": "身强", "weak": "身弱", "balanced": "中和"}[self.verdict]


def analyze_strength(chart: BaziChart) -> StrengthResult:
    """对命盘做旺衰判定与用神喜忌分析"""
    de = _ELEMENT_INDEX[STEM_ELEMENT[chart.day.stem_index]]

    element_scores = {e: 0.0 for e in _ELEMENTS}
    support = 0.0
    drain = 0.0

    for name, pillar in chart.pillars.items():
        # 月令权重只作用于月支藏干（「得令」看月支司令，与月干无关）
        branch_mult = _MONTH_MULTIPLIER if name == "Month" else 1

        # 天干（日主自身不计入帮扶/消耗，但计入五行分布）
        stem_e = _ELEMENT_INDEX[STEM_ELEMENT[pillar.stem_index]]
        element_scores[_ELEMENTS[stem_e]] += 10
        if not (name == "Day"):
            if _role_of(de, stem_e) in (0, 4):
                support += 10
            else:
                drain += 10

        # 地支藏干
        for i, hidden in enumerate(BRANCH_HIDDEN_STEMS[pillar.branch_index]):
            w = _HIDDEN_WEIGHTS[i] * branch_mult
            he = _ELEMENT_INDEX[STEM_ELEMENT[hidden]]
            element_scores[_ELEMENTS[he]] += w
            if _role_of(de, he) in (0, 4):
                support += w
            else:
                drain += w

    total = support + drain
    ratio = support / total if total else 0.5
    if ratio > 0.55:
        verdict, lean = "strong", "strong"
    elif ratio < 0.45:
        verdict, lean = "weak", "weak"
    else:
        verdict = "balanced"
        lean = "strong" if ratio >= 0.5 else "weak"

    resource_e = _ELEMENTS[(de + 4) % 5]   # 印
    companion_e = _ELEMENTS[de]            # 比劫
    output_e = _ELEMENTS[(de + 1) % 5]     # 食伤
    wealth_e = _ELEMENTS[(de + 2) % 5]     # 财
    authority_e = _ELEMENTS[(de + 3) % 5]  # 官杀

    if lean == "weak":
        favorable = [resource_e, companion_e]
        unfavorable = [authority_e, wealth_e, output_e]
        # 用神优先取盘中有根的印，无印则取比劫
        useful = resource_e if element_scores[resource_e] > 0 else companion_e
    else:
        favorable = [authority_e, output_e, wealth_e]
        unfavorable = [resource_e, companion_e]
        # 用神取克泄耗中盘内最旺者
        useful = max(favorable, key=lambda e: element_scores[e])

    return StrengthResult(
        support=support, drain=drain, ratio=round(ratio, 3),
        verdict=verdict, lean=lean,
        favorable_elements=favorable, unfavorable_elements=unfavorable,
        useful_god=useful, element_scores=element_scores,
    )


# 五行开运指引（幸运色 / 方位，三语），供文案与报告使用
ELEMENT_LUCKY = {
    "Wood": {
        "en": ("green", "east"), "es": ("verde", "el este"), "pt": ("verde", "o leste"),
    },
    "Fire": {
        "en": ("red", "south"), "es": ("rojo", "el sur"), "pt": ("vermelho", "o sul"),
    },
    "Earth": {
        "en": ("yellow and earth tones", "the southwest"),
        "es": ("amarillo y tonos tierra", "el suroeste"),
        "pt": ("amarelo e tons terrosos", "o sudoeste"),
    },
    "Metal": {
        "en": ("white and gold", "west"), "es": ("blanco y dorado", "el oeste"),
        "pt": ("branco e dourado", "o oeste"),
    },
    "Water": {
        "en": ("blue and black", "north"), "es": ("azul y negro", "el norte"),
        "pt": ("azul e preto", "o norte"),
    },
}

# 用神文案句（融入命盘解读模板）
FAVORABLE_PHRASES = {
    "en": "And here is your power move. Weighing your whole chart, your lucky element is "
          "{element}. Bring more {color} into your life, and face {direction} when you "
          "need clarity.",
    "es": "Y aquí va tu jugada maestra. Sopesando toda tu carta, tu elemento de la suerte "
          "es {element}. Trae más {color} a tu vida, y mira hacia {direction} cuando "
          "necesites claridad.",
    "pt": "E aqui vai a sua jogada mestra. Pesando o seu mapa inteiro, o seu elemento da "
          "sorte é {element}. Traga mais {color} para a sua vida, e olhe para {direction} "
          "quando precisar de clareza.",
}


def favorable_sentence(chart: BaziChart, lang: str) -> str:
    """生成「用神幸运五行」文案句（本地化）"""
    from .locales import ELEMENT_NAMES
    r = analyze_strength(chart)
    color, direction = ELEMENT_LUCKY[r.useful_god][lang]
    return FAVORABLE_PHRASES[lang].format(
        element=ELEMENT_NAMES[lang][r.useful_god], color=color, direction=direction)


if __name__ == "__main__":
    from datetime import datetime
    from .calculator import calculate_bazi

    c = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="female")
    r = analyze_strength(c)
    print(c.summary_text())
    print(f"\n旺衰: {r.verdict_cn} (帮扶 {r.support:.0f} vs 消耗 {r.drain:.0f}, "
          f"占比 {r.ratio:.0%})")
    print(f"喜用: {r.favorable_elements}  忌: {r.unfavorable_elements}  用神: {r.useful_god}")
