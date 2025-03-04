#!/bin/bash
# 
# Telegram Bot 停止脚本
#

# 彩色输出函数
print_green() {
    echo -e "\e[32m$1\e[0m"
}

print_yellow() {
    echo -e "\e[33m$1\e[0m"
}

print_red() {
    echo -e "\e[31m$1\e[0m"
}

# 确保脚本在正确的目录中执行
cd "$(dirname "$0")" || {
    print_red "无法切换到脚本所在目录"
    exit 1
}

print_green "===== Telegram Bot 停止脚本 ====="
print_yellow "当前工作目录: $(pwd)"

BOT_DIR=$(pwd)
PID_FILE="$BOT_DIR/bot.pid"
LOCK_FILE="$BOT_DIR/bot.lock"

# 检查进程ID文件
if [ -f "$PID_FILE" ]; then
    BOT_PID=$(cat "$PID_FILE")
    
    if [ -n "$BOT_PID" ]; then
        print_yellow "找到机器人进程，PID: $BOT_PID"
        
        # 检查进程是否存在
        if ps -p "$BOT_PID" > /dev/null; then
            print_yellow "正在停止机器人进程..."
            kill "$BOT_PID"
            
            # 等待进程终止
            count=0
            while ps -p "$BOT_PID" > /dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
                print_yellow "等待进程终止... ($count/10)"
            done
            
            # 检查进程是否已终止
            if ps -p "$BOT_PID" > /dev/null; then
                print_red "进程未响应，尝试强制终止..."
                kill -9 "$BOT_PID"
                sleep 1
            fi
            
            print_green "机器人进程已停止"
        else
            print_yellow "进程ID $BOT_PID 已不存在"
        fi
    else
        print_red "PID文件为空"
    fi
    
    # 删除PID文件
    rm -f "$PID_FILE"
    print_yellow "已删除PID文件"
else
    print_yellow "未找到PID文件，尝试查找Python进程..."
    # 尝试通过进程名找到并停止
    BOT_PIDS=$(pgrep -f "python3 bot.py")
    
    if [ -n "$BOT_PIDS" ]; then
        print_yellow "找到机器人进程: $BOT_PIDS"
        for pid in $BOT_PIDS; do
            print_yellow "正在停止进程 $pid..."
            kill "$pid"
        done
        print_green "已发送停止信号到所有机器人进程"
    else
        print_red "未找到正在运行的机器人进程"
    fi
fi

# 删除锁文件
if [ -f "$LOCK_FILE" ]; then
    rm -f "$LOCK_FILE"
    print_yellow "已删除锁文件"
fi

print_green "机器人停止操作完成" 