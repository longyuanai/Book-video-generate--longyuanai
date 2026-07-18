"""
出海八字短视频文案生成（多语言：英/西/葡）。

两类内容：
1. 个人命盘解读（chart reading）—— 输入出生日期
2. 生肖每日运势（zodiac daily fortune）—— 系列化批量内容

均为「LLM 优先、内置母语模板兜底」，离线也能出片。
"""

import hashlib
from datetime import datetime, date as date_type
from typing import Optional

from .calculator import BaziChart, BRANCH_ANIMAL, BRANCH_ELEMENT, STEMS
from .locales import (ANIMAL_NAMES, DAY_MASTER_READINGS, ELEMENT_NAMES,
                      ELEMENT_TIPS, LANGUAGE_NAMES, POLARITY_NAMES, check_lang)

_MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "pt": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
           "agosto", "setembro", "outubro", "novembro", "dezembro"],
}


def format_date(d: datetime, lang: str) -> str:
    """按语言习惯格式化日期"""
    if lang == "en":
        return d.strftime("%B %d, %Y")
    months = _MONTHS[lang]
    return f"{d.day} de {months[d.month - 1]} de {d.year}"


def _day_master_phrase(chart: BaziChart, lang: str) -> str:
    """日主的本地化说法，如 'Yang Metal' / 'Metal Yang'"""
    i = chart.day.stem_index
    polarity = POLARITY_NAMES[lang][["Yang", "Yin"][i % 2]]
    element = ELEMENT_NAMES[lang][chart.day.stem_element]
    if lang == "en":
        return f"{polarity} {element}"
    return f"{element} {polarity}"


def _current_luck_element(chart: BaziChart) -> Optional[str]:
    """当前所行大运的天干五行（未排大运或未起运则返回 None）"""
    if not chart.luck_pillars:
        return None
    age = (datetime.now() - chart.birth_time).days / 365.25
    for lp in chart.luck_pillars:
        if lp.start_age <= age < lp.start_age + 10:
            return lp.pillar.stem_element
    return None


# ---------------------------------------------------------------------------
# 个人命盘模板（三语）
# ---------------------------------------------------------------------------

def _template_en(chart: BaziChart) -> str:
    dm = _day_master_phrase(chart, "en")
    dominant = chart.dominant_element()
    missing = chart.missing_elements()
    tips = ELEMENT_TIPS["en"]
    parts = [
        f"If you were born on {format_date(chart.birth_time, 'en')}, this is what your "
        f"Chinese birth chart says about you.",
        f"In BaZi, the ancient Chinese art of destiny, your Day Master is {dm}. "
        f"{DAY_MASTER_READINGS['en'][chart.day_master]}",
        f"Your chart is dominated by the {dominant} element. That means your life "
        f"theme is about {tips[dominant][0]}.",
    ]
    if missing:
        m = missing[0]
        parts.append(
            f"But here is the interesting part. Your chart is missing the {m} element. "
            f"{m} stands for {tips[m][0]}. So this year, focus on one thing: {tips[m][1]}.")
    else:
        parts.append("And here is the rare part. All five elements appear in your chart. "
                     "That is a sign of balance most people do not have.")
    luck = _current_luck_element(chart)
    if luck:
        parts.append(f"Right now you are also walking through a {ELEMENT_NAMES['en'][luck]} "
                     f"decade of luck, which quietly pushes you toward {tips[luck][0]}.")
    parts.append(f"You were also born in the year of the {chart.zodiac_animal}, which adds "
                 f"another layer to your story.")
    parts.append("If this sounds like you, follow for more, and drop your birth date in the "
                 "comments for a free reading.")
    return "\n\n".join(parts)


def _template_es(chart: BaziChart) -> str:
    dm = _day_master_phrase(chart, "es")
    dominant = chart.dominant_element()
    missing = chart.missing_elements()
    tips = ELEMENT_TIPS["es"]
    names = ELEMENT_NAMES["es"]
    animal = ANIMAL_NAMES["es"][chart.zodiac_animal]
    parts = [
        f"Si naciste el {format_date(chart.birth_time, 'es')}, esto es lo que dice tu "
        f"carta astral china sobre ti.",
        f"En el BaZi, el antiguo arte chino del destino, tu Maestro del Día es {dm}. "
        f"{DAY_MASTER_READINGS['es'][chart.day_master]}",
        f"Tu carta está dominada por el elemento {names[dominant]}. Eso significa que el "
        f"tema de tu vida es {tips[dominant][0]}.",
    ]
    if missing:
        m = missing[0]
        parts.append(
            f"Pero aquí viene lo interesante. A tu carta le falta el elemento {names[m]}. "
            f"{names[m]} representa {tips[m][0]}. Así que este año, enfócate en una sola "
            f"cosa: {tips[m][1]}.")
    else:
        parts.append("Y aquí viene lo más raro. Los cinco elementos aparecen en tu carta. "
                     "Es una señal de equilibrio que muy poca gente tiene.")
    luck = _current_luck_element(chart)
    if luck:
        parts.append(f"Además, ahora mismo estás atravesando una década de suerte de "
                     f"{names[luck]}, que en silencio te empuja hacia {tips[luck][0]}.")
    parts.append(f"También naciste en el año del {animal}, que añade otra capa a tu historia.")
    parts.append("Si esto suena como tú, sígueme para más, y deja tu fecha de nacimiento "
                 "en los comentarios para una lectura gratis.")
    return "\n\n".join(parts)


def _template_pt(chart: BaziChart) -> str:
    dm = _day_master_phrase(chart, "pt")
    dominant = chart.dominant_element()
    missing = chart.missing_elements()
    tips = ELEMENT_TIPS["pt"]
    names = ELEMENT_NAMES["pt"]
    animal = ANIMAL_NAMES["pt"][chart.zodiac_animal]
    parts = [
        f"Se você nasceu em {format_date(chart.birth_time, 'pt')}, é isso que o seu "
        f"mapa astral chinês diz sobre você.",
        f"No BaZi, a antiga arte chinesa do destino, o seu Mestre do Dia é {dm}. "
        f"{DAY_MASTER_READINGS['pt'][chart.day_master]}",
        f"Seu mapa é dominado pelo elemento {names[dominant]}. Isso significa que o tema "
        f"da sua vida é {tips[dominant][0]}.",
    ]
    if missing:
        m = missing[0]
        parts.append(
            f"Mas aqui vem a parte interessante. Falta no seu mapa o elemento {names[m]}. "
            f"{names[m]} representa {tips[m][0]}. Então este ano, foque em uma única "
            f"coisa: {tips[m][1]}.")
    else:
        parts.append("E aqui vem a parte rara. Os cinco elementos aparecem no seu mapa. "
                     "É um sinal de equilíbrio que pouquíssimas pessoas têm.")
    luck = _current_luck_element(chart)
    if luck:
        parts.append(f"Além disso, agora mesmo você está atravessando uma década de sorte "
                     f"de {names[luck]}, que silenciosamente te empurra para {tips[luck][0]}.")
    parts.append(f"Você também nasceu no ano do {animal}, o que adiciona mais uma camada "
                 f"à sua história.")
    parts.append("Se isso soa como você, siga para ver mais, e deixe sua data de nascimento "
                 "nos comentários para uma leitura grátis.")
    return "\n\n".join(parts)


_TEMPLATES = {"en": _template_en, "es": _template_es, "pt": _template_pt}


# ---------------------------------------------------------------------------
# 生肖每日运势模板（三语）
# ---------------------------------------------------------------------------

# 每语言 4 组可轮换的建议句式，按 (日期, 生肖) 哈希取样，避免 12 条视频雷同
_FORTUNE_LINES = {
    "en": [
        "Today rewards patience. The thing you are rushing will land better tomorrow.",
        "An unexpected conversation opens a door today. Say yes before you overthink it.",
        "Money moves in your favor today, but only if you finish something you started.",
        "Someone is watching how you handle pressure today. Handle it with grace.",
        "Today is for quiet progress. One small step now saves you a big detour later.",
    ],
    "es": [
        "Hoy la paciencia da frutos. Eso que estás apurando saldrá mejor mañana.",
        "Una conversación inesperada te abre una puerta hoy. Di que sí antes de pensarlo demasiado.",
        "El dinero se mueve a tu favor hoy, pero solo si terminas algo que empezaste.",
        "Alguien observa cómo manejas la presión hoy. Manéjala con elegancia.",
        "Hoy es para el progreso silencioso. Un paso pequeño ahora te ahorra un gran desvío después.",
    ],
    "pt": [
        "Hoje a paciência dá frutos. Aquilo que você está apressando vai sair melhor amanhã.",
        "Uma conversa inesperada abre uma porta hoje. Diga sim antes de pensar demais.",
        "O dinheiro se move a seu favor hoje, mas só se você terminar algo que começou.",
        "Alguém está observando como você lida com a pressão hoje. Lide com elegância.",
        "Hoje é dia de progresso silencioso. Um pequeno passo agora evita um grande desvio depois.",
    ],
}

_FORTUNE_INTRO = {
    "en": "{animal}, this is your Chinese fortune for {date}.",
    "es": "{animal}, este es tu horóscopo chino para el {date}.",
    "pt": "{animal}, este é o seu horóscopo chinês para {date}.",
}

_FORTUNE_ELEMENT = {
    "en": "In BaZi, your sign carries the {element} element, so your natural strength is {theme}.",
    "es": "En el BaZi, tu signo lleva el elemento {element}, así que tu fuerza natural es {theme}.",
    "pt": "No BaZi, seu signo carrega o elemento {element}, então sua força natural é {theme}.",
}

_FORTUNE_CTA = {
    "en": "Follow so you never miss your sign, and comment your birth date for a free personal reading.",
    "es": "Sígueme para no perderte tu signo, y comenta tu fecha de nacimiento para una lectura personal gratis.",
    "pt": "Siga para não perder o seu signo, e comente sua data de nascimento para uma leitura pessoal grátis.",
}


def zodiac_branch_index(animal: str) -> int:
    return BRANCH_ANIMAL.index(animal)


def _template_zodiac(animal: str, day: date_type, lang: str) -> str:
    branch = zodiac_branch_index(animal)
    element = BRANCH_ELEMENT[branch]
    theme = ELEMENT_TIPS[lang][element][0]
    animal_local = ANIMAL_NAMES[lang][animal]
    # 用 (日期, 生肖) 做确定性取样：同一天 12 条各不相同，隔天轮换
    seed = int(hashlib.md5(f"{day}{animal}".encode()).hexdigest(), 16)
    pool = _FORTUNE_LINES[lang]
    line1 = pool[seed % len(pool)]
    line2 = pool[(seed // 7 + 3) % len(pool)]
    if line2 == line1:
        line2 = pool[(seed % len(pool) + 1) % len(pool)]
    date_str = format_date(datetime(day.year, day.month, day.day), lang)
    return "\n\n".join([
        _FORTUNE_INTRO[lang].format(animal=animal_local, date=date_str),
        _FORTUNE_ELEMENT[lang].format(element=ELEMENT_NAMES[lang][element], theme=theme),
        line1,
        line2,
        _FORTUNE_CTA[lang],
    ])


# ---------------------------------------------------------------------------
# LLM 生成
# ---------------------------------------------------------------------------

LLM_SYSTEM_PROMPT = """You are a charismatic BaZi (Chinese Four Pillars astrology) content creator \
for TikTok and YouTube Shorts, speaking to an overseas audience curious about Chinese metaphysics.

## Requirements
- Write a NARRATION SCRIPT in {language}, 130-170 words, for a 45-70 second video.
- Structure: (1) a scroll-stopping hook in the first line, (2) explain the chart in simple, \
vivid language — no jargon without a one-line explanation, (3) one practical takeaway, \
(4) a short call-to-action ending (follow / comment your birth date).
- Tone: warm, confident, a little mysterious, never doom-y. This is entertainment and \
self-reflection, NOT medical, legal or financial advice.
- Plain text only: no emojis, no hashtags, no timestamps, no stage directions, no markdown.
- Use short sentences. They will be read aloud by a TTS voice and shown as subtitles.

Write the script for the chart data the user provides."""


def _try_llm(message: str, lang: str) -> Optional[str]:
    try:
        from llm import LLMClient
        client = LLMClient()
        response = client.chat(
            message, system_prompt=LLM_SYSTEM_PROMPT.format(language=LANGUAGE_NAMES[lang]))
        if not response.get("error"):
            content = (response.get("content") or "").strip()
            if 60 <= len(content.split()) <= 400:
                return content
        print("LLM 文案生成失败，使用内置模板。")
    except Exception as e:
        print(f"LLM 调用异常（{e}），使用内置模板。")
    return None


def generate_bazi_script(chart: BaziChart, use_llm: bool = True, lang: str = "en",
                         extra_instruction: Optional[str] = None) -> str:
    """
    生成个人命盘口播文案。

    Args:
        chart: 排好的八字命盘
        use_llm: 是否尝试调用 LLM（失败自动降级为模板）
        lang: 目标语言 en / es / pt
        extra_instruction: 追加给 LLM 的额外要求（如目标平台、语气）
    """
    check_lang(lang)
    if use_llm:
        gods = chart.ten_gods()
        chart_data = {
            "birth_time": chart.birth_time.strftime("%Y-%m-%d %H:%M"),
            "pillars": {k: f"{p.hanzi} ({p.english()})" for k, p in chart.pillars.items()},
            "ten_gods": {k: f"{v['stem'][1]} / {v['branch'][1]}" for k, v in gods.items()},
            "day_master": chart.day_master_english,
            "zodiac": chart.zodiac_animal,
            "five_elements": chart.element_counts(),
            "missing_elements": chart.missing_elements(),
        }
        if chart.luck_pillars:
            chart_data["luck_pillars"] = [
                f"age {lp.age_range()}: {lp.pillar.hanzi} ({lp.pillar.english()})"
                for lp in chart.luck_pillars[:4]]
        message = str(chart_data)
        if extra_instruction:
            message += f"\n\nExtra instruction: {extra_instruction}"
        content = _try_llm(message, lang)
        if content:
            return content
    return _TEMPLATES[lang](chart)


def generate_zodiac_script(animal: str, day: date_type, use_llm: bool = True,
                           lang: str = "en") -> str:
    """生成某生肖某日的每日运势文案（系列内容）"""
    check_lang(lang)
    if animal not in BRANCH_ANIMAL:
        raise ValueError(f"未知生肖 '{animal}'，可选: {', '.join(BRANCH_ANIMAL)}")
    if use_llm:
        branch = zodiac_branch_index(animal)
        message = str({
            "content_type": "zodiac daily fortune (entertainment)",
            "zodiac_animal": animal,
            "branch_element": BRANCH_ELEMENT[branch],
            "date": str(day),
        })
        content = _try_llm(message, lang)
        if content:
            return content
    return _template_zodiac(animal, day, lang)


if __name__ == "__main__":
    from .calculator import calculate_bazi

    chart = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="female")
    for lang in ("en", "es", "pt"):
        print(f"\n======== {lang} ========")
        print(_TEMPLATES[lang](chart))
    print("\n======== zodiac (en) ========")
    print(_template_zodiac("Dragon", date_type(2026, 7, 18), "en"))
