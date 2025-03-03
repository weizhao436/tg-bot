#!/bin/bash

# 创建临时目录
TEMP_DIR="/tmp/telegram_bot_package"
mkdir -p $TEMP_DIR

# 复制所有必要文件
cp -r /opt/telegram_bot/*.py $TEMP_DIR/
cp -r /opt/telegram_bot/templates $TEMP_DIR/
cp -r /opt/telegram_bot/static $TEMP_DIR/

# 创建必要的目录
mkdir -p $TEMP_DIR/static/uploads

# 创建 README 文件
cat > $TEMP_DIR/README.md << 'EOF'
# Telegram 机器人后台管理系统

这是一个用于管理 Telegram 机器人的后台系统，可以通过 Web 界面轻松管理机器人的按钮和回复内容。

## 安装步骤

1. 确保已安装 Python 3.7+ 和 pip
2. 安装依赖：
   ```
   pip install python-telegram-bot flask flask-login flask-wtf
   ```

3. 修改 config.py 中的配置：
   - 设置安全的 SECRET_KEY
   - 设置管理员用户名和密码
   - 设置您的 Telegram 机器人 TOKEN

4. 运行后台管理系统：
   ```
   python admin_web.py
   ```

5. 在另一个终端运行机器人：
   ```
   python bot.py
   ```

6. 访问后台管理系统：
   - 打开浏览器，访问 http://localhost:5000
   - 使用配置的管理员用户名和密码登录

## 文件结构

- admin_web.py - 后台管理 Web 服务器
- bot.py - Telegram 机器人主程序
- config.py - 配置文件
- templates/ - HTML 模板
- static/ - 静态文件（CSS、JS）

## 功能

- 管理机器人按钮：添加、编辑、删除键盘按钮
- 管理回复内容：设置触发词和对应的回复
- 支持图片回复：可以为回复添加图片
- 用户统计：查看用户数量和活跃度

## 注意事项

- 确保 bot_data.db 文件有写入权限
- 首次运行时会自动创建数据库和默认内容
- 修改配置后需要重启服务

EOF

# 创建启动脚本
cat > $TEMP_DIR/start.sh << 'EOF'
#!/bin/bash

# 启动后台管理系统
echo "启动后台管理系统..."
python admin_web.py &
ADMIN_PID=$!

# 等待几秒钟确保后台系统已启动
sleep 3

# 启动机器人
echo "启动 Telegram 机器人..."
python bot.py &
BOT_PID=$!

# 捕获 SIGINT 信号（Ctrl+C）
trap "echo '正在关闭服务...'; kill $ADMIN_PID $BOT_PID; exit" INT

# 等待用户按 Ctrl+C
echo "服务已启动。按 Ctrl+C 停止服务。"
wait
EOF

# 添加执行权限
chmod +x $TEMP_DIR/start.sh

# 创建 ZIP 文件
cd /tmp
zip -r telegram_bot_package.zip telegram_bot_package

# 移动到桌面
mv telegram_bot_package.zip ~/Desktop/

# 清理临时目录
rm -rf $TEMP_DIR

echo "打包完成！文件已保存到桌面：telegram_bot_package.zip" 