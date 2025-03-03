#!/usr/bin/env python3
"""
用于修复bot.py中潜在的错误
"""
import os
import sys
import re

def main():
    print("Telegram Bot 错误修复工具")
    print("========================")
    
    # 检查bot.py是否存在
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"错误: {bot_file} 不存在")
        return False
    
    # 读取文件内容
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 创建备份
    backup_file = f"{bot_file}.bak"
    print(f"创建备份文件: {backup_file}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 修复1: 确保BUTTON_UPDATE_FLAG初始化正确
    if "BUTTON_UPDATE_FLAG" in content:
        print("检查BUTTON_UPDATE_FLAG初始化...")
        # 确保按钮更新标志文件存在
        flag_path = os.path.join(os.path.dirname(__file__), 'button_update.flag')
        if not os.path.exists(flag_path):
            print(f"创建按钮更新标志文件: {flag_path}")
            with open(flag_path, 'w') as f:
                f.write(str(os.path.getmtime(__file__)))
    
    # 修复2: 添加异常捕获和详细日志记录
    print("添加更详细的错误处理...")
    
    # 确保日志级别设置为DEBUG
    content = re.sub(
        r'level=logging\.(INFO|WARNING|ERROR)', 
        r'level=logging.DEBUG',
        content
    )
    
    # 在main函数中添加更详细的异常处理
    # 寻找main函数定义
    main_func_match = re.search(r'def main\(\):[^\n]*\n', content)
    if main_func_match:
        print("修改main函数以添加更详细的异常处理...")
        main_func_start = main_func_match.start()
        
        # 找到main函数体开始的缩进级别
        indentation = re.search(r'\n(\s+)', content[main_func_start:]).group(1)
        
        # 构建需要插入的异常处理代码
        exception_handling = f'''def main():
{indentation}# 添加全局异常处理
{indentation}try:
'''
        
        # 将原函数体缩进一级
        main_body = content[main_func_start + len(main_func_match.group(0)):]
        # 分割main函数体和后续代码
        next_def_match = re.search(r'\ndef ', main_body)
        if next_def_match:
            main_body_end = next_def_match.start()
            after_main = main_body[main_body_end:]
            main_body = main_body[:main_body_end]
        else:
            after_main = ""
        
        # 增加缩进
        main_body = main_body.replace('\n' + indentation, '\n' + indentation + '    ')
        
        # 添加异常处理的结束部分
        main_body += f'''
{indentation}except Exception as e:
{indentation}    logger.critical(f"机器人运行时发生严重错误: {{e}}")
{indentation}    logger.critical("详细错误信息:", exc_info=True)
{indentation}    import traceback
{indentation}    error_msg = traceback.format_exc()
{indentation}    with open("bot_error.log", "w") as error_file:
{indentation}        error_file.write(error_msg)
{indentation}    logger.critical(f"错误信息已保存到 bot_error.log 文件")
{indentation}    raise  # 重新抛出异常以便系统可以看到详细信息
'''
        
        # 重新组合代码
        new_content = content[:main_func_start] + exception_handling + main_body + after_main
        
        # 保存修改后的文件
        with open(bot_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"已修改 {bot_file} 以添加更详细的错误处理")
        return True
    else:
        print(f"警告: 无法在 {bot_file} 中找到main函数")
        return False

if __name__ == "__main__":
    if main():
        print("修复完成，请重新运行 bot.py")
    else:
        print("修复失败，请手动检查 bot.py 文件") 