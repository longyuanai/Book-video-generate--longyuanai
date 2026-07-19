# 腾讯云服务器部署（每日自动出片）

适用于 Ubuntu / Debian 系统（OpenCloudOS/CentOS 把 `apt` 换成 `yum` 即可）。

## 一次性安装（约 5 分钟）

```bash
# 1. 基础依赖
sudo apt update && sudo apt install -y git python3-venv python3-pip ffmpeg

# 2. 拉代码
git clone https://github.com/hzj-Jeff-07/Book-video-generate--longyuanai.git
cd Book-video-generate--longyuanai

# 3. Python 环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 配置 LLM（可选但推荐，DeepSeek 国内直连）
cp .env.example .env
vim .env   # 填入 LLM_API_KEY 等

# 5. 手动跑一条验证全链路（重点看 TTS 是否连通）
python main_bazi.py --date 1995-08-17 --time 14:30 --zoom 200
```

## 配置每日定时（crontab）

```bash
chmod +x deploy/daily_run.sh
crontab -e
# 添加一行（每天早上 8:00 生成英文版；路径按实际修改）：
0 8 * * * bash /root/Book-video-generate--longyuanai/deploy/daily_run.sh en
# 想多语言就多加几行错开时间：
# 30 8 * * * bash /root/Book-video-generate--longyuanai/deploy/daily_run.sh es
```

生成结果在 `appdata/zodiac_日期_语言/`（自动保留最近 7 天），日志在 `logs/`。

## 取回视频发布

任选其一：

```bash
# 方式 A：本地电脑用 scp 拉取（Windows 用 WinSCP 图形界面同理）
scp -r root@服务器IP:~/Book-video-generate--longyuanai/appdata/zodiac_$(date +%Y%m%d)_en ./

# 方式 B：服务器上装宝塔面板，网页文件管理器里直接下载
```

## Docker 方式（可选替代）

```bash
docker build -t bazi-video .
# crontab 行改为：
# 0 8 * * * docker run --rm -v /root/bazi-out:/app/appdata --env-file /root/.env bazi-video --series zodiac --jobs 2 --zoom 100
```

## 常见问题

- **TTS 失败（连不上 Edge-TTS）**：大陆机房访问微软服务偶有波动，重试通常可过；
  如持续失败，换香港/新加坡地域的服务器最稳。
- **磁盘涨满**：`daily_run.sh` 已自动清理 7 天前的产物；也可调小保留天数。
- **更新代码**：`cd 项目目录 && git pull`（正在运行的 cron 不受影响）。
