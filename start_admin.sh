#!/bin/bash
#
# Telegram Bot 管理面板启动脚本
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

print_green "===== Telegram Bot 管理面板启动脚本 ====="
print_yellow "当前工作目录: $(pwd)"

# 设置基本配置
BOT_DIR=$(pwd)
LOG_DIR="$BOT_DIR/logs"
DATA_DIR="$BOT_DIR/data"
LOG_FILE="$LOG_DIR/admin.log"

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
else
    print_red "未找到config.py文件"
    exit 1
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

# 启动管理面板
print_green "启动Telegram Bot管理面板..."
echo "===== 启动时间: $(date) =====" | tee -a "$LOG_FILE"

# 前台运行（开发测试用）
if [ "$1" = "--foreground" ] || [ "$1" = "-f" ]; then
    print_yellow "在前台运行管理面板 (按Ctrl+C停止)"
    python3 admin.py 2>&1 | tee -a "$LOG_FILE"
else
    # 后台运行（生产环境用）
    print_yellow "在后台运行管理面板"
    nohup python3 admin.py > "$LOG_FILE" 2>&1 &
    ADMIN_PID=$!
    echo $ADMIN_PID > "$BOT_DIR/admin.pid"
    print_green "管理面板已在后台启动，PID: $ADMIN_PID"
    print_yellow "查看日志: tail -f $LOG_FILE"
    print_yellow "停止管理面板: bash stop_admin.sh"
fi 