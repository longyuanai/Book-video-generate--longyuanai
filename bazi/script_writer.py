"""
出海八字短视频英文文案生成。

Generates an English narration script for a BaZi (Chinese astrology)
short video, aimed at TikTok / YouTube Shorts / Instagram Reels audiences.

优先调用 LLM 生成个性化文案；LLM 不可用时自动降级为内置英文模板，
保证整条流水线离线也能跑通。
"""

from typing import Optional

from .calculator import BaziChart

# 日主（日元）性格解读 —— 模板模式使用
DAY_MASTER_READINGS = {
    "甲": "Like a tall tree, you grow straight toward your goals. You are principled, "
          "a natural leader, and you refuse to bend even when life pushes hard.",
    "乙": "Like a climbing vine, you are flexible and quietly persistent. You adapt "
          "where others break, and your gentleness is actually your superpower.",
    "丙": "Like the sun itself, you light up every room you walk into. You are warm, "
          "generous and expressive — people are drawn to your energy.",
    "丁": "Like candlelight, you burn softly but never go out. You are perceptive, "
          "thoughtful, and you see details that everyone else misses.",
    "戊": "Like a mountain, you are solid and dependable. People lean on you in a "
          "crisis, and your loyalty runs deeper than you ever say out loud.",
    "己": "Like fertile soil, you nurture everything you touch. You are patient, "
          "tolerant, and you quietly help people grow without asking for credit.",
    "庚": "Like raw steel, you are decisive and fearless. You cut through problems "
          "directly, and you'd rather hear a hard truth than a soft lie.",
    "辛": "Like fine jewelry, you are refined and precise. You care about quality in "
          "everything — your work, your words, and the people you keep close.",
    "壬": "Like the open ocean, you are ambitious and free-spirited. Your mind never "
          "stops moving, and you were never meant to stay in one small pond.",
    "癸": "Like gentle rain, you are intuitive and quietly powerful. You sense what "
          "people feel before they say it, and you nourish everyone around you.",
}

# 五行行动建议 —— 用于「所缺五行」的内容钩子
ELEMENT_TIPS = {
    "Wood": "growth, planning and starting new things — say yes to that new project",
    "Fire": "visibility and passion — stop hiding, let people see what you can do",
    "Earth": "stability and trust — build routines and keep your promises to yourself",
    "Metal": "discipline and boundaries — learn to say no and finish what you start",
    "Water": "wisdom and flow — read more, travel more, and let things move",
}

LLM_SYSTEM_PROMPT = """You are a charismatic BaZi (Chinese Four Pillars astrology) content creator \
for TikTok and YouTube Shorts, speaking to a Western audience that is curious about Chinese metaphysics.

## Requirements
- Write a NARRATION SCRIPT in English, 130-170 words, for a 45-70 second video.
- Structure: (1) a scroll-stopping hook in the first line, (2) explain the chart in simple, \
vivid language — no jargon without a one-line explanation, (3) one practical takeaway, \
(4) a short call-to-action ending (follow / comment your birth date).
- Tone: warm, confident, a little mysterious, never doom-y. This is entertainment and \
self-reflection, NOT medical, legal or financial advice.
- Plain text only: no emojis, no hashtags, no timestamps, no stage directions, no markdown.
- Use short sentences. They will be read aloud by a TTS voice and shown as subtitles.

Write the script for the chart data the user provides."""


def _template_script(chart: BaziChart) -> str:
    """离线英文模板：不依赖任何外部 API"""
    dm = chart.day_master
    reading = DAY_MASTER_READINGS[dm]
    dominant = chart.dominant_element()
    missing = chart.missing_elements()

    lines = [
        f"If you were born on {chart.birth_time:%B %d, %Y}, this is what your Chinese "
        f"birth chart says about you.",
        "",
        f"In BaZi, the ancient Chinese art of destiny, your Day Master is "
        f"{chart.day_master_english.split(' (')[0]}. {reading}",
        "",
        f"Your chart is dominated by the {dominant} element. That means your life "
        f"theme is about {ELEMENT_TIPS[dominant].split(' — ')[0]}.",
    ]

    if missing:
        m = missing[0]
        lines += [
            "",
            f"But here is the interesting part. Your chart is missing the {m} element. "
            f"{m} stands for {ELEMENT_TIPS[m].split(' — ')[0]}. "
            f"So this year, focus on one thing: {ELEMENT_TIPS[m].split(' — ')[1]}.",
        ]
    else:
        lines += [
            "",
            "And here is the rare part. All five elements appear in your chart. "
            "That is a sign of balance most people do not have.",
        ]

    lines += [
        "",
        f"You were also born in the year of the {chart.zodiac_animal}, which adds "
        f"another layer to your story.",
        "",
        "If this sounds like you, follow for more, and drop your birth date in the "
        "comments for a free reading.",
    ]
    return "\n".join(lines)


def generate_bazi_script(chart: BaziChart, use_llm: bool = True,
                         extra_instruction: Optional[str] = None) -> str:
    """
    生成英文口播文案。

    Args:
        chart: 排好的八字命盘
        use_llm: 是否尝试调用 LLM（失败自动降级为模板）
        extra_instruction: 追加给 LLM 的额外要求（如目标平台、语气）
    """
    if use_llm:
        try:
            from llm import LLMClient
            chart_data = {
                "birth_time": chart.birth_time.strftime("%Y-%m-%d %H:%M"),
                "pillars": {k: f"{p.hanzi} ({p.english()})" for k, p in chart.pillars.items()},
                "day_master": chart.day_master_english,
                "zodiac": chart.zodiac_animal,
                "five_elements": chart.element_counts(),
                "missing_elements": chart.missing_elements(),
            }
            message = str(chart_data)
            if extra_instruction:
                message += f"\n\nExtra instruction: {extra_instruction}"
            client = LLMClient()
            response = client.chat(message, system_prompt=LLM_SYSTEM_PROMPT)
            if not response.get("error"):
                content = (response.get("content") or "").strip()
                # 长度合理才采用，防止 API 返回空串或异常内容
                if 60 <= len(content.split()) <= 400:
                    return content
            print("LLM 文案生成失败，使用内置英文模板。")
        except Exception as e:
            print(f"LLM 调用异常（{e}），使用内置英文模板。")
    return _template_script(chart)


if __name__ == "__main__":
    from datetime import datetime
    from .calculator import calculate_bazi

    chart = calculate_bazi(datetime(1995, 8, 17, 14, 30))
    print(chart.summary_text())
    print()
    print(_template_script(chart))
