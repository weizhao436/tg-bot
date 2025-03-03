#!/bin/bash

# 检查Redis服务是否运行
echo "检查Redis服务状态..."
if ! pgrep redis-server > /dev/null; then
    echo "Redis服务未运行，尝试启动..."
    if command -v redis-server > /dev/null; then
        redis-server --daemonize yes
        echo "Redis服务已启动"
    else
        echo "警告: 找不到Redis服务器，请安装Redis: apt-get install redis-server"
        echo "将使用传统文件监控方式进行按钮更新"
    fi
else
    echo "Redis服务正在运行"
fi

# 启动后台管理系统
echo "启动后台管理系统..."
python3 admin_web.py &
ADMIN_PID=$!

# 等待几秒钟确保后台系统已启动
sleep 3

# 启动机器人
echo "启动 Telegram 机器人..."
python3 bot.py &
BOT_PID=$!

# 捕获 SIGINT 信号（Ctrl+C）
trap "echo '正在关闭服务...'; kill $ADMIN_PID $BOT_PID; exit" INT

# 等待用户按 Ctrl+C
echo "服务已启动。按 Ctrl+C 停止服务。"
wait 