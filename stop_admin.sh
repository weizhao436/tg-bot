#!/bin/bash
#
# Telegram Bot 管理面板停止脚本
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

print_green "===== Telegram Bot 管理面板停止脚本 ====="
print_yellow "当前工作目录: $(pwd)"

# 检查PID文件
PID_FILE="admin.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    print_yellow "找到管理面板进程，PID: $PID"
    
    # 尝试停止进程
    if kill -15 $PID 2>/dev/null; then
        print_green "已发送停止信号到管理面板进程"
        
        # 等待进程结束
        print_yellow "等待进程结束..."
        for i in {1..5}; do
            if ! ps -p $PID > /dev/null; then
                break
            fi
            sleep 1
        done
        
        # 检查进程是否已经结束
        if ps -p $PID > /dev/null; then
            print_yellow "进程未响应停止信号，尝试强制终止..."
            kill -9 $PID 2>/dev/null
            sleep 1
        fi
        
        if ! ps -p $PID > /dev/null; then
            print_green "管理面板已成功停止"
            rm -f "$PID_FILE"
        else
            print_red "无法停止管理面板进程"
            exit 1
        fi
    else
        print_yellow "进程 $PID 已不存在，清理PID文件"
        rm -f "$PID_FILE"
    fi
else
    print_yellow "未找到PID文件，尝试查找管理面板进程..."
    
    # 尝试通过进程名称查找并停止
    ADMIN_PIDS=$(pgrep -f "python3 admin.py" 2>/dev/null)
    
    if [ -n "$ADMIN_PIDS" ]; then
        print_yellow "找到管理面板进程: $ADMIN_PIDS"
        
        for PID in $ADMIN_PIDS; do
            if kill -15 $PID 2>/dev/null; then
                print_green "已发送停止信号到进程 $PID"
                
                # 等待进程结束
                sleep 2
                
                # 检查进程是否已经结束
                if ps -p $PID > /dev/null; then
                    print_yellow "进程未响应停止信号，尝试强制终止..."
                    kill -9 $PID 2>/dev/null
                    sleep 1
                fi
                
                if ! ps -p $PID > /dev/null; then
                    print_green "进程 $PID 已成功停止"
                else
                    print_red "无法停止进程 $PID"
                fi
            else
                print_yellow "进程 $PID 已不存在"
            fi
        done
    else
        print_yellow "未找到运行中的管理面板进程"
    fi
fi

print_green "管理面板停止操作完成" 