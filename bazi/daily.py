"""
真·每日干支运势：按当天日柱（干支）与生肖地支的关系推算，而非通用建议池。

规则（娱乐向但有真实命理依据）：
- 计算当日日柱（1949-10-01 甲子日锚点，60 甲子循环）；
- 生肖地支 vs 当日日支：六合（贵人日）/ 三合（顺势日）/ 六冲（动荡日）/
  值日（聚光日）/ 其余（平稳日）；
- 幸运色取当日日干五行的对应色，幸运数字按（日期+生肖）确定性生成。

同一天 12 生肖各不相同，隔天自动变化——每天的内容是"真的今天"。
"""

import hashlib
from datetime import date as date_type, datetime
from typing import Dict

from .calculator import (BRANCH_ANIMAL, BRANCHES, Pillar, STEM_ELEMENT,
                         STEMS, _DAY_ANCHOR, _trine_group)
from .compatibility import _LIUHE
from .locales import ANIMAL_NAMES, ELEMENT_NAMES, check_lang
from .script_writer import format_date


def day_pillar_of(d: date_type) -> Pillar:
    """某公历日的日柱干支"""
    idx = (d - _DAY_ANCHOR).days % 60
    return Pillar(idx % 10, idx % 12)


def daily_relation(animal: str, d: date_type) -> str:
    """生肖与当日日支的关系: liuhe / sanhe / chong / same / neutral"""
    ab = BRANCH_ANIMAL.index(animal)
    db = day_pillar_of(d).branch_index
    if ab == db:
        return "same"
    if frozenset((ab, db)) in _LIUHE:
        return "liuhe"
    if abs(ab - db) == 6:
        return "chong"
    if _trine_group(ab) == _trine_group(db):
        return "sanhe"
    return "neutral"


# 五行幸运色（三语）
_LUCKY_COLORS = {
    "Wood": {"en": "green", "es": "verde", "pt": "verde"},
    "Fire": {"en": "red", "es": "rojo", "pt": "vermelho"},
    "Earth": {"en": "yellow", "es": "amarillo", "pt": "amarelo"},
    "Metal": {"en": "white and gold", "es": "blanco y dorado", "pt": "branco e dourado"},
    "Water": {"en": "blue", "es": "azul", "pt": "azul"},
}

# 关系 -> 运势基调句（每语言每基调 2 个变体，按日期轮换避免雷同）
_TONE_LINES = {
    "en": {
        "liuhe": [
            "Today's energy is your secret ally. A door opens through a person, not luck — say yes to that conversation.",
            "The day quietly works in your favor. Someone you already know holds the key to today's opportunity.",
        ],
        "sanhe": [
            "You ride the same current as today. Things click with less force — push the project you postponed.",
            "Momentum is on your side today. Start the thing; the follow-through will feel easier than usual.",
        ],
        "chong": [
            "Today clashes with your sign. Plans may shift under your feet — stay flexible and don't force decisions.",
            "A turbulence day. Delay big commitments if you can, and let sudden changes reroute you instead of rattle you.",
        ],
        "same": [
            "Today the spotlight finds you — the day pillar matches your sign. Be visible, but move deliberately.",
            "This is your day on the throne. Wins get louder and so do lessons. Show up, and mark the moment.",
        ],
        "neutral": [
            "A builder's day. No storms, no fireworks — which is exactly why one quiet consistent step compounds.",
            "Steady energy today. Perfect for finishing, organizing, and setting up tomorrow's win.",
        ],
    },
    "es": {
        "liuhe": [
            "La energía de hoy es tu aliada secreta. Una puerta se abre a través de una persona, no de la suerte: di que sí a esa conversación.",
            "El día trabaja en silencio a tu favor. Alguien que ya conoces tiene la llave de la oportunidad de hoy.",
        ],
        "sanhe": [
            "Hoy navegas la misma corriente del día. Todo encaja con menos esfuerzo: empuja ese proyecto que pospusiste.",
            "El impulso está de tu lado hoy. Empieza eso pendiente; te costará menos de lo habitual.",
        ],
        "chong": [
            "Hoy choca con tu signo. Los planes pueden moverse bajo tus pies: mantente flexible y no fuerces decisiones.",
            "Día de turbulencia. Aplaza los grandes compromisos si puedes, y deja que los cambios te redirijan en vez de sacudirte.",
        ],
        "same": [
            "Hoy el reflector te encuentra: el pilar del día coincide con tu signo. Hazte visible, pero muévete con intención.",
            "Es tu día en el trono. Los triunfos suenan más fuerte, y las lecciones también. Preséntate y marca el momento.",
        ],
        "neutral": [
            "Día de constructor. Sin tormentas ni fuegos artificiales: por eso mismo, un paso constante rinde el doble.",
            "Energía estable hoy. Perfecta para terminar, ordenar y preparar la victoria de mañana.",
        ],
    },
    "pt": {
        "liuhe": [
            "A energia de hoje é sua aliada secreta. Uma porta se abre através de uma pessoa, não da sorte: diga sim àquela conversa.",
            "O dia trabalha em silêncio a seu favor. Alguém que você já conhece tem a chave da oportunidade de hoje.",
        ],
        "sanhe": [
            "Hoje você navega na mesma corrente do dia. As coisas se encaixam com menos esforço: empurre aquele projeto adiado.",
            "O impulso está do seu lado hoje. Comece aquilo pendente; vai custar menos do que o normal.",
        ],
        "chong": [
            "Hoje se choca com o seu signo. Os planos podem se mover sob seus pés: mantenha-se flexível e não force decisões.",
            "Dia de turbulência. Adie grandes compromissos se puder, e deixe as mudanças te redirecionarem em vez de te abalarem.",
        ],
        "same": [
            "Hoje o holofote te encontra: o pilar do dia coincide com o seu signo. Seja visível, mas mova-se com intenção.",
            "É o seu dia no trono. As vitórias soam mais alto, e as lições também. Apareça e marque o momento.",
        ],
        "neutral": [
            "Dia de construtor. Sem tempestades nem fogos: e é exatamente por isso que um passo constante rende em dobro.",
            "Energia estável hoje. Perfeita para terminar, organizar e preparar a vitória de amanhã.",
        ],
    },
}

_INTRO = {
    "en": "{animal}, here is your fortune for {date} — {article} {element} {day_animal} day in the Chinese calendar.",
    "es": "{animal}, este es tu horóscopo para el {date}: un día de {day_animal} de {element} en el calendario chino.",
    "pt": "{animal}, este é o seu horóscopo para {date}: um dia de {day_animal} de {element} no calendário chinês.",
}

_LUCKY = {
    "en": "Your lucky color today is {color}, and your lucky number is {number}.",
    "es": "Tu color de la suerte hoy es el {color}, y tu número de la suerte es el {number}.",
    "pt": "Sua cor da sorte hoje é o {color}, e seu número da sorte é o {number}.",
}

_CTA = {
    "en": "Follow so you never miss your sign, and comment your birth date for a free personal reading.",
    "es": "Sígueme para no perderte tu signo, y comenta tu fecha de nacimiento para una lectura personal gratis.",
    "pt": "Siga para não perder o seu signo, e comente sua data de nascimento para uma leitura pessoal grátis.",
}


def daily_fortune(animal: str, d: date_type) -> Dict[str, object]:
    """当日运势结构化数据（供模板与 LLM 使用）"""
    if animal not in BRANCH_ANIMAL:
        raise ValueError(f"未知生肖 '{animal}'")
    dp = day_pillar_of(d)
    seed = int(hashlib.md5(f"{d}{animal}".encode()).hexdigest(), 16)
    return {
        "day_pillar": dp,
        "day_element": STEM_ELEMENT[dp.stem_index],
        "relation": daily_relation(animal, d),
        "lucky_number": seed % 9 + 1,
        "variant": seed // 9 % 2,
    }


def generate_daily_script(animal: str, d: date_type, lang: str = "en") -> str:
    """生成某生肖某日的干支运势文案（模板，三语）"""
    check_lang(lang)
    f = daily_fortune(animal, d)
    dp: Pillar = f["day_pillar"]
    element_local = ELEMENT_NAMES[lang][f["day_element"]]
    color = _LUCKY_COLORS[f["day_element"]][lang]

    intro_kwargs = dict(
        animal=ANIMAL_NAMES[lang][animal],
        date=format_date(datetime(d.year, d.month, d.day), lang),
        element=element_local,
        day_animal=ANIMAL_NAMES[lang][dp.animal])
    if lang == "en":
        intro_kwargs["article"] = "an" if element_local[0] in "AEIOU" else "a"

    return "\n\n".join([
        _INTRO[lang].format(**intro_kwargs),
        _TONE_LINES[lang][f["relation"]][f["variant"]],
        _LUCKY[lang].format(color=color, number=f["lucky_number"]),
        _CTA[lang],
    ])


if __name__ == "__main__":
    # 已知锚点：2000-01-01 为戊午日
    dp = day_pillar_of(date_type(2000, 1, 1))
    assert dp.hanzi == "戊午", dp.hanzi
    # 戊午日：马值日、鼠被冲、羊六合、虎三合
    d = date_type(2000, 1, 1)
    assert daily_relation("Horse", d) == "same"
    assert daily_relation("Rat", d) == "chong"
    assert daily_relation("Goat", d) == "liuhe"
    assert daily_relation("Tiger", d) == "sanhe"
    print(generate_daily_script("Horse", d, "en"))
    print("\ndaily self-check passed ✓")
