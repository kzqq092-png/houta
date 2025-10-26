"""
简化版JSON追踪器 - 只追踪DuckDB操作
"""
import sys
import json
import traceback


class SimpleJSONTracer:
    def __init__(self, original, name):
        self.original = original
        self.name = name
        self.buffer = ""

    def write(self, text):
        if not text:
            return 0

        self.buffer += str(text)

        # 检查是否包含目标JSON
        if '{"result"' in self.buffer or '"result"' in self.buffer:
            if '"error"' in self.buffer:
                # 可能找到了
                print("\n" + "="*60, file=self.original)
                print(f"[{self.name}] Possible target JSON detected", file=self.original)
                print("="*60, file=self.original)
                print(f"Buffer content: {self.buffer[-200:]}", file=self.original)
                print("-"*60, file=self.original)
                print("Stack trace:", file=self.original)
                for line in traceback.format_stack()[-10:]:  # 只显示最后10层
                    print(line.rstrip(), file=self.original)
                print("="*60, file=self.original)
                self.buffer = ""

        # 限制缓冲区大小
        if len(self.buffer) > 5000:
            self.buffer = self.buffer[-1000:]

        return self.original.write(text)

    def flush(self):
        if hasattr(self.original, 'flush'):
            return self.original.flush()

    def __getattr__(self, name):
        return getattr(self.original, name)


# 安装追踪器
_stdout = sys.stdout
_stderr = sys.stderr

sys.stdout = SimpleJSONTracer(_stdout, "OUT")
sys.stderr = SimpleJSONTracer(_stderr, "ERR")

print("="*60)
print("Simple JSON Tracer Started")
print("="*60)

# 测试DuckDB操作
try:
    print("\nTesting DuckDB operations...")

    # 导入必要的模块
    from core.services.unified_data_manager import UnifiedDataManager
    from core.asset_database_manager import AssetDatabaseManager
    from core.database.duckdb_manager import DuckDBConnectionManager
    from core.database.duckdb_operations import DuckDBOperations

    print("Modules imported")

    # 创建管理器
    duckdb_manager = DuckDBConnectionManager()
    asset_manager = AssetDatabaseManager(duckdb_manager=duckdb_manager)
    duckdb_ops = DuckDBOperations(duckdb_manager)

    print("Managers created")

    # 创建UnifiedDataManager
    udm = UnifiedDataManager(
        duckdb_operations=duckdb_ops,
        asset_manager=asset_manager
    )

    print("UnifiedDataManager created")

    # 尝试获取资产列表（这会触发问题）
    print("\nCalling get_asset_list...")
    result = udm.get_asset_list('stock')
    print(f"Result: {len(result) if result is not None else 'None'} rows")

except Exception as e:
    print(f"\nException: {e}")
    traceback.print_exc()

print("\nTest completed")
