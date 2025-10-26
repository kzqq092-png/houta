"""简单运行验证并显示结果"""
import subprocess
import sys

result = subprocess.run([sys.executable, "verify_distributed_integration.py"], 
                       capture_output=True, text=True, encoding='utf-8')

# 只显示最后的汇总部分
lines = result.stdout.split('\n')
start_idx = -1
for i, line in enumerate(lines):
    if '测试结果汇总' in line:
        start_idx = i - 2
        break

if start_idx >= 0:
    for line in lines[start_idx:]:
        print(line)
else:
    print("未找到测试结果汇总")
    print(result.stdout[-2000:])  # 显示最后2000字符

sys.exit(result.returncode)

