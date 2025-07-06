#!/usr/bin/env python3
"""
图表服务调试脚本

专门测试图表服务和股票服务的交互问题
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockServiceContainer:
    """模拟服务容器"""

    def __init__(self, stock_service):
        self.stock_service = stock_service
        logger.debug(f"MockServiceContainer initialized with stock_service: {stock_service}")

    def get_service(self, service_type):
        """获取服务"""
        logger.debug(f"get_service called with service_type: {service_type}")
        logger.debug(f"service_type.__name__: {getattr(service_type, '__name__', 'N/A')}")

        if hasattr(service_type, '__name__') and service_type.__name__ == 'StockService':
            logger.debug(f"Returning stock_service: {self.stock_service}")
            return self.stock_service

        logger.debug("No matching service found, returning None")
        return None

    def try_resolve(self, service_type):
        """尝试解析服务"""
        return self.get_service(service_type)


def test_chart_service_interaction():
    """测试图表服务和股票服务的交互"""

    print("=" * 60)
    print("图表服务和股票服务交互调试")
    print("=" * 60)

    try:
        # 1. 创建事件总线
        print("\n1. 创建事件总线...")
        from core.events.event_bus import EventBus
        event_bus = EventBus()
        print("✓ 事件总线创建成功")

        # 2. 创建股票服务
        print("\n2. 创建股票服务...")
        from core.services.stock_service import StockService
        stock_service = StockService(event_bus=event_bus)
        stock_service.initialize()
        print("✓ 股票服务创建成功")

        # 3. 创建图表服务
        print("\n3. 创建图表服务...")
        from core.services.chart_service import ChartService
        chart_service = ChartService(event_bus=event_bus)
        chart_service.initialize()
        print("✓ 图表服务创建成功")

        # 4. 创建服务容器
        print("\n4. 创建服务容器...")
        service_container = MockServiceContainer(stock_service)
        chart_service.service_container = service_container
        print("✓ 服务容器设置成功")

        # 5. 测试股票服务直接调用
        print("\n5. 测试股票服务直接调用...")
        test_stock_code = "sz000001"
        stock_data = stock_service.get_stock_data(test_stock_code, period='D', count=5)
        if stock_data is not None and not stock_data.empty:
            print(f"✓ 股票服务直接调用成功，获取到 {len(stock_data)} 条数据")
        else:
            print("✗ 股票服务直接调用失败")

        # 6. 测试图表服务获取股票服务
        print("\n6. 测试图表服务获取股票服务...")
        retrieved_stock_service = chart_service._get_stock_service()
        if retrieved_stock_service:
            print(f"✓ 图表服务成功获取股票服务: {retrieved_stock_service}")
            print(f"  原始股票服务: {stock_service}")
            print(f"  是否为同一对象: {retrieved_stock_service is stock_service}")
        else:
            print("✗ 图表服务无法获取股票服务")

        # 7. 测试图表服务通过获取的股票服务调用数据
        print("\n7. 测试图表服务通过获取的股票服务调用数据...")
        if retrieved_stock_service:
            try:
                chart_stock_data = retrieved_stock_service.get_stock_data(test_stock_code, period='D', count=5)
                if chart_stock_data is not None and not chart_stock_data.empty:
                    print(f"✓ 图表服务通过股票服务获取数据成功，获取到 {len(chart_stock_data)} 条数据")
                else:
                    print("✗ 图表服务通过股票服务获取数据失败")
            except Exception as e:
                print(f"✗ 图表服务通过股票服务获取数据异常: {e}")
        else:
            print("✗ 无法测试，因为图表服务未获取到股票服务")

        # 8. 测试图表服务创建图表
        print("\n8. 测试图表服务创建图表...")
        try:
            chart_config = chart_service.create_chart(
                stock_code=test_stock_code,
                chart_type='candlestick',
                period='D',
                indicators=['MA5'],
                time_range=10
            )

            if chart_config:
                print(f"✓ 图表创建成功")
                print(f"  图表类型: {chart_config.get('chart_type')}")
                print(f"  数据量: {len(chart_config.get('data', []))}")
            else:
                print("✗ 图表创建失败")

        except Exception as e:
            print(f"✗ 图表创建异常: {e}")
            import traceback
            traceback.print_exc()

        # 9. 测试图表服务获取图表数据
        print("\n9. 测试图表服务获取图表数据...")
        try:
            chart_data = chart_service.get_chart_data(
                stock_code=test_stock_code,
                period='D',
                indicators=['MA5'],
                time_range=10
            )

            if chart_data and 'kline_data' in chart_data:
                print(f"✓ 图表数据获取成功")
                print(f"  数据量: {len(chart_data.get('kline_data', []))}")
                print(f"  股票名称: {chart_data.get('stock_name', 'N/A')}")
            else:
                print("✗ 图表数据获取失败")
                print(f"  返回数据: {chart_data}")

        except Exception as e:
            print(f"✗ 图表数据获取异常: {e}")
            import traceback
            traceback.print_exc()

        # 10. 检查服务容器的详细信息
        print("\n10. 检查服务容器的详细信息...")
        print(f"  图表服务是否有service_container属性: {hasattr(chart_service, 'service_container')}")
        if hasattr(chart_service, 'service_container'):
            print(f"  service_container值: {chart_service.service_container}")
            print(f"  service_container类型: {type(chart_service.service_container)}")

        # 11. 手动测试服务容器
        print("\n11. 手动测试服务容器...")
        try:
            from core.services.stock_service import StockService
            manual_service = service_container.get_service(StockService)
            print(f"  手动获取服务结果: {manual_service}")
            print(f"  是否为同一对象: {manual_service is stock_service}")
        except Exception as e:
            print(f"  手动获取服务异常: {e}")

    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_chart_service_interaction()
