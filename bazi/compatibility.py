"""
合婚配对（Compatibility）：输入两人命盘，输出契合度评分与解读文案。

评分依据（娱乐向简化规则）：
- 年支关系：六合 / 三合（加分），六冲（减分）
- 日支（夫妻宫）关系：六合（加分），六冲（减分）
- 日主五行：相生（加分）、比和（小加分）、相克（小减分）
- 五行互补：一方的旺五行恰好补另一方所缺（加分）

「Drop your birthday + your person's birthday」是海外命理内容互动性最强的形态。
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .calculator import BaziChart, STEM_ELEMENT, _ELEMENT_INDEX, _trine_group
from .locales import ELEMENT_NAMES, check_lang
from .script_writer import _day_master_phrase, format_date

# 地支六合对
_LIUHE = {frozenset(p) for p in [(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)]}


def _branch_relation(a: int, b: int) -> str:
    """两地支关系: liuhe / sanhe / chong / neutral"""
    if frozenset((a, b)) in _LIUHE:
        return "liuhe"
    if a != b and _trine_group(a) == _trine_group(b):
        return "sanhe"
    if abs(a - b) == 6:
        return "chong"
    return "neutral"


@dataclass
class CompatResult:
    chart_a: BaziChart
    chart_b: BaziChart
    score: int
    facts: List[str]  # 结构化关系标签，供文案与 LLM 使用


def analyze_compatibility(chart_a: BaziChart, chart_b: BaziChart) -> CompatResult:
    score = 50
    facts = []

    # 年支（生肖）关系
    rel = _branch_relation(chart_a.year.branch_index, chart_b.year.branch_index)
    if rel == "liuhe":
        score += 15
        facts.append("zodiac_liuhe")
    elif rel == "sanhe":
        score += 12
        facts.append("zodiac_sanhe")
    elif rel == "chong":
        score -= 12
        facts.append("zodiac_chong")

    # 日支（夫妻宫）关系
    rel = _branch_relation(chart_a.day.branch_index, chart_b.day.branch_index)
    if rel in ("liuhe", "sanhe"):
        score += 10
        facts.append("spouse_harmony")
    elif rel == "chong":
        score -= 8
        facts.append("spouse_clash")

    # 日主五行关系
    ea = _ELEMENT_INDEX[STEM_ELEMENT[chart_a.day.stem_index]]
    eb = _ELEMENT_INDEX[STEM_ELEMENT[chart_b.day.stem_index]]
    if (ea + 1) % 5 == eb:
        score += 10
        facts.append("dm_generate_ab")
    elif (eb + 1) % 5 == ea:
        score += 10
        facts.append("dm_generate_ba")
    elif ea == eb:
        score += 5
        facts.append("dm_same")
    elif (ea + 2) % 5 == eb:
        score -= 4
        facts.append("dm_control_ab")
    else:
        score -= 4
        facts.append("dm_control_ba")

    # 五行互补
    if chart_a.dominant_element() in chart_b.missing_elements():
        score += 8
        facts.append("complement_ab")
    if chart_b.dominant_element() in chart_a.missing_elements():
        score += 8
        facts.append("complement_ba")

    return CompatResult(chart_a, chart_b, max(8, min(98, score)), facts)


# ---------------------------------------------------------------------------
# 三语文案
# ---------------------------------------------------------------------------

_FACT_PHRASES: Dict[str, Dict[str, str]] = {
    "en": {
        "zodiac_liuhe": "Your zodiac animals are secret allies — one of the six harmony pairs in Chinese astrology. This bond protects you in hard times.",
        "zodiac_sanhe": "Your zodiac animals belong to the same harmony triangle. You instinctively pull in the same direction.",
        "zodiac_chong": "Your zodiac animals sit directly opposite each other. That means sparks — passion when it works, friction when it does not.",
        "spouse_harmony": "Here is the rare part: your Day branches — the marriage palace itself — are in harmony. That is what old masters looked for first.",
        "spouse_clash": "Your marriage palaces clash, which means you will need to give each other room when tempers rise.",
        "dm_generate_ab": "{a} feeds {b} the way {ea} feeds {eb}. One of you naturally gives the other energy.",
        "dm_generate_ba": "{b} feeds {a} the way {eb} feeds {ea}. One of you naturally gives the other energy.",
        "dm_same": "You are the same element. You understand each other without words — just do not compete over the same ground.",
        "dm_control_ab": "{ea} controls {eb} here, so one of you tends to steer. Balance comes from letting go sometimes.",
        "dm_control_ba": "{eb} controls {ea} here, so one of you tends to steer. Balance comes from letting go sometimes.",
        "complement_ab": "And listen to this: the element that fills one chart is exactly what the other chart is missing. You complete each other — literally.",
        "complement_ba": "And listen to this: the element that fills one chart is exactly what the other chart is missing. You complete each other — literally.",
    },
    "es": {
        "zodiac_liuhe": "Sus animales del zodiaco son aliados secretos: una de las seis parejas de armonía de la astrología china. Ese vínculo los protege en los momentos difíciles.",
        "zodiac_sanhe": "Sus animales pertenecen al mismo triángulo de armonía. Por instinto, tiran en la misma dirección.",
        "zodiac_chong": "Sus animales están directamente opuestos. Eso significa chispas: pasión cuando funciona, fricción cuando no.",
        "spouse_harmony": "Y aquí viene lo raro: sus ramas del Día, el palacio del matrimonio, están en armonía. Eso es lo primero que buscaban los antiguos maestros.",
        "spouse_clash": "Sus palacios del matrimonio chocan: tendrán que darse espacio cuando suban los ánimos.",
        "dm_generate_ab": "{a} alimenta a {b} como {ea} alimenta a {eb}. Uno de ustedes le da energía al otro de forma natural.",
        "dm_generate_ba": "{b} alimenta a {a} como {eb} alimenta a {ea}. Uno de ustedes le da energía al otro de forma natural.",
        "dm_same": "Son el mismo elemento. Se entienden sin palabras; solo no compitan por el mismo terreno.",
        "dm_control_ab": "Aquí {ea} controla a {eb}, así que uno tiende a llevar el timón. El equilibrio llega cuando aprende a soltarlo.",
        "dm_control_ba": "Aquí {eb} controla a {ea}, así que uno tiende a llevar el timón. El equilibrio llega cuando aprende a soltarlo.",
        "complement_ab": "Y escuchen esto: el elemento que abunda en una carta es justo el que le falta a la otra. Se completan, literalmente.",
        "complement_ba": "Y escuchen esto: el elemento que abunda en una carta es justo el que le falta a la otra. Se completan, literalmente.",
    },
    "pt": {
        "zodiac_liuhe": "Os animais do zodíaco de vocês são aliados secretos: um dos seis pares de harmonia da astrologia chinesa. Esse laço protege vocês nos momentos difíceis.",
        "zodiac_sanhe": "Os animais de vocês pertencem ao mesmo triângulo de harmonia. Por instinto, vocês puxam na mesma direção.",
        "zodiac_chong": "Os animais de vocês estão em oposição direta. Isso significa faíscas: paixão quando funciona, atrito quando não.",
        "spouse_harmony": "E aqui vem a parte rara: os ramos do Dia de vocês, o próprio palácio do casamento, estão em harmonia. Era isso que os antigos mestres procuravam primeiro.",
        "spouse_clash": "Os palácios do casamento de vocês se chocam: será preciso dar espaço um ao outro quando os ânimos esquentarem.",
        "dm_generate_ab": "{a} alimenta {b} como {ea} alimenta {eb}. Um de vocês naturalmente dá energia ao outro.",
        "dm_generate_ba": "{b} alimenta {a} como {eb} alimenta {ea}. Um de vocês naturalmente dá energia ao outro.",
        "dm_same": "Vocês são o mesmo elemento. Entendem-se sem palavras; só não disputem o mesmo terreno.",
        "dm_control_ab": "Aqui {ea} controla {eb}, então um de vocês tende a segurar o leme. O equilíbrio vem de soltá-lo às vezes.",
        "dm_control_ba": "Aqui {eb} controla {ea}, então um de vocês tende a segurar o leme. O equilíbrio vem de soltá-lo às vezes.",
        "complement_ab": "E escutem isso: o elemento que transborda em um mapa é exatamente o que falta no outro. Vocês se completam, literalmente.",
        "complement_ba": "E escutem isso: o elemento que transborda em um mapa é exatamente o que falta no outro. Vocês se completam, literalmente.",
    },
}

_OPENING = {
    "en": "Two birthdays: {da} and {db}. Let's see what Chinese astrology says about you two.",
    "es": "Dos fechas de nacimiento: {da} y {db}. Veamos qué dice la astrología china sobre ustedes dos.",
    "pt": "Duas datas de nascimento: {da} e {db}. Vamos ver o que a astrologia chinesa diz sobre vocês dois.",
}

_DM_INTRO = {
    "en": "One of you is {a}, the other is {b}.",
    "es": "Uno de ustedes es {a}, el otro es {b}.",
    "pt": "Um de vocês é {a}, o outro é {b}.",
}

_SCORE_LINE = {
    "en": "Overall compatibility: {score} out of 100.",
    "es": "Compatibilidad total: {score} de 100.",
    "pt": "Compatibilidade geral: {score} de 100.",
}

_VERDICT = {
    "en": {
        "high": "That is a rare match. Do not let this one go.",
        "mid": "A solid match — the kind that grows stronger the more you build together.",
        "low": "A challenging match, but challenge is not a verdict. It is a to-do list.",
    },
    "es": {
        "high": "Es una unión rara. No dejen ir esto.",
        "mid": "Una unión sólida, de las que se fortalecen cuanto más construyen juntos.",
        "low": "Una unión desafiante, pero un desafío no es una sentencia: es una lista de tareas.",
    },
    "pt": {
        "high": "É uma combinação rara. Não deixem isso escapar.",
        "mid": "Uma combinação sólida, daquelas que ficam mais fortes quanto mais vocês constroem juntos.",
        "low": "Uma combinação desafiadora, mas desafio não é sentença: é uma lista de tarefas.",
    },
}

_CTA = {
    "en": "Send this to your person, and drop both your birth dates in the comments for a free reading.",
    "es": "Envíale esto a tu persona, y dejen sus dos fechas de nacimiento en los comentarios para una lectura gratis.",
    "pt": "Envie isto para a sua pessoa, e deixem as duas datas de nascimento nos comentários para uma leitura grátis.",
}


def generate_compat_script(result: CompatResult, lang: str = "en") -> str:
    """合婚解读口播文案（三语模板）"""
    check_lang(lang)
    a, b = result.chart_a, result.chart_b
    dm_a = _day_master_phrase(a, lang)
    dm_b = _day_master_phrase(b, lang)
    names = ELEMENT_NAMES[lang]
    fmt = {
        "a": dm_a, "b": dm_b,
        "ea": names[a.day.stem_element], "eb": names[b.day.stem_element],
    }

    parts = [
        _OPENING[lang].format(da=format_date(a.birth_time, lang),
                              db=format_date(b.birth_time, lang)),
        _DM_INTRO[lang].format(a=dm_a, b=dm_b),
    ]
    for fact in result.facts:
        if fact in _FACT_PHRASES[lang]:
            parts.append(_FACT_PHRASES[lang][fact].format(**fmt))
    parts.append(_SCORE_LINE[lang].format(score=result.score))
    band = "high" if result.score >= 75 else ("mid" if result.score >= 55 else "low")
    parts.append(_VERDICT[lang][band])
    parts.append(_CTA[lang])
    return "\n\n".join(parts)


def generate_compat_content(result: CompatResult, use_llm: bool = True,
                            lang: str = "en") -> str:
    """合婚文案：LLM 优先（带完整关系数据），失败降级为三语模板"""
    check_lang(lang)
    if use_llm:
        from .script_writer import _try_llm
        a, b = result.chart_a, result.chart_b
        data = {
            "content_type": "couple compatibility reading (entertainment)",
            "person_a": {"birth": a.birth_time.strftime("%Y-%m-%d %H:%M"),
                         "day_master": a.day_master_english, "zodiac": a.zodiac_animal},
            "person_b": {"birth": b.birth_time.strftime("%Y-%m-%d %H:%M"),
                         "day_master": b.day_master_english, "zodiac": b.zodiac_animal},
            "relations": result.facts,
            "score": f"{result.score}/100",
            "instruction": "End with: send this to your person + comment both birth dates.",
        }
        content = _try_llm(str(data), lang)
        if content:
            return content
    return generate_compat_script(result, lang)


if __name__ == "__main__":
    from datetime import datetime
    from .calculator import calculate_bazi

    a = calculate_bazi(datetime(1995, 8, 17, 14, 30))
    b = calculate_bazi(datetime(1997, 2, 11, 8, 0))
    r = analyze_compatibility(a, b)
    print(f"score={r.score} facts={r.facts}\n")
    print(generate_compat_script(r, "en"))
