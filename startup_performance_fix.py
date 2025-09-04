#!/usr/bin/env python3
"""
性能仪表盘启动修复脚本
在应用启动时运行此脚本以确保数据正常显示
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def startup_fix():
    """启动修复"""
    try:
        from core.performance import get_performance_monitor
        
        # 预热性能监控器
        monitor = get_performance_monitor()
        
        # 预热系统监控
        for i in range(3):
            metrics = monitor.system_monitor.collect_metrics()
            print(f"预热 {i+1}/3: CPU={metrics.get('CPU使用率', 0)}%")
            
        print("✅ 性能监控器预热完成")
        
        # 生成最新的汇总数据
        import sqlite3
        with sqlite3.connect("db/metrics.sqlite") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM resource_metrics_summary")
            cursor.execute("""
                INSERT INTO resource_metrics_summary (t_stamp, cpu, mem, disk)
                SELECT 
                    datetime(timestamp, 'unixepoch') as t_stamp,
                    AVG(CASE WHEN metric_name = 'cpu_usage' THEN value END) as cpu,
                    AVG(CASE WHEN metric_name = 'memory_usage' THEN value END) as mem,
                    AVG(CASE WHEN metric_name = 'disk_usage' THEN value END) as disk
                FROM metrics 
                WHERE category = 'system' 
                AND timestamp > strftime('%s', 'now', '-1 hour')
                GROUP BY datetime(timestamp, 'unixepoch', 'start of minute')
                ORDER BY timestamp DESC
                LIMIT 60
            """)
            conn.commit()
            
        print("✅ 汇总数据已更新")
        
        return True
        
    except Exception as e:
        print(f"❌ 启动修复失败: {e}")
        return False

if __name__ == "__main__":
    startup_fix()
