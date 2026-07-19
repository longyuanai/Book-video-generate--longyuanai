#!/usr/bin/env bash
# 每日自动出片脚本（配合 crontab 使用，见 deploy/README.md）
# 用法: bash deploy/daily_run.sh [lang]
set -e

cd "$(dirname "$0")/.."
LANG_OPT="${1:-en}"
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily_$(date +%Y%m%d).log"

# 激活虚拟环境（如果存在）
[ -f venv/bin/activate ] && source venv/bin/activate

echo "===== $(date '+%F %T') 开始生成 (${LANG_OPT}) =====" >> "$LOG_FILE"
python main_bazi.py --series zodiac --lang "$LANG_OPT" --jobs 2 --zoom 100 >> "$LOG_FILE" 2>&1
echo "===== $(date '+%F %T') 完成 =====" >> "$LOG_FILE"

# 只保留最近 7 天的生成产物与日志，避免磁盘涨满
find appdata -maxdepth 1 -type d -name "zodiac_*" -mtime +7 -exec rm -rf {} + 2>/dev/null || true
find "$LOG_DIR" -name "daily_*.log" -mtime +7 -delete 2>/dev/null || true
