#!/usr/bin/env python3
"""
创建新版本的bot.py，修复语法错误
"""
import os
import shutil

def create_new_bot():
    print("创建新版本的bot.py...")
    
    # 检查原始文件
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"错误: 找不到 {bot_file}")
        return False
    
    # 创建备份
    backup_file = f"{bot_file}.full.bak"
    shutil.copy2(bot_file, backup_file)
    print(f"已创建完整备份: {backup_file}")
    
    # 读取文件
    with open(bot_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到if __name__行
    if_name_line = -1
    for i, line in enumerate(lines):
        if "if __name__ == '__main__':" in line:
            if_name_line = i
            break
    
    if if_name_line == -1:
        print("未找到if __name__行，无法修复")
        return False
    
    # 找到main函数
    main_line = -1
    for i, line in enumerate(lines):
        if "def main():" in line:
            main_line = i
            break
    
    if main_line == -1:
        print("未找到main函数，无法修复")
        return False
    
    # 从头开始创建新文件，直到main函数定义
    new_lines = lines[:main_line + 1]
    
    # 创建一个安全的main函数
    main_indent = len(lines[main_line]) - len(lines[main_line].lstrip())
    indent = ' ' * (main_indent + 4)
    
    new_lines.append(indent + "# 完全重写的main函数体\n")
    new_lines.append(indent + "try:\n")
    new_lines.append(indent + "    # 测试数据库连接\n")
    new_lines.append(indent + "    try:\n")
    new_lines.append(indent + "        conn = sqlite3.connect(DB_PATH)\n")
    new_lines.append(indent + "        print(\"✅ 数据库连接成功\")\n")
    new_lines.append(indent + "        conn.close()\n")
    new_lines.append(indent + "    except Exception as e:\n")
    new_lines.append(indent + "        print(f\"❌ 数据库连接失败: {str(e)}\")\n")
    new_lines.append(indent + "        return\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 测试Redis连接\n")
    new_lines.append(indent + "    try:\n")
    new_lines.append(indent + "        if redis_client:\n")
    new_lines.append(indent + "            redis_client.ping()\n")
    new_lines.append(indent + "            print(\"✅ Redis连接成功\")\n")
    new_lines.append(indent + "    except Exception as e:\n")
    new_lines.append(indent + "        print(f\"❌ Redis连接失败: {str(e)}\")\n")
    new_lines.append(indent + "        print(\"将使用文件监控方式进行按钮更新\")\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 创建锁文件\n")
    new_lines.append(indent + "    try:\n")
    new_lines.append(indent + "        lock_file = open(\"/tmp/telegram_bot.lock\", \"w\")\n")
    new_lines.append(indent + "        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)\n")
    new_lines.append(indent + "    except IOError:\n")
    new_lines.append(indent + "        logger.error(\"另一个机器人实例已经在运行\")\n")
    new_lines.append(indent + "        sys.exit(1)\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 初始化Redis\n")
    new_lines.append(indent + "    redis_success = init_redis()\n")
    new_lines.append(indent + "    if redis_success:\n")
    new_lines.append(indent + "        # 启动Redis订阅线程\n")
    new_lines.append(indent + "        subscriber_thread = threading.Thread(target=redis_subscriber, daemon=True)\n")
    new_lines.append(indent + "        subscriber_thread.start()\n")
    new_lines.append(indent + "        logger.info(\"已启动Redis订阅线程\")\n")
    new_lines.append(indent + "    else:\n")
    new_lines.append(indent + "        logger.warning(\"Redis初始化失败，将使用文件监控方式检查按钮更新\")\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 从配置文件读取token\n")
    new_lines.append(indent + "    try:\n")
    new_lines.append(indent + "        with open('config.json', 'r') as f:\n")
    new_lines.append(indent + "            config = json.load(f)\n")
    new_lines.append(indent + "            token = config.get('token', BOT_TOKEN)\n")
    new_lines.append(indent + "    except Exception as e:\n")
    new_lines.append(indent + "        logger.error(f\"读取配置文件时出错: {e}\")\n")
    new_lines.append(indent + "        token = BOT_TOKEN\n")
    new_lines.append("\n")
    new_lines.append(indent + "    if not token:\n")
    new_lines.append(indent + "        logger.error(\"未找到有效的机器人token\")\n")
    new_lines.append(indent + "        sys.exit(1)\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 设置数据库\n")
    new_lines.append(indent + "    setup_database()\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 创建Application\n")
    new_lines.append(indent + "    defaults = Defaults(parse_mode='HTML')\n")
    new_lines.append(indent + "    application = Application.builder().token(token).defaults(defaults).build()\n")
    new_lines.append(indent + "    logger.info(\"成功创建Application实例\")\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 保存全局应用实例\n")
    new_lines.append(indent + "    set_application_instance(application)\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 添加处理程序\n")
    new_lines.append(indent + "    job_queue = application.job_queue\n")
    new_lines.append(indent + "    job_queue.run_repeating(check_updates, interval=10, first=5)\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 添加命令处理程序\n")
    new_lines.append(indent + "    application.add_handler(CommandHandler(\"start\", start))\n")
    new_lines.append(indent + "    application.add_handler(CommandHandler(\"help\", help_command))\n")
    new_lines.append(indent + "    application.add_handler(CommandHandler(\"refresh\", refresh_command))\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 添加错误处理程序\n")
    new_lines.append(indent + "    application.add_error_handler(error_handler)\n")
    new_lines.append("\n")
    new_lines.append(indent + "    # 启动机器人\n")
    new_lines.append(indent + "    logger.info(\"开始运行机器人...\")\n")
    new_lines.append(indent + "    application.run_polling(drop_pending_updates=True)\n")
    new_lines.append("\n")
    new_lines.append(indent + "except Exception as e:\n")
    new_lines.append(indent + "    logger.error(f\"初始化机器人时发生错误: {e}\")\n")
    new_lines.append(indent + "    import traceback\n")
    new_lines.append(indent + "    logger.error(traceback.format_exc())\n")
    new_lines.append(indent + "    raise\n")
    new_lines.append("\n")
    
    # 添加if __name__块
    new_lines.append(lines[if_name_line])  # if __name__ == '__main__':
    for line in lines[if_name_line + 1:]:
        new_lines.append(line)
    
    # 保存新版本
    new_bot_file = "bot_fixed.py"
    with open(new_bot_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"已创建新版本: {new_bot_file}")
    print("请使用以下命令运行新版本:")
    print("  python3 bot_fixed.py")
    
    # 创建一个启动脚本
    start_script = "start_fixed.sh"
    with open(start_script, 'w', encoding='utf-8') as f:
        f.write("#!/bin/bash\n\n")
        f.write("# 检查Redis服务\n")
        f.write("echo \"检查Redis服务...\"\n")
        f.write("if command -v redis-cli > /dev/null; then\n")
        f.write("    if ! redis-cli ping > /dev/null 2>&1; then\n")
        f.write("        echo \"Redis服务未运行，尝试启动...\"\n")
        f.write("        if command -v redis-server > /dev/null; then\n")
        f.write("            redis-server --daemonize yes\n")
        f.write("            echo \"Redis服务已启动\"\n")
        f.write("        fi\n")
        f.write("    else\n")
        f.write("        echo \"Redis服务正在运行\"\n")
        f.write("    fi\n")
        f.write("fi\n\n")
        f.write("# 启动后台管理系统\n")
        f.write("echo \"启动后台管理系统...\"\n")
        f.write("python3 admin_web.py &\n")
        f.write("ADMIN_PID=$!\n\n")
        f.write("# 等待几秒钟确保后台系统已启动\n")
        f.write("sleep 3\n\n")
        f.write("# 启动机器人\n")
        f.write("echo \"启动Telegram机器人...\"\n")
        f.write("python3 bot_fixed.py &\n")
        f.write("BOT_PID=$!\n\n")
        f.write("# 捕获SIGINT信号（Ctrl+C）\n")
        f.write("trap \"echo '正在关闭服务...'; kill $ADMIN_PID $BOT_PID; exit\" INT\n\n")
        f.write("# 等待用户按Ctrl+C\n")
        f.write("echo \"服务已启动。按Ctrl+C停止服务。\"\n")
        f.write("wait\n")
    
    os.chmod(start_script, 0o755)  # 添加执行权限
    print(f"已创建启动脚本: {start_script}")
    print(f"使用以下命令启动服务:")
    print(f"  ./{start_script}")
    
    return True

if __name__ == "__main__":
    create_new_bot() 