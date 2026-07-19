"""
流年运势：某公历年对 12 生肖的年度运势（如 2026 丙午火马年）。

规则（娱乐向）：生肖地支与流年地支的关系
- 值太岁（同支）：本命年，动荡与高光并存
- 冲太岁（对冲）：变动之年，宜主动求变
- 六合 / 三合：贵人年 / 顺势年
- 其余：平稳积累年

「What {year} means for your sign」是年初/年中天然的高搜索量选题。
"""

from typing import Dict, List

from .calculator import (BRANCH_ANIMAL, BRANCH_ELEMENT, Pillar, STEM_ELEMENT,
                         _trine_group)
from .compatibility import _LIUHE
from .locales import ANIMAL_NAMES, ELEMENT_NAMES, ELEMENT_TIPS, PUBLISH, check_lang


def year_pillar(year: int) -> Pillar:
    return Pillar((year - 4) % 10, (year - 4) % 12)


def year_relation(year: int, animal: str) -> str:
    """生肖与流年的关系: tai_sui / chong / liuhe / sanhe / neutral"""
    yb = year_pillar(year).branch_index
    ab = BRANCH_ANIMAL.index(animal)
    if ab == yb:
        return "tai_sui"
    if abs(ab - yb) == 6:
        return "chong"
    if frozenset((ab, yb)) in _LIUHE:
        return "liuhe"
    if _trine_group(ab) == _trine_group(yb):
        return "sanhe"
    return "neutral"


_YEAR_INTRO = {
    "en": "{animal}, this is what {year} — the year of the {element} {year_animal} — means for you.",
    "es": "{animal}, esto es lo que {year}, el año del {year_animal} de {element}, significa para ti.",
    "pt": "{animal}, é isso que {year}, o ano do {year_animal} de {element}, significa para você.",
}

_RELATION_LINES: Dict[str, Dict[str, str]] = {
    "en": {
        "tai_sui": "This is YOUR year on the throne. In Chinese astrology that means everything gets louder — the wins and the lessons. Move deliberately, mark the big moments, and do not coast.",
        "chong": "Your sign clashes with the year, and a clash year is a moving year. Job, city, relationship — change finds you anyway, so choose your changes before they choose you.",
        "liuhe": "Your sign is the secret ally of this year. Doors open quietly for you — through people, not luck. Say yes to introductions.",
        "sanhe": "Your sign rides the same current as this year. Things click into place with less force. This is the year to launch what you postponed.",
        "neutral": "For you this is a builder's year. No drama, no storm — which is exactly why quiet consistent moves will compound more than you expect.",
    },
    "es": {
        "tai_sui": "Este es TU año en el trono. En la astrología china eso significa que todo suena más fuerte: los triunfos y las lecciones. Muévete con intención y no te dejes llevar.",
        "chong": "Tu signo choca con el año, y un año de choque es un año de movimiento. Trabajo, ciudad, relación: el cambio te encontrará igual, así que elige tus cambios antes de que ellos te elijan.",
        "liuhe": "Tu signo es el aliado secreto de este año. Las puertas se abren en silencio para ti, a través de personas, no de la suerte. Di que sí a las presentaciones.",
        "sanhe": "Tu signo navega la misma corriente que este año. Las cosas encajan con menos esfuerzo. Este es el año para lanzar lo que pospusiste.",
        "neutral": "Para ti este es un año de constructor. Sin drama ni tormenta: por eso mismo, los pasos constantes y silenciosos rendirán más de lo que esperas.",
    },
    "pt": {
        "tai_sui": "Este é o SEU ano no trono. Na astrologia chinesa isso significa que tudo fica mais alto: as vitórias e as lições. Mova-se com intenção e não vá no piloto automático.",
        "chong": "Seu signo se choca com o ano, e ano de choque é ano de movimento. Trabalho, cidade, relacionamento: a mudança vai te encontrar de qualquer jeito, então escolha suas mudanças antes que elas escolham você.",
        "liuhe": "Seu signo é o aliado secreto deste ano. Portas se abrem em silêncio para você, através de pessoas, não de sorte. Diga sim às apresentações.",
        "sanhe": "Seu signo navega na mesma corrente deste ano. As coisas se encaixam com menos esforço. Este é o ano de lançar o que você adiou.",
        "neutral": "Para você este é um ano de construtor. Sem drama, sem tempestade: e é exatamente por isso que passos constantes e silenciosos vão render mais do que você espera.",
    },
}

_YEAR_ELEMENT_LINE = {
    "en": "The year runs on {element} energy, so whatever you do, {action}.",
    "es": "El año corre con energía de {element}, así que hagas lo que hagas, {action}.",
    "pt": "O ano corre com a energia de {element}, então faça o que fizer, {action}.",
}

_YEAR_CTA = {
    "en": "Follow for the rest of the signs, and comment your birth date for a free personal {year} reading.",
    "es": "Sígueme para ver el resto de los signos, y comenta tu fecha de nacimiento para una lectura personal de {year} gratis.",
    "pt": "Siga para ver os outros signos, e comente sua data de nascimento para uma leitura pessoal de {year} grátis.",
}


def generate_year_script(animal: str, year: int, lang: str = "en",
                         use_llm: bool = True) -> str:
    """某生肖某流年的运势文案"""
    check_lang(lang)
    if animal not in BRANCH_ANIMAL:
        raise ValueError(f"未知生肖 '{animal}'")
    yp = year_pillar(year)
    relation = year_relation(year, animal)

    if use_llm:
        from .script_writer import _try_llm
        content = _try_llm(str({
            "content_type": "annual zodiac forecast (entertainment)",
            "zodiac_animal": animal,
            "forecast_year": f"{year} ({yp.hanzi}, {STEM_ELEMENT[yp.stem_index]} {yp.animal})",
            "relation_to_year": relation,
            "sign_element": BRANCH_ELEMENT[BRANCH_ANIMAL.index(animal)],
        }), lang)
        if content:
            return content

    names = ELEMENT_NAMES[lang]
    year_element = STEM_ELEMENT[yp.stem_index]
    return "\n\n".join([
        _YEAR_INTRO[lang].format(
            animal=ANIMAL_NAMES[lang][animal], year=year,
            element=names[year_element],
            year_animal=ANIMAL_NAMES[lang][yp.animal]),
        _RELATION_LINES[lang][relation],
        _YEAR_ELEMENT_LINE[lang].format(
            element=names[year_element],
            action=ELEMENT_TIPS[lang][year_element][1]),
        _YEAR_CTA[lang].format(year=year),
    ])


def build_year_publish_kit(animal: str, year: int, lang: str = "en") -> Dict[str, object]:
    """流年运势视频发布素材"""
    check_lang(lang)
    yp = year_pillar(year)
    animal_local = ANIMAL_NAMES[lang][animal]
    year_animal = ANIMAL_NAMES[lang][yp.animal]
    titles = {
        "en": f"{animal_local} in {year} 🔮 Year of the {year_animal} Forecast",
        "es": f"{animal_local} en {year} 🔮 Predicción del año del {year_animal}",
        "pt": f"{animal_local} em {year} 🔮 Previsão do ano do {year_animal}",
    }
    descriptions = {
        "en": f"What {year}, the year of the {year_animal}, holds for the {animal_local} in Chinese astrology. Comment your birth date for a free personal {year} reading! 🔮",
        "es": f"Lo que {year}, el año del {year_animal}, trae para {animal_local} según la astrología china. ¡Comenta tu fecha de nacimiento para una lectura de {year} gratis! 🔮",
        "pt": f"O que {year}, o ano do {year_animal}, reserva para {animal_local} na astrologia chinesa. Comente sua data de nascimento para uma leitura de {year} grátis! 🔮",
    }
    return {
        "type": "year", "lang": lang,
        "title": titles[lang],
        "description": descriptions[lang],
        "hashtags": PUBLISH[lang]["hashtags"] + [f"#{year}"],
    }


if __name__ == "__main__":
    # 2026 丙午（火马）年
    assert year_pillar(2026).hanzi == "丙午"
    assert year_relation(2026, "Horse") == "tai_sui"
    assert year_relation(2026, "Rat") == "chong"
    assert year_relation(2026, "Goat") == "liuhe"    # 午未六合
    assert year_relation(2026, "Tiger") == "sanhe"   # 寅午戌
    assert year_relation(2026, "Rooster") == "neutral"
    print(generate_year_script("Horse", 2026, "en", use_llm=False))
    print("\nannual self-check passed ✓")
