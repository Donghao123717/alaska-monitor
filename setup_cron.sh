#!/bin/bash
# 设置 macOS 定时任务（每小时运行一次）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/Users/lidonghao/.pyenv/versions/3.11.1/bin/python3"
LOG="$SCRIPT_DIR/cron.log"

# 写入 crontab（每小时的第0分钟运行）
CRON_LINE="*/5 * * * * cd $SCRIPT_DIR && $PYTHON monitor.py >> $LOG 2>&1"

# 检查是否已存在
(crontab -l 2>/dev/null | grep -v "alaska_monitor"; echo "$CRON_LINE") | crontab -

echo "✅ 定时任务已设置：每5分钟运行一次"
echo "   查看任务：crontab -l"
echo "   查看日志：tail -f $LOG"
echo ""
echo "⚠️  注意：Mac 睡眠时 cron 不会运行。"
echo "   如需持续监控，建议保持 Mac 唤醒，或改用 launchd。"
