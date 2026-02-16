#!/bin/bash
# 钉钉机器人停止脚本

echo "🛑 停止钉钉机器人..."

pkill -f "src/gateway.py"
pkill -f "src/processor.py"

sleep 2

echo "✓ 服务已停止"
