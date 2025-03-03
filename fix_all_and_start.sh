#!/bin/bash

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== Telegram Bot 全面修复和启动工具 =====${NC}"
echo "此脚本将修复所有可能的问题并启动机器人"
echo ""

# 脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"
echo -e "${YELLOW}工作目录: $(pwd)${NC}"

# 确保脚本有执行权限
echo -e "${YELLOW}修复脚本权限...${NC}"
chmod +x start.sh
chmod +x fix_bot_error.py
chmod +x fix_redis.py
chmod +x fix_config.py
echo -e "${GREEN}✓ 权限修复完成${NC}"

# 修复配置文件中的循环导入问题
echo -e "${YELLOW}检查配置文件中的循环导入问题...${NC}"
# 直接在这里检查和修复循环导入问题
if grep -q "from config import DB_PATH" config.py; then
    echo "检测到循环导入问题，正在修复..."
    # 创建备份
    cp config.py config.py.bak
    # 修复循环导入
    sed -i 's/from config import DB_PATH/# 已修复循环导入问题/g' config.py
    echo -e "${GREEN}✓ 循环导入问题已修复${NC}"
else
    echo -e "${GREEN}✓ 未检测到循环导入问题${NC}"
fi

# 检查并创建数据目录
echo -e "${YELLOW}检查数据目录...${NC}"
mkdir -p "$SCRIPT_DIR/data"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 数据目录已创建/确认${NC}"
else
    echo -e "${RED}✗ 创建数据目录失败${NC}"
fi

# 确保按钮更新标志文件存在
echo -e "${YELLOW}检查按钮更新标志文件...${NC}"
BUTTON_FLAG="$SCRIPT_DIR/button_update.flag"
if [ ! -f "$BUTTON_FLAG" ]; then
    echo "创建按钮更新标志文件..."
    echo "$(date +%s)" > "$BUTTON_FLAG"
    echo -e "${GREEN}✓ 按钮更新标志文件已创建${NC}"
else
    echo -e "${GREEN}✓ 按钮更新标志文件已存在${NC}"
fi

# 运行Redis修复工具
echo -e "${YELLOW}运行Redis修复工具...${NC}"
python3 fix_redis.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Redis环境已检查和修复${NC}"
else
    echo -e "${YELLOW}! Redis修复可能未完全成功，但会继续尝试${NC}"
fi

# 运行机器人错误修复工具
echo -e "${YELLOW}运行机器人错误修复工具...${NC}"
python3 fix_bot_error.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 机器人代码已修复${NC}"
else
    echo -e "${YELLOW}! 机器人错误修复可能未完全成功，但会继续尝试${NC}"
fi

# 修复数据库文件权限
echo -e "${YELLOW}修复数据库文件权限...${NC}"
# 创建数据目录(如果不存在)
mkdir -p "$SCRIPT_DIR/data"
# 设置适当的权限
chmod -R 755 "$SCRIPT_DIR/data"
if [ -f "$SCRIPT_DIR/data/bot_data.db" ]; then
    chmod 644 "$SCRIPT_DIR/data/bot_data.db"
fi
echo -e "${GREEN}✓ 数据库文件权限已修复${NC}"

# 最终启动前检查
echo -e "${YELLOW}执行最终启动前检查...${NC}"

# 检查config.json文件
if [ ! -f "config.json" ]; then
    echo -e "${RED}警告: config.json文件不存在${NC}"
    echo "创建示例配置文件..."
    echo '{
  "token": "YOUR_BOT_TOKEN_HERE"
}' > config.json
    echo -e "${YELLOW}请编辑config.json文件，添加您的Telegram bot token${NC}"
    exit 1
fi

# 检查token是否设置
TOKEN=$(grep -o '"token"[^,}]*' config.json | grep -o '"[^"]*"$' | tr -d '"')
if [ "$TOKEN" = "YOUR_BOT_TOKEN_HERE" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}错误: 请在config.json中设置有效的bot token${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 所有检查已完成${NC}"
echo ""
echo -e "${BLUE}正在启动Telegram Bot服务...${NC}"
echo ""

# 运行机器人
if [ -x "$(command -v ./start.sh)" ]; then
    # 尝试使用start.sh脚本
    ./start.sh
else
    # 如果start.sh不可执行，直接启动服务
    echo -e "${YELLOW}start.sh不可执行，直接启动服务...${NC}"
    
    # 启动后台管理系统
    echo -e "${BLUE}正在启动后台管理系统...${NC}"
    python3 admin_web.py &
    ADMIN_PID=$!
    
    # 等待几秒钟确保后台系统已启动
    echo "等待后台系统启动..."
    sleep 3
    
    # 启动机器人
    echo -e "${BLUE}正在启动 Telegram 机器人...${NC}"
    python3 bot.py &
    BOT_PID=$!
    
    # 捕获 SIGINT 信号（Ctrl+C）
    trap "echo -e '${YELLOW}正在关闭服务...${NC}'; kill $ADMIN_PID $BOT_PID; exit" INT
    
    # 等待用户按 Ctrl+C
    echo -e "${GREEN}服务已启动。${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止服务。${NC}"
    echo ""
    echo "管理后台地址: http://localhost:5000"
    echo ""
    
    wait
fi 