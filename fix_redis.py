#!/usr/bin/env python3
"""
用于测试和修复Redis连接问题
"""
import os
import sys
import time
import socket
import subprocess

def check_redis_service():
    """检查Redis服务是否运行"""
    print("正在检查Redis服务...")
    
    # 尝试连接Redis默认端口
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("localhost", 6379))
        s.close()
        print("✅ Redis服务正在运行")
        return True
    except Exception:
        print("❌ Redis服务未运行")
        s.close()
        return False

def start_redis_service():
    """尝试启动Redis服务"""
    print("尝试启动Redis服务...")
    
    try:
        # 检查redis-server命令是否存在
        result = subprocess.run(
            ["which", "redis-server"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print("❌ Redis服务器未安装，请安装Redis:")
            print("    在Ubuntu上: apt-get install redis-server")
            print("    在CentOS上: yum install redis")
            print("    在macOS上: brew install redis")
            return False
        
        # 尝试启动Redis服务
        subprocess.run(
            ["redis-server", "--daemonize", "yes"],
            check=True
        )
        
        # 等待服务启动
        print("等待Redis服务启动...")
        time.sleep(2)
        
        # 再次检查是否运行
        if check_redis_service():
            print("✅ Redis服务已成功启动")
            return True
        else:
            print("❌ Redis服务启动失败")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动Redis服务时出错: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        return False

def modify_bot_to_handle_missing_redis():
    """修改bot.py以优雅地处理缺少Redis的情况"""
    print("修改bot.py以处理Redis不可用的情况...")
    
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"❌ 找不到{bot_file}文件")
        return False
    
    # 读取文件内容
    with open(bot_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 创建备份
    with open(f"{bot_file}.redis.bak", 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # 在init_redis函数中寻找失败后可能缺少回退的代码
    init_redis_start = -1
    init_redis_end = -1
    for i, line in enumerate(lines):
        if "def init_redis()" in line:
            init_redis_start = i
        elif init_redis_start > 0 and line.startswith("def "):
            init_redis_end = i
            break
    
    if init_redis_start > 0 and init_redis_end > 0:
        # 寻找在连接失败时的处理逻辑
        has_proper_fallback = False
        for i in range(init_redis_start, init_redis_end):
            if "return False" in lines[i] and any(x in lines[i-1].lower() for x in ["exception", "error", "except"]):
                has_proper_fallback = True
                break
        
        if not has_proper_fallback:
            print("修改init_redis函数以添加更好的错误处理...")
            
            # 找到缩进级别
            indentation = ""
            for i in range(init_redis_start + 1, init_redis_end):
                if lines[i].strip():
                    indentation = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
                    break
            
            # 修改函数以添加更好的错误处理
            new_function = []
            in_except_block = False
            for i in range(init_redis_start, init_redis_end):
                line = lines[i]
                
                # 跳过现有的except块
                if "except" in line:
                    in_except_block = True
                    continue
                if in_except_block and line.strip() and not line.strip().startswith("#"):
                    if "return" in line:
                        in_except_block = False
                    else:
                        continue
                
                new_function.append(line)
                
                # 在try块后添加我们自己的except块
                if "try:" in line:
                    new_function.append(f"{indentation}    redis_client = redis.Redis(\n")
                    new_function.append(f"{indentation}        host=REDIS_HOST,\n")
                    new_function.append(f"{indentation}        port=REDIS_PORT,\n")
                    new_function.append(f"{indentation}        db=REDIS_DB,\n")
                    new_function.append(f"{indentation}        password=REDIS_PASSWORD,\n")
                    new_function.append(f"{indentation}        socket_timeout=2,  # 添加超时以防止长时间挂起\n")
                    new_function.append(f"{indentation}        socket_connect_timeout=2  # 连接超时\n")
                    new_function.append(f"{indentation}    )\n")
                    new_function.append(f"{indentation}    # 测试连接\n")
                    new_function.append(f"{indentation}    redis_client.ping()\n")
                    new_function.append(f"{indentation}    logger.info(\"Redis客户端初始化成功\")\n")
                    new_function.append(f"{indentation}    return True\n")
                    new_function.append(f"{indentation}except redis.ConnectionError as e:\n")
                    new_function.append(f"{indentation}    logger.warning(f\"Redis连接错误: {{e}}\")\n")
                    new_function.append(f"{indentation}    logger.warning(\"将使用文件监控方式替代Redis\")\n")
                    new_function.append(f"{indentation}    return False\n")
                    new_function.append(f"{indentation}except redis.RedisError as e:\n")
                    new_function.append(f"{indentation}    logger.error(f\"Redis错误: {{e}}\")\n")
                    new_function.append(f"{indentation}    return False\n")
                    new_function.append(f"{indentation}except Exception as e:\n")
                    new_function.append(f"{indentation}    logger.error(f\"Redis客户端初始化失败: {{e}}\")\n")
                    new_function.append(f"{indentation}    return False\n")
            
            # 替换原始函数
            lines[init_redis_start:init_redis_end] = new_function
            
            # 保存修改后的文件
            with open(bot_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print("✅ 已修改init_redis函数以添加更好的错误处理")
            return True
        else:
            print("ℹ️ init_redis函数已有适当的错误处理")
            return True
    else:
        print("❌ 无法在bot.py中找到init_redis函数")
        return False

def main():
    print("===== Redis连接修复工具 =====")
    
    # 检查Redis服务
    if not check_redis_service():
        # 尝试启动Redis服务
        if not start_redis_service():
            # 如果无法启动Redis，修改bot.py以处理这种情况
            modify_bot_to_handle_missing_redis()
            print("\n总结: Redis服务未运行，已修改bot.py以优雅地处理这种情况")
            print("机器人将使用文件监控方式代替Redis")
        else:
            print("\n总结: Redis服务已成功启动")
    else:
        print("\n总结: Redis服务正常运行，无需修复")
    
    # 创建按钮更新标志文件
    flag_path = os.path.join(os.path.dirname(__file__), 'button_update.flag')
    if not os.path.exists(flag_path):
        print(f"创建按钮更新标志文件: {flag_path}")
        with open(flag_path, 'w') as f:
            f.write(str(time.time()))
    
    print("\n修复完成。请使用以下命令启动机器人:")
    print("  python3 bot.py")

if __name__ == "__main__":
    main() 