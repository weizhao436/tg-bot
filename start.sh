#!/bin/bash
# 
# Telegram Bot 启动脚本
# 解决权限问题和环境变量设置
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

print_green "===== Telegram Bot 启动脚本 ====="
print_yellow "当前工作目录: $(pwd)"

# 设置基本配置
BOT_DIR=$(pwd)
LOG_DIR="$BOT_DIR/logs"
DATA_DIR="$BOT_DIR/data"
LOG_FILE="$LOG_DIR/bot.log"

# 创建必要的目录
print_yellow "确保必要的目录存在..."
mkdir -p "$LOG_DIR" "$DATA_DIR"
chmod 755 "$LOG_DIR" "$DATA_DIR"

# 输出系统信息
print_yellow "系统信息:"
echo "操作系统: $(uname -a)"
echo "Python版本: $(python3 --version 2>&1)"
echo "用户: $(whoami)"
echo "权限: $(id)"

# 检查config.py文件
if [ -f "config.py" ]; then
    print_green "找到config.py文件"
    
    # 从config.py提取BOT_TOKEN并设置环境变量
    if grep -q "BOT_TOKEN" config.py; then
        print_yellow "从config.py中提取BOT_TOKEN..."
        # 使用Python读取BOT_TOKEN (更可靠的方法)
        TOKEN=$(python3 -c "import config; print(config.BOT_TOKEN)")
        
        if [ -n "$TOKEN" ]; then
            print_green "成功提取BOT_TOKEN"
            export TELEGRAM_BOT_TOKEN="$TOKEN"
            echo "已设置环境变量TELEGRAM_BOT_TOKEN"
        else
            print_red "无法从config.py提取BOT_TOKEN"
        fi
    else
        print_red "config.py中未找到BOT_TOKEN变量"
    fi
else
    print_red "未找到config.py文件"
fi

# 检查数据库文件
DB_PATH="$DATA_DIR/bot_data.db"
if [ -f "$DB_PATH" ]; then
    print_green "找到数据库文件: $DB_PATH"
    # 确保数据库文件有正确的权限
    chmod 664 "$DB_PATH"
else
    print_yellow "未找到数据库文件，将在启动时创建: $DB_PATH"
    touch "$DB_PATH"
    chmod 664 "$DB_PATH"
fi

# 确认环境变量设置
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    print_green "环境变量TELEGRAM_BOT_TOKEN已设置"
else
    print_red "警告: 环境变量TELEGRAM_BOT_TOKEN未设置"
    print_yellow "尝试从config.py获取TOKEN..."
fi

# 启动机器人，将日志输出到文件和控制台
print_green "启动Telegram Bot..."
echo "===== 启动时间: $(date) =====" | tee -a "$LOG_FILE"

# 前台运行（开发测试用）
if [ "$1" = "--foreground" ] || [ "$1" = "-f" ]; then
    print_yellow "在前台运行机器人 (按Ctrl+C停止)"
    python3 bot.py 2>&1 | tee -a "$LOG_FILE"
else
    # 后台运行（生产环境用）
    print_yellow "在后台运行机器人"
    nohup python3 bot.py > "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > "$BOT_DIR/bot.pid"
    print_green "机器人已在后台启动，PID: $BOT_PID"
    print_yellow "查看日志: tail -f $LOG_FILE"
    print_yellow "停止机器人: bash stop.sh"
fi 