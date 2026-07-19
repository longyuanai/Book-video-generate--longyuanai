"""
PDF 命书报告生成 —— 付费交付物（三语）。

一页 A4 深色设计：四柱命盘（五行配色 + 十神）、日主解读、五行分布、
藏干、神煞、大运时间轴、娱乐声明。配合视频 CTA
（评论区留生日 -> 私信发详细报告）形成变现闭环。
"""

from pathlib import Path
from typing import Dict

from .calculator import BaziChart, ELEMENT_CN, SHENSHA_INFO
from .locales import (DAY_MASTER_READINGS, ELEMENT_NAMES, ELEMENT_TIPS,
                      SHENSHA_PHRASES, check_lang)
from .script_writer import _day_master_phrase, format_date

# 深色主题（RGB）
BG = (16, 14, 28)
CARD = (28, 25, 46)
GOLD = (214, 178, 106)
WHITE = (238, 238, 240)
DIM = (150, 150, 160)
ELEMENT_COLOR = {
    "Wood": (102, 187, 106), "Fire": (239, 83, 80), "Earth": (255, 183, 77),
    "Metal": (210, 210, 214), "Water": (79, 195, 247),
}

_L: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "BAZI DESTINY REPORT", "pillars": "Your Four Pillars",
        "day_master": "Your Day Master", "elements": "Five Elements Balance",
        "hidden": "Hidden Stems", "stars": "Special Stars",
        "luck": "Luck Pillars (10-Year Cycles)", "age": "Age",
        "missing": "Missing element: {e} — focus: {tip}",
        "disclaimer": "For entertainment and self-reflection only. Not medical, legal or financial advice.",
        "cols": ["YEAR", "MONTH", "DAY", "HOUR"],
    },
    "es": {
        "title": "INFORME DE DESTINO BAZI", "pillars": "Tus Cuatro Pilares",
        "day_master": "Tu Maestro del Día", "elements": "Balance de los Cinco Elementos",
        "hidden": "Troncos Ocultos", "stars": "Estrellas Especiales",
        "luck": "Pilares de la Suerte (ciclos de 10 años)", "age": "Edad",
        "missing": "Elemento faltante: {e} — enfoque: {tip}",
        "disclaimer": "Solo para entretenimiento y autorreflexión. No es consejo médico, legal ni financiero.",
        "cols": ["AÑO", "MES", "DÍA", "HORA"],
    },
    "pt": {
        "title": "RELATÓRIO DE DESTINO BAZI", "pillars": "Seus Quatro Pilares",
        "day_master": "Seu Mestre do Dia", "elements": "Equilíbrio dos Cinco Elementos",
        "hidden": "Troncos Ocultos", "stars": "Estrelas Especiais",
        "luck": "Pilares da Sorte (ciclos de 10 anos)", "age": "Idade",
        "missing": "Elemento faltante: {e} — foco: {tip}",
        "disclaimer": "Apenas para entretenimento e autorreflexão. Não é aconselhamento médico, jurídico ou financeiro.",
        "cols": ["ANO", "MÊS", "DIA", "HORA"],
    },
}


def generate_report(chart: BaziChart, out_path: Path, font_path: Path,
                    lang: str = "en") -> Path:
    """生成一页 A4 PDF 命书，返回输出路径"""
    check_lang(lang)
    from fpdf import FPDF

    L = _L[lang]
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_font("msyh", fname=str(font_path))
    pdf.set_text_shaping(False)
    pdf.add_page()
    W, H = 210, 297

    # 背景
    pdf.set_fill_color(*BG)
    pdf.rect(0, 0, W, H, style="F")

    def text(x, y, s, size=11, color=WHITE, center_w=None):
        pdf.set_font("msyh", size=size)
        pdf.set_text_color(*color)
        if center_w is not None:
            pdf.set_xy(x, y)
            pdf.cell(center_w, size * 0.5, s, align="C")
        else:
            pdf.text(x, y, s)

    def heading(y, s):
        text(16, y, s, size=13, color=GOLD)
        pdf.set_draw_color(*GOLD)
        pdf.set_line_width(0.3)
        pdf.line(16, y + 2, W - 16, y + 2)

    # 标题
    text(0, 20, L["title"], size=20, color=GOLD, center_w=W)
    text(0, 29, format_date(chart.birth_time, lang) +
         chart.birth_time.strftime(" · %H:%M"), size=11, color=DIM, center_w=W)

    # ---- 四柱 ----
    heading(42, L["pillars"])
    gods = chart.ten_gods()
    col_w = (W - 32) / 4
    for i, (key, name) in enumerate(zip(("Year", "Month", "Day", "Hour"), L["cols"])):
        p = chart.pillars[key]
        x = 16 + i * col_w
        pdf.set_fill_color(*CARD)
        pdf.rect(x + 2, 47, col_w - 4, 46, style="F")
        text(x, 51, name, size=9, color=DIM, center_w=col_w)
        text(x, 57, p.hanzi[0], size=22,
             color=ELEMENT_COLOR[p.stem_element], center_w=col_w)
        text(x, 68, p.hanzi[1], size=22,
             color=ELEMENT_COLOR[p.branch_element], center_w=col_w)
        text(x, 81, p.pinyin, size=8, color=WHITE, center_w=col_w)
        god = gods[key]["stem"][1] if key != "Day" else "Day Master"
        text(x, 86.5, god, size=7, color=DIM, center_w=col_w)

    # ---- 日主解读 ----
    heading(101, L["day_master"] + f"  ·  {_day_master_phrase(chart, lang)} {chart.day_master}")
    pdf.set_font("msyh", size=10)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(16, 105)
    pdf.multi_cell(W - 32, 5.5, DAY_MASTER_READINGS[lang][chart.day_master])

    # ---- 五行分布 ----
    y0 = 131
    heading(y0, L["elements"])
    counts = chart.element_counts()
    bar_y = y0 + 5
    for e, c in counts.items():
        text(16, bar_y + 3.5, f"{ELEMENT_CN[e]} {ELEMENT_NAMES[lang][e]}", size=9)
        pdf.set_fill_color(*ELEMENT_COLOR[e])
        if c:
            pdf.rect(52, bar_y, c * 16, 4, style="F")
        text(52 + c * 16 + 3, bar_y + 3.5, str(c), size=9, color=DIM)
        bar_y += 7.5
    missing = chart.missing_elements()
    if missing:
        m = missing[0]
        text(16, bar_y + 3, L["missing"].format(
            e=ELEMENT_NAMES[lang][m], tip=ELEMENT_TIPS[lang][m][1]), size=9, color=GOLD)
        bar_y += 6

    # ---- 藏干 + 神煞 ----
    y0 = bar_y + 8
    heading(y0, L["hidden"] + " & " + L["stars"])
    hidden = chart.hidden_stems()
    text(16, y0 + 7, "  ".join(f"{k}: {''.join(v)}" for k, v in hidden.items()), size=9)
    yy = y0 + 13
    for cn, en, _meaning in chart.shensha():
        text(16, yy, f"★ {cn} {en}", size=9, color=GOLD)
        pdf.set_font("msyh", size=8)
        pdf.set_text_color(*DIM)
        pdf.set_xy(16, yy + 1.5)
        pdf.multi_cell(W - 32, 4, SHENSHA_PHRASES[lang][en])
        yy = pdf.get_y() + 4

    # ---- 大运 ----
    if chart.luck_pillars:
        heading(yy + 2, L["luck"])
        ly = yy + 8
        lx = 16
        for lp in chart.luck_pillars[:8]:
            pdf.set_fill_color(*CARD)
            pdf.rect(lx, ly, 20, 14, style="F")
            text(lx, ly + 5, lp.pillar.hanzi, size=10,
                 color=ELEMENT_COLOR[lp.pillar.stem_element], center_w=20)
            text(lx, ly + 11, lp.age_range(), size=6.5, color=DIM, center_w=20)
            lx += 22.2

    # ---- 声明 ----
    text(0, H - 10, L["disclaimer"], size=7, color=DIM, center_w=W)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path


if __name__ == "__main__":
    from datetime import datetime
    from .calculator import calculate_bazi

    chart = calculate_bazi(datetime(1995, 8, 17, 14, 30), gender="female")
    root = Path(__file__).resolve().parent.parent
    out = generate_report(chart, root / "appdata" / "report_test.pdf",
                          root / "resource" / "fonts" / "msyh.ttc", "en")
    print(f"报告已生成: {out} ({out.stat().st_size // 1024} KB)")
