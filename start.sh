#!/bin/bash
# 钉钉机器人启动脚本

DINGTALK_DIR="/home/admin/.opencode/skills/dingtalk-robot"
cd "$DINGTALK_DIR"

echo "🔍 检查现有进程..."
pkill -f "src/gateway.py" 2>/dev/null
pkill -f "src/processor.py" 2>/dev/null
sleep 2

echo "🚀 启动钉钉机器人..."

# 启动 Gateway
nohup python3 -u src/gateway.py > logs/gateway.log 2>&1 &
GATEWAY_PID=$!
echo "  ✓ Gateway 进程 ID: $GATEWAY_PID"

# 启动 Processor (使用-u避免输出缓冲)
nohup python3 -u src/processor.py > logs/processor.log 2>&1 &
PROCESSOR_PID=$!
echo "  ✓ Processor 进程 ID: $PROCESSOR_PID"

sleep 3

echo ""
echo "📊 检查服务状态..."
if ps -p $GATEWAY_PID > /dev/null; then
    echo "  ✓ Gateway 运行中"
    tail -5 logs/gateway.log | grep -E "Token refreshed|endpoint is"
else
    echo "  ✗ Gateway 未启动，查看日志: tail -f $DINGTALK_DIR/logs/gateway.log"
fi

if ps -p $PROCESSOR_PID > /dev/null; then
    echo "  ✓ Processor 运行中"
else
    echo "  ✗ Processor 未启动，查看日志: tail -f $DINGTALK_DIR/logs/processor.log"
fi

echo ""
echo "📝 进程 ID 已保存到: /tmp/dingtalk_pids.txt"
echo $GATEWAY_PID $PROCESSOR_PID > /tmp/dingtalk_pids.txt

echo ""
echo "💬 现在可以在钉钉中给机器人发送消息了！"
echo ""
echo "📖 可用命令:"
echo "  - 列出文件"
echo "  - 查看 <文件名>"
echo "  - 执行 <命令>"
echo "  - 状态"
echo "  - 帮助"
echo ""
echo "🔍 查看日志:"
echo "  tail -f $DINGTALK_DIR/logs/gateway.log"
echo "  tail -f $DINGTALK_DIR/logs/processor.log"
echo ""
echo "⏹️  停止服务:"
echo "  bash $DINGTALK_DIR/stop.sh"
