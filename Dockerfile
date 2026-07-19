# 出海八字短视频生成器 —— 服务器/挂机批量出片用
#
# 构建:  docker build -t bazi-video .
# 出片:  docker run --rm -v $(pwd)/appdata:/app/appdata -v $(pwd)/.env:/app/.env \
#            bazi-video --date 1995-08-17 --time 14:30
# 系列:  docker run --rm -v $(pwd)/appdata:/app/appdata bazi-video --series zodiac --jobs 4

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 无显示器渲染
ENV SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy

ENTRYPOINT ["python", "main_bazi.py"]
CMD ["--help"]
