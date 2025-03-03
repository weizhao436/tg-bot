#!/usr/bin/env python3
"""
修复bot.py中的语法错误 - 未闭合的try块
"""
import os
import sys

def fix_syntax_error():
    """修复bot.py中的语法错误"""
    print("开始修复bot.py中的语法错误...")
    
    # 检查文件是否存在
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"错误: 找不到 {bot_file} 文件")
        return False
    
    # 读取文件内容
    with open(bot_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 创建备份
    backup_file = f"{bot_file}.syntax.bak"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"已创建备份: {backup_file}")
    
    # 寻找问题
    in_try_block = False
    unclosed_try = False
    try_start_line = -1
    
    # 首先检查是否存在未闭合的try块
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("try:"):
            in_try_block = True
            try_start_line = i
        elif in_try_block and (stripped.startswith("except") or stripped.startswith("finally:")):
            in_try_block = False
        elif in_try_block and stripped.startswith("if __name__ == '__main__'"):
            unclosed_try = True
            print(f"发现未闭合的try块，开始于{try_start_line+1}行，到{i+1}行仍未关闭")
            break
    
    if not unclosed_try:
        print("未发现语法错误或未闭合的try块")
        # 尝试寻找其他潜在问题
        for i, line in enumerate(lines):
            if "if __name__ == '__main__'" in line:
                print(f"'if __name__'语句位于第{i+1}行")
                # 检查前后几行是否有问题
                for j in range(max(0, i-5), min(len(lines), i+5)):
                    print(f"行 {j+1}: {lines[j].rstrip()}")
        return False
    
    # 修复未闭合的try块
    print("正在修复未闭合的try块...")
    fixed_lines = []
    in_try_block = False
    fixed = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 如果遇到if __name__但在try块内，先添加一个except
        if in_try_block and stripped.startswith("if __name__ == '__main__'"):
            # 确定适当的缩进
            indent = ""
            for char in line:
                if char.isspace():
                    indent += char
                else:
                    break
            
            # 添加除了try之外的缩进级别
            # 通常try块内的代码会有额外的缩进
            try_indent = ""
            for char in lines[try_start_line]:
                if char.isspace():
                    try_indent += char
                else:
                    break
            
            # 添加missing except和finally
            fixed_lines.append(f"{try_indent}except Exception as e:\n")
            fixed_lines.append(f"{try_indent}    print(f\"未捕获的异常: {{e}}\")\n")
            fixed_lines.append(f"{try_indent}    raise\n")
            fixed_lines.append("\n")
            
            fixed = True
            in_try_block = False
        
        fixed_lines.append(line)
        
        if stripped.startswith("try:"):
            in_try_block = True
            try_start_line = i
        elif in_try_block and (stripped.startswith("except") or stripped.startswith("finally:")):
            in_try_block = False
    
    # 保存修复后的文件
    if fixed:
        with open(bot_file, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print("✅ 语法错误已修复")
        return True
    else:
        print("❌ 未能修复语法错误")
        return False

if __name__ == "__main__":
    if fix_syntax_error():
        print("修复完成，请尝试重新运行bot.py")
    else:
        print("未能修复语法错误，可能需要手动检查bot.py文件") 