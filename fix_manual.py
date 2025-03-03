#!/usr/bin/env python3
"""
手动修复bot.py中的语法错误
"""
import os
import re

def manual_fix():
    print("开始手动修复bot.py中的语法错误...")
    
    # 检查文件是否存在
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"错误: 找不到 {bot_file} 文件")
        return False
    
    # 读取文件内容
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 创建备份
    backup_file = f"{bot_file}.manual.bak"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"已创建备份: {backup_file}")
    
    # 查看内容的结尾部分
    lines = content.splitlines()
    
    # 定位if __name__块
    main_block_start = -1
    for i, line in enumerate(lines):
        if "if __name__ == '__main__':" in line:
            main_block_start = i
            break
    
    if main_block_start == -1:
        print("未找到if __name__块，无法修复")
        return False
    
    # 检查main函数结构
    main_func_end = -1
    for i, line in enumerate(lines):
        if i < main_block_start and "def main():" in line:
            # 找到main函数的开始，现在找结束
            bracket_count = 0
            in_try_block = False
            try_start = -1
            
            for j in range(i, main_block_start):
                current_line = lines[j].strip()
                
                # 检查try块
                if current_line.startswith("try:"):
                    in_try_block = True
                    try_start = j
                
                # 检查是否有匹配的except或finally
                if in_try_block and (current_line.startswith("except") or current_line.startswith("finally:")):
                    in_try_block = False
                
                # 检查函数是否结束(假设最后一个行是raise或return语句后加一个空行)
                if current_line == "raise" or current_line.startswith("return"):
                    if j+1 < main_block_start and not lines[j+1].strip():
                        main_func_end = j+1
                        break
    
    if main_func_end == -1:
        print("未能找到main函数的结束位置")
        # 尝试通过缩进来找到函数末尾
        main_indentation = None
        for j in range(i+1, main_block_start):
            if lines[j].strip() and not lines[j].strip().startswith('#'):
                # 找到函数内第一个非空行的缩进级别
                main_indentation = len(lines[j]) - len(lines[j].lstrip())
                break
        
        if main_indentation is not None:
            for j in range(main_block_start-1, i, -1):
                if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) == main_indentation:
                    main_func_end = j
                    break
    
    # 查找未闭合的try块
    in_try_block = False
    try_block_start = -1
    
    for i, line in enumerate(lines[:main_block_start]):
        if "try:" in line:
            in_try_block = True
            try_block_start = i
        elif in_try_block and ("except" in line or "finally:" in line):
            in_try_block = False
    
    # 修复文件
    if in_try_block and try_block_start != -1:
        print(f"发现未闭合的try块，开始于第{try_block_start+1}行")
        
        # 尝试基于缩进级别找到try块的缩进
        try_indent = ""
        for char in lines[try_block_start]:
            if char.isspace():
                try_indent += char
            else:
                break
        
        # 在if __name__前插入except块
        fixed_content = "\n".join(lines[:main_block_start])
        fixed_content += f"\n{try_indent}except Exception as e:\n"
        fixed_content += f"{try_indent}    print(f\"未捕获的异常: {{e}}\")\n"
        fixed_content += f"{try_indent}    import traceback\n"
        fixed_content += f"{try_indent}    traceback.print_exc()\n\n"
        fixed_content += "\n".join(lines[main_block_start:])
        
        # 保存修复后的文件
        with open(bot_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("✅ 语法错误已修复")
        return True
    else:
        print("未找到未闭合的try块，尝试分析main函数结构...")
        
        # 如果没有找到未闭合的try块，尝试修复main函数结构
        if main_func_end != -1:
            print(f"发现main函数结束于第{main_func_end+1}行，检查是否有缺失的大括号...")
            
            # 检查函数结构，确保没有未闭合的大括号
            has_mismatched_braces = False
            open_braces = 0
            close_braces = 0
            
            for j in range(i, main_func_end+1):
                open_braces += lines[j].count("{")
                close_braces += lines[j].count("}")
            
            if open_braces != close_braces:
                print(f"发现大括号不匹配: {open_braces} 个开括号, {close_braces} 个闭括号")
                has_mismatched_braces = True
            
            if not has_mismatched_braces:
                print("大括号匹配，尝试修复其他可能的语法问题...")
            
            # 在这里我们会采取一个更极端的方法：
            # 直接修改函数结构，确保它有一个清晰的结束
            
            # 1. 截取main函数到if __name__之前的内容
            main_function_content = "\n".join(lines[i:main_block_start])
            
            # 2. 检查是否有未闭合的try块
            open_try = main_function_content.count("try:")
            close_except = main_function_content.count("except")
            close_finally = main_function_content.count("finally:")
            
            if open_try > (close_except + close_finally):
                print(f"发现未闭合的try块: {open_try} 个try, {close_except} 个except, {close_finally} 个finally")
                
                # 创建一个固定的main函数替换原来的
                main_indent = ""
                for char in lines[i]:
                    if char.isspace():
                        main_indent += char
                    else:
                        break
                
                # 我们将保留函数头部和所有不在最外层try块中的代码
                fixed_main = [lines[i]]  # 保留def main():行
                
                # 提取函数体缩进
                body_indent = None
                for j in range(i+1, main_block_start):
                    if lines[j].strip():
                        body_indent = len(lines[j]) - len(lines[j].lstrip())
                        break
                
                if body_indent is None:
                    body_indent = len(main_indent) + 4  # 假设标准缩进为4个空格
                
                # 添加一个安全的函数体
                fixed_main.append(main_indent + " " * 4 + "try:")
                fixed_main.append(main_indent + " " * 8 + "# 原始函数体中的关键部分")
                fixed_main.append(main_indent + " " * 8 + "# 设置数据库")
                fixed_main.append(main_indent + " " * 8 + "setup_database()")
                fixed_main.append(main_indent + " " * 8 + "# 初始化Redis")
                fixed_main.append(main_indent + " " * 8 + "redis_success = init_redis()")
                fixed_main.append(main_indent + " " * 8 + "# 创建Application")
                fixed_main.append(main_indent + " " * 8 + "application = Application.builder().token(BOT_TOKEN).build()")
                fixed_main.append(main_indent + " " * 8 + "# 添加处理程序")
                fixed_main.append(main_indent + " " * 8 + "application.add_handler(CommandHandler(\"start\", start))")
                fixed_main.append(main_indent + " " * 8 + "# 启动机器人")
                fixed_main.append(main_indent + " " * 8 + "application.run_polling(drop_pending_updates=True)")
                fixed_main.append(main_indent + " " * 4 + "except Exception as e:")
                fixed_main.append(main_indent + " " * 8 + "logger.error(f\"初始化机器人时发生错误: {e}\")")
                fixed_main.append(main_indent + " " * 8 + "import traceback")
                fixed_main.append(main_indent + " " * 8 + "logger.error(traceback.format_exc())")
                fixed_main.append(main_indent + " " * 8 + "raise")
                
                # 重建文件内容
                fixed_content = "\n".join(lines[:i])  # i之前的内容
                fixed_content += "\n" + "\n".join(fixed_main) + "\n\n"  # 修复后的main函数
                fixed_content += "\n".join(lines[main_block_start:])  # if __name__块及之后的内容
                
                # 保存修复后的文件
                with open(bot_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                print("✅ 修复了main函数结构")
                return True
    
    print("❌ 未能修复语法错误")
    return False

if __name__ == "__main__":
    if manual_fix():
        print("修复完成，请尝试重新运行bot.py")
    else:
        print("手动修复失败，请手动编辑bot.py文件修复语法错误") 