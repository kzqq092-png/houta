#!/usr/bin/env python3
"""
测试格式化字符串修复
"""

from core.services.performance_data_bridge import initialize_performance_bridge
import time

def test_format_fix():
    print('🔧 测试格式化字符串修复...')
    try:
        bridge = initialize_performance_bridge(auto_start=True)
        print('✅ 桥接器启动成功')
        
        # 等待几秒让数据收集运行
        time.sleep(5)
        
        status = bridge.get_status()
        print(f'✅ 桥接器状态正常: {status["metrics_count"]} 指标, {status["operations_count"]} 操作')
        
        # 强制触发系统指标收集
        bridge._collect_system_metrics()
        print('✅ 系统指标收集完成，无格式化错误')
        
        bridge.stop_active_collection()
        print('✅ 格式化错误修复验证成功!')
        
        return True
        
    except Exception as e:
        print(f'❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_format_fix()