#!/bin/bash
# 钉钉机器人诊断工具

DINGTALK_DIR="/home/admin/.opencode/skills/dingtalk-robot"

echo "=========================================="
echo "   钉钉机器人 - 问题诊断"
echo "=========================================="
echo ""

echo "🔍 1. 检查服务状态..."
if ps aux | grep "src/gateway.py" | grep -v grep > /dev/null; then
    echo "  ✅ Gateway 运行中"
else
    echo "  ❌ Gateway 未运行"
    echo ""
    echo "💡 解决方案:"
    echo "   cd $DINGTALK_DIR"
    echo "   ./start.sh"
    exit 1
fi

if ps aux | grep "src/processor.py" | grep -v grep > /dev/null; then
    echo "  ✅ Processor 运行中"
else
    echo "  ❌ Processor 未运行"
fi

echo ""
echo "🔍 2. 检查连接状态..."
CONNECTION=$(grep "endpoint is" "$DINGTALK_DIR/logs/gateway.log" | tail -1)
if [ -n "$CONNECTION" ]; then
    echo "  ✅ 已连接到钉钉"
    echo "  $CONNECTION"
else
    echo "  ❌ 未连接到钉钉"
fi

echo ""
echo "🔍 3. 检查 Token 状态..."
TOKEN_STATUS=$(grep "Token refreshed" "$DINGTALK_DIR/logs/gateway.log" | tail -1)
if [ -n "$TOKEN_STATUS" ]; then
    echo "  ✅ Token 已获取"
    echo "  $TOKEN_STATUS"
else
    echo "  ❌ Token 未获取"
fi

echo ""
echo "🔍 4. 检查消息接收..."
MSG_RECEIVED=$(grep -E "\[群聊\]|\[单聊\]" "$DINGTALK_DIR/logs/gateway.log" | tail -3)
if [ -n "$MSG_RECEIVED" ]; then
    echo "  ✅ 已收到消息:"
    echo "$MSG_RECEIVED" | sed 's/^/    /'
else
    echo "  ❌ 没有收到任何消息"
    echo ""
    echo "💡 这是最常见的问题！原因可能是:"
    echo ""
    echo "  1️⃣  机器人未添加到群聊"
    echo "     → 在钉钉中把机器人添加到群里"
    echo ""
    echo "  2️⃣  机器人权限未配置"
    echo "     → 需要在钉钉开放平台配置机器人权限"
    echo ""
    echo "  3️⃣  用户ID不在授权列表中"
    echo "     → 需要将你的用户ID添加到配置文件"
    echo ""
    echo "  4️⃣  机器人消息订阅未启用"
    echo "     → 需要订阅机器人的消息事件"
fi

echo ""
echo "🔍 5. 检查授权用户配置..."
USER_COUNT=$(jq '.AUTHORIZED_USERS | length' "$DINGTALK_DIR/config.json" 2>/dev/null || echo "2")
echo "  授权用户数量: $USER_COUNT"
echo "  当前授权用户:"
jq -r '.AUTHORIZED_USERS[]' "$DINGTALK_DIR/config.json" 2>/dev/null || cat "$DINGTALK_DIR/config.json" | grep -A 10 "AUTHORIZED_USERS"

echo ""
echo "💡 快速解决方案"
echo ""
echo "【方案一】先在私聊中测试"
echo "  1. 在钉钉中打开机器人聊天"
echo "  2. 发送消息: 测试"
echo "  3. 查看日志: tail -f $DINGTALK_DIR/logs/gateway.log"
echo ""
echo "【方案二】确保机器人已添加到群聊"
echo "  1. 打开钉钉群聊设置"
echo "  2. 检查机器人在群成员列表中"
echo "  3. 如果不在，邀请机器人入群"
echo ""
echo "【方案三】配置机器人权限（需要操作）"
echo "  1. 访问钉钉开放平台: https://open-dev.dingtalk.com/"
echo "  2. 进入你的应用设置"
echo "  3. 启用机器人功能"
echo "  4. 配置消息推送和订阅"
echo "  5. 设置机器人在群聊中可被 @"
echo ""
echo "【方案四】添加用户ID到授权列表"
echo "  1. 在钉钉中获取你的用户ID"
echo "  2. 编辑配置文件: nano $DINGTALK_DIR/config.json"
echo "  3. 添加你的ID到 AUTHORIZED_USERS"
echo "  4. 重启服务: $DINGTALK_DIR/stop.sh && $DINGTALK_DIR/start.sh"
echo ""
echo "📚 查看完整日志:"
echo "  tail -100 $DINGTALK_DIR/logs/gateway.log | less"
echo ""
echo "=========================================="
