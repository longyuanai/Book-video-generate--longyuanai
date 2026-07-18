"""
多语言资源：英语（en）、西班牙语（es）、葡萄牙语（pt，巴西）。

包含：日主性格解读、五行译名、五行主题与行动建议、发布素材文案。
拉美与巴西是玄学内容需求最大的海外市场之一，es/pt 均为母语级模板。
"""

# 五行译名
ELEMENT_NAMES = {
    "en": {"Wood": "Wood", "Fire": "Fire", "Earth": "Earth", "Metal": "Metal", "Water": "Water"},
    "es": {"Wood": "Madera", "Fire": "Fuego", "Earth": "Tierra", "Metal": "Metal", "Water": "Agua"},
    "pt": {"Wood": "Madeira", "Fire": "Fogo", "Earth": "Terra", "Metal": "Metal", "Water": "Água"},
}

# 生肖译名
ANIMAL_NAMES = {
    "en": {"Rat": "Rat", "Ox": "Ox", "Tiger": "Tiger", "Rabbit": "Rabbit", "Dragon": "Dragon",
           "Snake": "Snake", "Horse": "Horse", "Goat": "Goat", "Monkey": "Monkey",
           "Rooster": "Rooster", "Dog": "Dog", "Pig": "Pig"},
    "es": {"Rat": "Rata", "Ox": "Buey", "Tiger": "Tigre", "Rabbit": "Conejo", "Dragon": "Dragón",
           "Snake": "Serpiente", "Horse": "Caballo", "Goat": "Cabra", "Monkey": "Mono",
           "Rooster": "Gallo", "Dog": "Perro", "Pig": "Cerdo"},
    "pt": {"Rat": "Rato", "Ox": "Boi", "Tiger": "Tigre", "Rabbit": "Coelho", "Dragon": "Dragão",
           "Snake": "Serpente", "Horse": "Cavalo", "Goat": "Cabra", "Monkey": "Macaco",
           "Rooster": "Galo", "Dog": "Cão", "Pig": "Porco"},
}

# 阴阳译名
POLARITY_NAMES = {
    "en": {"Yang": "Yang", "Yin": "Yin"},
    "es": {"Yang": "Yang", "Yin": "Yin"},
    "pt": {"Yang": "Yang", "Yin": "Yin"},
}

# 日主性格解读（按日柱天干）
DAY_MASTER_READINGS = {
    "en": {
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
    },
    "es": {
        "甲": "Como un árbol alto, creces recto hacia tus metas. Tienes principios firmes, "
              "eres un líder natural y no te doblas ni cuando la vida te empuja fuerte.",
        "乙": "Como una enredadera, eres flexible y persistente en silencio. Te adaptas "
              "donde otros se quiebran, y tu suavidad es en realidad tu superpoder.",
        "丙": "Como el mismo sol, iluminas cada lugar al que entras. Eres cálido, generoso "
              "y expresivo: la gente se siente atraída por tu energía.",
        "丁": "Como la luz de una vela, ardes suave pero nunca te apagas. Eres perceptivo, "
              "reflexivo, y ves detalles que todos los demás pasan por alto.",
        "戊": "Como una montaña, eres sólido y confiable. La gente se apoya en ti en las "
              "crisis, y tu lealtad es más profunda de lo que jamás dices en voz alta.",
        "己": "Como la tierra fértil, nutres todo lo que tocas. Eres paciente, tolerante, "
              "y ayudas a crecer a los demás sin pedir nada a cambio.",
        "庚": "Como el acero puro, eres decidido y valiente. Cortas los problemas de frente, "
              "y prefieres una verdad dura antes que una mentira suave.",
        "辛": "Como una joya fina, eres refinado y preciso. Te importa la calidad en todo: "
              "tu trabajo, tus palabras y las personas que mantienes cerca.",
        "壬": "Como el océano abierto, eres ambicioso y de espíritu libre. Tu mente nunca "
              "se detiene, y nunca naciste para quedarte en un estanque pequeño.",
        "癸": "Como la lluvia suave, eres intuitivo y silenciosamente poderoso. Sientes lo "
              "que otros sienten antes de que lo digan, y nutres a todos a tu alrededor.",
    },
    "pt": {
        "甲": "Como uma árvore alta, você cresce reto em direção às suas metas. Você tem "
              "princípios, é um líder nato e não se curva nem quando a vida aperta.",
        "乙": "Como uma trepadeira, você é flexível e persistente em silêncio. Você se "
              "adapta onde os outros quebram, e sua suavidade é seu superpoder.",
        "丙": "Como o próprio sol, você ilumina qualquer lugar em que entra. Você é caloroso, "
              "generoso e expressivo — as pessoas são atraídas pela sua energia.",
        "丁": "Como a luz de uma vela, você queima suave mas nunca se apaga. Você é perceptivo, "
              "atencioso, e enxerga detalhes que todos os outros deixam passar.",
        "戊": "Como uma montanha, você é sólido e confiável. As pessoas se apoiam em você nas "
              "crises, e sua lealdade é mais profunda do que você jamais diz em voz alta.",
        "己": "Como a terra fértil, você nutre tudo o que toca. Você é paciente, tolerante, "
              "e ajuda os outros a crescer sem pedir crédito.",
        "庚": "Como o aço bruto, você é decidido e destemido. Você corta os problemas de frente, "
              "e prefere uma verdade dura a uma mentira suave.",
        "辛": "Como uma joia fina, você é refinado e preciso. Você se importa com a qualidade "
              "em tudo: seu trabalho, suas palavras e as pessoas que mantém por perto.",
        "壬": "Como o oceano aberto, você é ambicioso e de espírito livre. Sua mente nunca "
              "para, e você nunca nasceu para ficar num lago pequeno.",
        "癸": "Como a chuva suave, você é intuitivo e silenciosamente poderoso. Você sente o "
              "que as pessoas sentem antes de elas falarem, e nutre todos ao seu redor.",
    },
}

# 五行主题（theme）与行动建议（action）
ELEMENT_TIPS = {
    "en": {
        "Wood": ("growth, planning and starting new things", "say yes to that new project"),
        "Fire": ("visibility and passion", "stop hiding, let people see what you can do"),
        "Earth": ("stability and trust", "build routines and keep your promises to yourself"),
        "Metal": ("discipline and boundaries", "learn to say no and finish what you start"),
        "Water": ("wisdom and flow", "read more, travel more, and let things move"),
    },
    "es": {
        "Wood": ("el crecimiento, la planificación y los nuevos comienzos", "dile que sí a ese nuevo proyecto"),
        "Fire": ("la visibilidad y la pasión", "deja de esconderte y muestra lo que sabes hacer"),
        "Earth": ("la estabilidad y la confianza", "crea rutinas y cumple las promesas que te haces"),
        "Metal": ("la disciplina y los límites", "aprende a decir que no y termina lo que empiezas"),
        "Water": ("la sabiduría y el fluir", "lee más, viaja más y deja que las cosas fluyan"),
    },
    "pt": {
        "Wood": ("o crescimento, o planejamento e os novos começos", "diga sim àquele novo projeto"),
        "Fire": ("a visibilidade e a paixão", "pare de se esconder e mostre o que você sabe fazer"),
        "Earth": ("a estabilidade e a confiança", "crie rotinas e cumpra as promessas que faz a si mesmo"),
        "Metal": ("a disciplina e os limites", "aprenda a dizer não e termine o que começa"),
        "Water": ("a sabedoria e o fluir", "leia mais, viaje mais e deixe as coisas fluírem"),
    },
}

# LLM 提示词中的语言名
LANGUAGE_NAMES = {"en": "English", "es": "Spanish (Latin American)", "pt": "Brazilian Portuguese"}

# 发布素材：标题模板、描述模板、话题标签
PUBLISH = {
    "en": {
        "title_chart": "Born on {date}? Your Chinese Birth Chart, Explained 🔮",
        "title_zodiac": "{animal} Daily Fortune · {date} 🔮 Chinese Astrology",
        "description_chart": "Your BaZi (Four Pillars of Destiny) reading for {date}. "
                             "Day Master: {day_master}. Dominant element: {dominant}. "
                             "Drop YOUR birth date in the comments for a free reading! 🔮",
        "description_zodiac": "Daily BaZi fortune for the {animal}. Follow for your sign every day, "
                              "and comment your birth date for a free personal reading! 🔮",
        "hashtags": ["#bazi", "#chineseastrology", "#fourpillarsofdestiny", "#zodiac",
                     "#astrology", "#fyp", "#spirituality", "#birthchart"],
        "cta_comment": "Comment your birth date for a free reading!",
    },
    "es": {
        "title_chart": "¿Naciste el {date}? Tu carta astral china, explicada 🔮",
        "title_zodiac": "Horóscopo del {animal} · {date} 🔮 Astrología china",
        "description_chart": "Tu lectura de BaZi (Cuatro Pilares del Destino) para {date}. "
                             "Maestro del Día: {day_master}. Elemento dominante: {dominant}. "
                             "¡Deja TU fecha de nacimiento en los comentarios para una lectura gratis! 🔮",
        "description_zodiac": "Horóscopo BaZi diario para {animal}. Sígueme para ver tu signo cada día "
                              "y comenta tu fecha de nacimiento para una lectura personal gratis. 🔮",
        "hashtags": ["#bazi", "#astrologiachina", "#cuatropilares", "#zodiaco",
                     "#astrologia", "#fyp", "#espiritualidad", "#cartaastral"],
        "cta_comment": "¡Comenta tu fecha de nacimiento para una lectura gratis!",
    },
    "pt": {
        "title_chart": "Nasceu em {date}? Seu mapa astral chinês, explicado 🔮",
        "title_zodiac": "Horóscopo do {animal} · {date} 🔮 Astrologia chinesa",
        "description_chart": "Sua leitura de BaZi (Quatro Pilares do Destino) para {date}. "
                             "Mestre do Dia: {day_master}. Elemento dominante: {dominant}. "
                             "Deixe SUA data de nascimento nos comentários para uma leitura grátis! 🔮",
        "description_zodiac": "Horóscopo BaZi diário para {animal}. Siga para ver seu signo todo dia "
                              "e comente sua data de nascimento para uma leitura pessoal grátis. 🔮",
        "hashtags": ["#bazi", "#astrologiachinesa", "#quatropilares", "#zodiaco",
                     "#astrologia", "#fyp", "#espiritualidade", "#mapaastral"],
        "cta_comment": "Comente sua data de nascimento para uma leitura grátis!",
    },
}

SUPPORTED_LANGS = list(DAY_MASTER_READINGS.keys())


def check_lang(lang: str) -> str:
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"不支持的语言 '{lang}'，可选: {', '.join(SUPPORTED_LANGS)}")
    return lang
