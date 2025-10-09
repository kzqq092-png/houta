#!/usr/bin/env python3
"""
TET框架状态监控脚本

实时监控TET框架的运行状态、性能指标和插件健康状况
作者: FactorWeave-Quant团队
版本: 1.0
"""

from core.containers import get_service_container
from core.services.uni_plugin_data_manager import get_uni_plugin_data_manager
from loguru import logger
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class TETFrameworkMonitor:
    """TET框架状态监控器"""

    def __init__(self):
        self.service_container = get_service_container()
        self.uni_manager = None
        self.monitoring = False

    def initialize(self) -> bool:
        """初始化监控器"""
        try:
            # 获取UniPluginDataManager实例
            self.uni_manager = get_uni_plugin_data_manager()
            if not self.uni_manager:
                logger.error("无法获取UniPluginDataManager实例")
                return False

            logger.info("TET框架监控器初始化成功")
            return True

        except Exception as e:
            logger.error(f"TET框架监控器初始化失败: {e}")
            return False

    def get_tet_status_summary(self) -> Dict[str, Any]:
        """获取TET框架状态摘要"""
        if not self.uni_manager:
            return {"error": "UniPluginDataManager未初始化"}

        try:
            status = self.uni_manager.get_tet_framework_status()

            # 生成状态摘要
            summary = {
                "timestamp": datetime.now().isoformat(),
                "framework": {
                    "name": status["framework_info"]["name"],
                    "version": status["framework_info"]["version"],
                    "status": status["framework_info"]["status"]
                },
                "performance": {
                    "total_requests": status["performance_metrics"]["total_requests"],
                    "success_rate": f"{status['performance_metrics']['success_rate']:.2%}",
                    "avg_response_time": f"{status['performance_metrics']['avg_response_time']:.3f}s",
                    "cache_hit_rate": f"{status['performance_metrics']['cache_hit_rate']:.2%}"
                },
                "plugins": {
                    "total": status["plugin_center"]["total_plugins"],
                    "active": status["plugin_center"]["active_plugins"],
                    "data_sources": status["plugin_center"]["data_source_plugins"]
                },
                "routing": {
                    "registered_plugins": status["routing_engine"]["registered_plugins"],
                    "intelligent_routing": status["routing_engine"]["intelligent_routing_enabled"],
                    "adaptive_weights": status["routing_engine"]["adaptive_weights_enabled"]
                }
            }

            return summary

        except Exception as e:
            logger.error(f"获取TET状态摘要失败: {e}")
            return {"error": str(e)}

    def print_status_dashboard(self):
        """打印状态仪表板"""
        status = self.get_tet_status_summary()

        if "error" in status:
            print(f"❌ 错误: {status['error']}")
            return

        print("\n" + "="*80)
        print("🚀 TET框架状态监控仪表板")
        print("="*80)

        # 框架信息
        fw = status["framework"]
        print(f"📋 框架信息:")
        print(f"   名称: {fw['name']}")
        print(f"   版本: {fw['version']}")
        print(f"   状态: {'🟢' if fw['status'] == 'Active' else '🔴'} {fw['status']}")

        # 性能指标
        perf = status["performance"]
        print(f"\n📊 性能指标:")
        print(f"   总请求数: {perf['total_requests']}")
        print(f"   成功率: {perf['success_rate']}")
        print(f"   平均响应时间: {perf['avg_response_time']}")
        print(f"   缓存命中率: {perf['cache_hit_rate']}")

        # 插件状态
        plugins = status["plugins"]
        print(f"\n🔌 插件状态:")
        print(f"   总插件数: {plugins['total']}")
        print(f"   活跃插件: {plugins['active']}")
        print(f"   数据源插件: {plugins['data_sources']}")

        # 路由引擎
        routing = status["routing"]
        print(f"\n🎯 路由引擎:")
        print(f"   注册插件数: {routing['registered_plugins']}")
        print(f"   智能路由: {'🟢 启用' if routing['intelligent_routing'] else '🔴 禁用'}")
        print(f"   自适应权重: {'🟢 启用' if routing['adaptive_weights'] else '🔴 禁用'}")

        print(f"\n⏰ 更新时间: {status['timestamp']}")
        print("="*80)

    async def start_monitoring(self, interval: int = 10):
        """开始监控"""
        if not self.initialize():
            return

        self.monitoring = True
        logger.info(f"开始TET框架监控，刷新间隔: {interval}秒")

        try:
            while self.monitoring:
                # 清屏（在支持的终端中）
                import os
                os.system('cls' if os.name == 'nt' else 'clear')

                # 显示状态仪表板
                self.print_status_dashboard()

                # 等待下一次刷新
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            logger.info("监控已停止")
        except Exception as e:
            logger.error(f"监控过程中出错: {e}")
        finally:
            self.monitoring = False

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False

    def export_status_report(self, output_file: str = None):
        """导出状态报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"tet_framework_report_{timestamp}.json"

        try:
            if not self.uni_manager:
                if not self.initialize():
                    return False

            # 获取完整状态信息
            full_status = self.uni_manager.get_tet_framework_status()
            full_status["export_timestamp"] = datetime.now().isoformat()

            # 写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(full_status, f, indent=2, ensure_ascii=False)

            logger.info(f"TET框架状态报告已导出: {output_file}")
            return True

        except Exception as e:
            logger.error(f"导出状态报告失败: {e}")
            return False

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="TET框架状态监控")
    parser.add_argument("--monitor", action="store_true", help="启动实时监控")
    parser.add_argument("--interval", type=int, default=10, help="监控刷新间隔（秒）")
    parser.add_argument("--export", type=str, help="导出状态报告到指定文件")
    parser.add_argument("--status", action="store_true", help="显示当前状态")

    args = parser.parse_args()

    monitor = TETFrameworkMonitor()

    if args.monitor:
        # 实时监控模式
        await monitor.start_monitoring(args.interval)
    elif args.export:
        # 导出报告模式
        monitor.export_status_report(args.export)
    elif args.status:
        # 显示当前状态
        if monitor.initialize():
            monitor.print_status_dashboard()
    else:
        # 默认显示状态
        if monitor.initialize():
            monitor.print_status_dashboard()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 监控已停止")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
