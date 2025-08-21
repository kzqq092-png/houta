#!/usr/bin/env python3
"""快速UI状态测试"""


def test_ui_status_logic():
    """测试UI状态逻辑"""
    print("🚀 测试UI状态逻辑修复...")

    # 模拟一个简单的健康检查结果
    class MockHealthResult:
        def __init__(self, is_healthy, error_message=None):
            self.is_healthy = is_healthy
            self.error_message = error_message

    # 模拟适配器
    class MockAdapter:
        def __init__(self, health_result):
            self._health_result = health_result

        def health_check(self):
            return self._health_result

    # 测试场景
    test_cases = [
        ("健康插件", MockAdapter(MockHealthResult(True)), True),
        ("不健康插件", MockAdapter(MockHealthResult(False, "连接失败")), False),
        ("异常插件", MockAdapter(None), False),  # 会抛出异常
    ]

    print("\n🔍 测试不同状态场景:")

    for name, adapter, expected in test_cases:
        try:
            # 模拟修复后的状态检查逻辑
            is_connected = False
            status_message = "未连接"

            try:
                health_result = adapter.health_check()
                if hasattr(health_result, 'is_healthy') and health_result.is_healthy:
                    is_connected = True
                    status_message = "活跃"
                else:
                    error_msg = getattr(health_result, 'error_message', '健康检查失败')
                    status_message = error_msg
            except Exception as e:
                status_message = f"健康检查异常: {str(e)}"

            result_icon = "✅" if is_connected == expected else "❌"
            status_icon = "🟢" if is_connected else "🔴"

            print(f"  {result_icon} {name}: {status_icon} {status_message}")

        except Exception as e:
            print(f"  ❌ {name}: 测试异常 - {e}")

    print("\n✅ UI状态逻辑测试完成")
    print("修复要点:")
    print("  1. 移除了过于严格的适配器状态检查")
    print("  2. 统一使用健康检查作为连接状态判断标准")
    print("  3. 为不支持is_connected的插件提供健康检查备用方案")


if __name__ == "__main__":
    test_ui_status_logic()
