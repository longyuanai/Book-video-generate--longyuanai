# 📚 Book Video Generator

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-required-red.svg)](https://ffmpeg.org/)

一个自动化短视频生成工具，包含两种模式：

- **📚 书籍推广模式**：根据书名自动生成带配音和字幕的书籍推广短视频；
- **🔮 出海八字模式**：输入出生日期，自动排四柱、生成英文解读文案、英文配音，输出 9:16 竖屏成片，可直接发布到 TikTok / YouTube Shorts / Instagram Reels。

## 🔮 出海八字模式（BaZi Overseas Mode）

面向海外受众的八字（Four Pillars of Destiny）内容自动化流水线：

```
出生日期时间 → 排四柱（天文级节气 + 时区 + 十神 + 大运，纯 Python 离线）
            → 多语言口播文案（英/西/葡；LLM 优先，失败自动降级母语模板）
            → TTS 配音 + SRT 字幕 + 词级时间戳（Edge-TTS，27 种海外语音）
            → 9:16 竖屏渲染（逐词高亮字幕、片头动画，支持无显示器服务器）
            → FFmpeg 合成成片 + 缩略图 + 标题/简介/话题标签
```

### 使用方法

```bash
# 单条个人命盘
python main_bazi.py --date 1995-08-17 --time 14:30 --gender female

# 海外出生：指定出生地时区（纽约冬令时 -5、伦敦 0、圣保罗 -3）
python main_bazi.py --date 1995-08-17 --tz -5

# 多语言市场：西班牙语（拉美）/ 葡萄牙语（巴西）
python main_bazi.py --date 1995-08-17 --lang es
python main_bazi.py --date 1995-08-17 --lang pt

# 批量模式：CSV 一行一条（评论区收集的生日直接喂进来）
python main_bazi.py --batch birthdays.csv

# 生肖系列：一次生成 12 生肖当日运势（日更内容）
python main_bazi.py --series zodiac --lang en

# 其他：离线文案 / 只出文案 / 指定语音 / 原尺寸渲染
python main_bazi.py --date 1995-08-17 --offline
python main_bazi.py --date 1995-08-17 --script-only
python main_bazi.py --date 1995-08-17 --voice Andrew
python main_bazi.py --date 1995-08-17 --zoom 100
```

批量 CSV 格式（date 必填，其余可省）：

```csv
date,time,tz,gender,lang,voice
1995-08-17,14:30,8,female,en,Ava
2001-03-02,,-5,male,es,
```

### 每条视频的输出物料

```
appdata/bazi_19950817_1430_en/
├── final_video.mp4    # 9:16 成片（可直发 TikTok/Shorts/Reels）
├── thumbnail.png      # 封面缩略图
├── script.txt         # 口播文案
├── publish.txt/json   # 标题 + 简介 + 话题标签
├── narration.mp3/.srt # 配音与字幕
└── narration.words.json  # 词级时间戳（逐词高亮字幕用）
```

### 视频与内容特性

- **四柱命盘展示**：四柱汉字按五行配色（木绿、火红、土黄、金白、水蓝），拼音+英文注解，片头逐列入场动画
- **逐词高亮字幕（卡拉OK式）**：基于 TTS 词级时间戳，已读白/当前金/未读灰，无词级数据自动降级整句字幕
- **命理深度**：日主性格、五行分布与所缺、十神、大运（当前十年运融入文案）
- **玄学风格素材**：`tools/generate_assets.py` 程序化生成星云/星空/金粉竖屏背景与 ambient 冥想 BGM，全部离线无版权风险
- **片尾 CTA**：引导关注 + 评论区留生日，天然互动增长钩子

### 排盘精度

- 节气采用天文算法（Meeus 太阳视黄经，误差约 ±15 分钟），年柱/月柱交接日附近也能排准
- 支持出生地时区（`--tz`），海外出生排盘必备
- 日柱以 1949-10-01 甲子日为锚点；默认晚子时（23 点后）按次日排日柱
- 大运：阳年男/阴年女顺排，起运年龄按 3 天折 1 年精确计算
- 模块可独立使用：`from bazi import calculate_bazi`

### LLM 配置（可选）

默认使用内置免费接口；建议切换到稳定的 OpenAI 兼容接口（DeepSeek / OpenAI / 智谱 GLM 等）。
推荐方式：复制 `.env.example` 为 `.env` 并填入配置（`.env` 不会被提交）：

```bash
cp .env.example .env
# 编辑 .env：
# LLM_API_URL=https://api.deepseek.com/v1/chat/completions
# LLM_API_KEY=sk-...
# LLM_MODEL=deepseek-chat
```

也可以用系统环境变量（优先级高于 .env）。不配置或调用失败时自动降级为内置母语模板（英/西/葡），离线也能出片。

---

## 📚 书籍推广模式

## 🖼️ 效果预览

[示例视频](https://github.com/user-attachments/assets/385a804c-904a-4aae-a595-58f9240a66b9)


### 视频特性
生成的视频包含：
- 🎬 **动态封面展示效果** - 书籍封面滑动动画，4秒片头效果，书籍封面在`resource/covers/`中随机获取
- 🖼️ **背景图片自动切换** - 每10秒切换背景，营造氛围，背景图片随机从`resource/backgrounds/`中获取
- 📝 **同步字幕显示** - 根据音频时长精准同步，底部居中显示
- 🎵 **多音轨混合** - 配音 + 背景音乐 + 音效，音量自动平衡，背景音乐随机从`resource/bgm/`中获取

### 使用建议
1. **首次使用**: 建议先下载示例视频查看效果
2. **测试运行**: 使用简单的书籍名称进行测试
3. **参数调整**: 根据需要调整视频参数和语音选择

## 📋 系统要求

- **Python**: 3.7+
- **FFmpeg**: 必须安装并添加到系统PATH
- **操作系统**: Windows / macOS / Linux

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/SheenHalo/Book-video-generate.git
cd Book-video-generate
```

### 2. 创建虚拟环境

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 检查FFmpeg

项目依赖FFmpeg进行视频合成，请确保已正确安装：

```bash
python video_processor.py
```

如果显示"ffmpeg 可用"，则安装成功。如果显示"ffmpeg 不可用"，请按以下步骤安装：

#### Windows FFmpeg安装
1. 下载FFmpeg: https://ffmpeg.org/download.html
2. 解压到 `C:\ffmpeg`
3. 添加 `C:\ffmpeg\bin` 到系统PATH环境变量
4. 重启命令行并验证：`ffmpeg -version`

#### macOS FFmpeg安装
```bash
brew install ffmpeg
```

#### Linux FFmpeg安装
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL/Fedora
sudo yum install ffmpeg
```

### 5. 配置LLM API
提供了一个免费的LLM API接口。如果失效了，请自行配置。
编辑 `llm.py` 文件，配置你的LLM API信息：

```python
# 在LLMClient类中修改
self.api_url = "你的API地址"
self.api_key = "你的API密钥"
```

### 6. 准备资源文件

确保以下目录包含必要的文件：

```
resource/
├── backgrounds/    # 背景图片 (jpg/png)
├── bgm/           # 背景音乐 (mp3)
├── covers/        # 书籍封面存储位置
├── effects/       # 音效文件 (mp3)
└── fonts/         # 字体文件 (包含msyh.ttc)
```

### 7. 运行程序

```bash
python main.py
```

按照提示输入书名，程序将自动生成视频：

```
请输入书名: 巴别塔
正在获取书籍信息...
正在生成文案...
正在生成语音...
正在生成视频...
开始合成音视频...
最终视频已保存到: appdata/巴别塔/final_video.mp4
```

## 🛠️ 高级配置

### 修改语音类型

在 `main.py` 中修改语音选择：

```python
# 查看所有可用语音
print(voice_dict.keys())

# 选择特定语音
voice = voice_dict.get("晓秋-女")
```

### 自定义视频参数

在 `app.py` 的 `make_movie` 函数中可以调整：
- 屏幕尺寸
- 动画时长
- 音量大小
- 背景切换时间

### 支持的语音列表

项目支持43种中文语音变体：

| 语音名称 | 类型 | 特点 |
|---------|------|------|
| 晓晓（标准）-女 | 标准 | 温暖，全面，生动 |
| 晓辰（标准）-女 | 标准 | 友好，休闲，乐观 |
| 云峰-男 | 标准 | 自信，生动，情感 |
| 晓晓（多语言）-女 | 多语言 | 温暖，生动，明亮 |
| 晓通（吴语）-女 | 方言 | 温暖，友好，舒缓 |
| 晓敏（粤语）-女 | 方言 | 明亮，清晰，自信 |
| ...更多语音详见代码 | | |

## 📁 项目结构

```
Book-video-generate/
├── main.py              # 书籍模式入口
├── main_bazi.py         # 出海八字模式入口
├── app.py               # 视频生成核心（书籍横屏）
├── bazi_video.py        # 八字竖屏渲染器（9:16、逐词字幕、片头动画、无显示器）
├── bazi/                # 八字模块
│   ├── calculator.py    # 四柱排盘（十神、大运、时区，纯Python）
│   ├── solar_terms.py   # 天文级节气计算（Meeus 算法）
│   ├── script_writer.py # 多语言文案生成（LLM+母语模板，英/西/葡）
│   ├── locales.py       # 多语言资源
│   └── publish_kit.py   # 发布素材（标题/简介/话题标签）
├── tools/
│   └── generate_assets.py # 程序化生成玄学风格背景与BGM
├── spider.py            # 豆瓣爬虫
├── llm.py               # LLM客户端（环境变量配置，OpenAI兼容）
├── tts_generator.py     # TTS生成器（27种海外语音+词级时间戳）
├── video_processor.py   # 视频处理工具
├── requirements.txt     # 依赖列表
├── appdata/            # 生成的文件
└── resource/           # 资源文件
```

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

