#!/bin/bash

# 数据库修复和启动脚本
# 用于修复数据库问题并启动服务

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Telegram Bot 修复和启动工具 ===${NC}"
echo "此脚本将修复数据库问题并启动服务"
echo ""

# 当前脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 确保数据目录存在
echo -e "${YELLOW}正在检查数据目录...${NC}"
mkdir -p "$SCRIPT_DIR/data"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 数据目录已创建/确认${NC}"
else
    echo -e "${RED}✗ 创建数据目录失败${NC}"
    exit 1
fi

# 修复数据库权限
echo -e "${YELLOW}正在设置目录权限...${NC}"
chmod -R 755 "$SCRIPT_DIR/data"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 权限设置成功${NC}"
else
    echo -e "${RED}✗ 权限设置失败，可能需要更高权限${NC}"
    echo "您可能需要手动执行: sudo chmod -R 755 $SCRIPT_DIR/data"
fi

# 运行数据库修复脚本
echo -e "${YELLOW}正在运行数据库修复脚本...${NC}"
python fix_db.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 数据库修复成功${NC}"
else
    echo -e "${RED}✗ 数据库修复失败${NC}"
    echo "请检查错误信息并手动解决问题"
    exit 1
fi

# 检查Redis服务是否运行
echo -e "${YELLOW}正在检查Redis服务...${NC}"
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis服务正在运行${NC}"
    else
        echo -e "${YELLOW}! Redis服务未运行，尝试启动...${NC}"
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ Redis服务已启动${NC}"
            else
                echo -e "${RED}✗ Redis服务启动失败${NC}"
                echo "将使用传统文件监控方式进行按钮更新"
            fi
        else
            echo -e "${YELLOW}! Redis服务未安装${NC}"
            echo "将使用传统文件监控方式进行按钮更新"
        fi
    fi
else
    echo -e "${YELLOW}! Redis客户端未安装${NC}"
    echo "将使用传统文件监控方式进行按钮更新"
fi

# 确保button_update.flag文件存在
echo -e "${YELLOW}正在创建按钮更新标志文件...${NC}"
touch "$SCRIPT_DIR/button_update.flag"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 按钮更新标志文件已创建${NC}"
else
    echo -e "${RED}✗ 创建按钮更新标志文件失败${NC}"
fi

# 创建启动脚本
echo -e "${YELLOW}正在准备启动服务...${NC}"
echo "初始化完成，现在将启动服务"
echo ""

# 启动后台管理系统
echo -e "${BLUE}正在启动后台管理系统...${NC}"
python admin_web.py &
ADMIN_PID=$!

# 等待几秒钟确保后台系统已启动
echo "等待后台系统启动..."
sleep 3

# 启动机器人
echo -e "${BLUE}正在启动 Telegram 机器人...${NC}"
python bot.py &
BOT_PID=$!

# 捕获 SIGINT 信号（Ctrl+C）
trap "echo -e '${YELLOW}正在关闭服务...${NC}'; kill $ADMIN_PID $BOT_PID; exit" INT

# 等待用户按 Ctrl+C
echo -e "${GREEN}服务已启动。${NC}"
echo -e "${YELLOW}按 Ctrl+C 停止服务。${NC}"
echo ""
echo "管理后台地址: http://localhost:5000"
echo "用户名: $ADMIN_USERNAME (默认: admin)"
echo "密码: $ADMIN_PASSWORD (默认: password)"
echo ""

wait 