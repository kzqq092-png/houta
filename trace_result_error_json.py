"""
精确追踪 {"result": "error"} JSON输出的来源

策略：
1. Hook所有可能的输出函数
2. 检查输出内容是否包含目标JSON
3. 捕获完整的调用堆栈
"""
import sys
import json
import traceback
from io import StringIO


class JSONOutputTracer:
    """精确追踪JSON输出"""

    def __init__(self, original_stream, stream_name):
        self.original = original_stream
        self.stream_name = stream_name
        self.buffer = ""

    def write(self, text):
        """拦截所有write调用"""
        if not text:
            return 0

        # 累积缓冲区
        self.buffer += str(text)

        # 检查是否包含完整的JSON对象
        if '{' in self.buffer and '}' in self.buffer:
            # 尝试提取JSON
            try:
                start_idx = self.buffer.find('{')
                end_idx = self.buffer.find('}', start_idx) + 1

                if start_idx != -1 and end_idx > start_idx:
                    potential_json = self.buffer[start_idx:end_idx]

                    # 尝试解析
                    try:
                        parsed = json.loads(potential_json)

                        # 检查是否是目标JSON
                        if isinstance(parsed, dict) and 'result' in parsed:
                            if parsed.get('result') == 'error':
                                # 找到了！
                                print("\n" + "="*80, file=self.original)
                                print(f"[TARGET FOUND] [{self.stream_name}] Found target JSON output!", file=self.original)
                                print("="*80, file=self.original)
                                print(f"JSON content: {potential_json}", file=self.original)
                                print(f"Full buffer: {self.buffer!r}", file=self.original)
                                print("-"*80, file=self.original)
                                print("Call stack:", file=self.original)
                                for line in traceback.format_stack()[:-1]:
                                    print(line.rstrip(), file=self.original)
                                print("="*80 + "\n", file=self.original)

                                # 清空缓冲区
                                self.buffer = ""
                    except json.JSONDecodeError:
                        pass

                    # 如果缓冲区太大，清空它
                    if len(self.buffer) > 10000:
                        self.buffer = self.buffer[-1000:]
            except Exception as e:
                pass

        # 写入原始流
        return self.original.write(text)

    def flush(self):
        if hasattr(self.original, 'flush'):
            return self.original.flush()

    def __getattr__(self, name):
        return getattr(self.original, name)


# 保存原始流
_original_stdout = sys.stdout
_original_stderr = sys.stderr

# 安装追踪器
sys.stdout = JSONOutputTracer(_original_stdout, "STDOUT")
sys.stderr = JSONOutputTracer(_original_stderr, "STDERR")

print("="*80)
print("[JSON Tracer] JSON output tracer started")
print("="*80)
print("Target: Track {'result': 'error'} JSON output")
print("Monitoring: stdout and stderr")
print("="*80)
print()

# 现在启动应用
if __name__ == '__main__':
    try:
        # 导入main模块会触发初始化
        print("Importing main module...")
        import main
        print("Main module imported successfully")
    except KeyboardInterrupt:
        print("\nUser interrupted")
    except Exception as e:
        print(f"\nError: {e}")
        traceback.print_exc()
