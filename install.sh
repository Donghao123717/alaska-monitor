#!/bin/bash
# ═══════════════════════════════════════════════
#  一键安装脚本 - Alaska Miles Monitor
# ═══════════════════════════════════════════════

set -e
echo "🛫 Alaska Miles Monitor 安装中..."

# 检查 Python 版本
python3 --version >/dev/null 2>&1 || { echo "❌ 需要 Python 3.10+"; exit 1; }

# 安装依赖
echo "📦 安装 Python 依赖..."
pip3 install playwright pyyaml

# 安装 Playwright 浏览器
echo "🌐 安装 Chromium 浏览器..."
python3 -m playwright install chromium

echo ""
echo "✅ 安装完成！"
echo ""
echo "📝 下一步："
echo "   1. 编辑 config.yaml，填入你的账号和航线信息"
echo "   2. 获取 Gmail App Password："
echo "      → Google 账号 → 安全性 → 两步验证 → 应用专用密码"
echo "   3. 运行测试：python3 monitor.py"
echo "   4. 设置定时任务：bash setup_cron.sh"
