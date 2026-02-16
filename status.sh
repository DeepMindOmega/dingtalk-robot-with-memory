#!/bin/bash
# 检查钉钉机器人状态

DINGTALK_DIR="/home/admin/.opencode/skills/dingtalk-robot"

echo "=========================================="
echo "   钉钉机器人 - 状态检查"
echo "=========================================="
echo ""

if [ -f /tmp/dingtalk_pids.txt ]; then
    PIDS=$(cat /tmp/dingtalk_pids.txt)
    echo "📋 记录的进程 ID: $PIDS"
    echo ""
fi

echo "🔍 检查运行中的进程..."
RUNNING_PROCS=$(ps aux | grep -E "gateway.py|processor.py" | grep -v grep)
if [ -z "$RUNNING_PROCS" ]; then
    echo "  ❌ 没有运行中的服务"
    echo ""
    echo "💡 启动服务:"
    echo "   cd $DINGTALK_DIR && ./start.sh"
    exit 1
else
    echo "  ✅ 服务运行中"
    echo ""
    echo "进程列表:"
    ps aux | grep -E "gateway.py|processor.py" | grep -v grep | awk '{print "  PID:", $2, "|", $11, $12, $13}'
    echo ""
fi

echo "📊 Gateway 日志摘要:"
if [ -f "$DINGTALK_DIR/logs/gateway.log" ]; then
    echo "  Token 状态:"
    grep "Token refreshed" "$DINGTALK_DIR/logs/gateway.log" | tail -1
    echo "  连接状态:"
    grep "endpoint is" "$DINGTALK_DIR/logs/gateway.log" | tail -1
    echo "  最近活动:"
    grep "INFO.*消息\|INFO.*任务\|INFO.*检查" "$DINGTALK_DIR/logs/gateway.log" | tail -3 | sed 's/^/    /'
else
    echo "  ❌ 日志文件不存在"
fi

echo ""
echo "📊 Processor 日志摘要:"
if [ -f "$DINGTALK_DIR/logs/processor.log" ]; then
    LAST_LINE=$(tail -1 "$DINGTALK_DIR/logs/processor.log")
    if [ -n "$LAST_LINE" ]; then
        echo "  $LAST_LINE"
    else
        echo "  (日志为空，等待第一个任务)"
    fi
else
    echo "  ❌ 日志文件不存在"
fi

echo ""
echo "=========================================="
echo "✅ 一切正常！可以在钉钉中使用机器人了"
echo "=========================================="
echo ""
echo "📖 命令帮助:"
echo "  - 列出文件"
echo "  - 查看 <文件>"
echo "  - 执行 <命令>"
echo "  - 状态"
echo "  - 帮助"
echo ""
echo "📚 详细文档:"
echo "  cat $DINGTALK_DIR/QUICKSTART.md"
echo ""
