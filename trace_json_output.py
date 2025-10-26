"""追踪神秘的JSON输出来源"""
import sys
import traceback
from io import StringIO


class OutputTracker:
    """追踪所有输出，特别是JSON格式的输出"""

    def __init__(self, original_stream, stream_name):
        self.original = original_stream
        self.stream_name = stream_name
        self.buffer = []

    def write(self, text):
        """拦截write调用"""
        # 检查是否包含可疑的JSON输出
        if text and isinstance(text, str):
            # 检测JSON模式
            suspicious = False
            if '{' in text and '}' in text:
                if 'result' in text.lower() or 'error' in text.lower():
                    suspicious = True

            if suspicious:
                # 捕获堆栈跟踪
                print("\n" + "="*80, file=self.original)
                print(f"[{self.stream_name}] 检测到可疑JSON输出:", file=self.original)
                print("="*80, file=self.original)
                print(f"内容: {text!r}", file=self.original)
                print("-"*80, file=self.original)
                print("调用堆栈:", file=self.original)
                for line in traceback.format_stack()[:-1]:
                    print(line.rstrip(), file=self.original)
                print("="*80 + "\n", file=self.original)

        # 写入原始流
        return self.original.write(text)

    def flush(self):
        """刷新缓冲区"""
        if hasattr(self.original, 'flush'):
            return self.original.flush()

    def __getattr__(self, name):
        """代理其他属性到原始流"""
        return getattr(self.original, name)


# 保存原始流
original_stdout = sys.stdout
original_stderr = sys.stderr

# 安装追踪器
sys.stdout = OutputTracker(original_stdout, "STDOUT")
sys.stderr = OutputTracker(original_stderr, "STDERR")

print("[OutputTracker] 已安装输出追踪器")
print("[OutputTracker] 开始监控所有stdout和stderr输出")
print("[OutputTracker] 特别关注包含'result'和'error'的JSON输出")
print()

# 导入并运行main
try:
    import main
    print("\n[OutputTracker] main模块导入完成")
except Exception as e:
    print(f"\n[OutputTracker] main模块导入失败: {e}")
    traceback.print_exc()
