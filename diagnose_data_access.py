#!/usr/bin/env python3
"""
数据访问诊断脚本

检查HIkyuu框架、数据管理器、服务层的初始化状态和连接情况
"""

import sys
import os
import logging
from typing import Dict, Any, List
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataAccessDiagnostic:
    """数据访问诊断器"""

    def __init__(self):
        self.results = {}
        self.issues = []
        self.recommendations = []

    def run_full_diagnostic(self) -> Dict[str, Any]:
        """运行完整诊断"""
        print("=" * 60)
        print("HIkyuu-UI 数据访问诊断")
        print("=" * 60)

        # 1. 检查HIkyuu框架
        self.check_hikyuu_framework()

        # 2. 检查数据管理器
        self.check_data_managers()

        # 3. 检查数据访问层
        self.check_data_access_layer()

        # 4. 检查服务层
        self.check_service_layer()

        # 5. 测试股票数据获取
        self.test_stock_data_access()

        # 6. 生成诊断报告
        self.generate_report()

        return self.results

    def check_hikyuu_framework(self):
        """检查HIkyuu框架状态"""
        print("\n1. 检查HIkyuu框架...")

        try:
            # 尝试导入HIkyuu
            import hikyuu
            from hikyuu import StockManager, Query
            from hikyuu.interactive import sm

            self.results['hikyuu_import'] = True
            print("  ✓ HIkyuu框架导入成功")

            # 检查版本
            if hasattr(hikyuu, '__version__'):
                version = hikyuu.__version__
                self.results['hikyuu_version'] = version
                print(f"  ✓ HIkyuu版本: {version}")
            else:
                self.results['hikyuu_version'] = "未知"
                print("  ⚠ 无法获取HIkyuu版本")

            # 检查StockManager
            if sm is not None:
                self.results['stock_manager_available'] = True
                print("  ✓ StockManager可用")

                # 检查股票数量
                try:
                    stock_count = len(sm)
                    self.results['stock_count'] = stock_count
                    print(f"  ✓ 股票数量: {stock_count}")

                    if stock_count == 0:
                        self.issues.append("HIkyuu数据库中没有股票数据")
                        self.recommendations.append("需要初始化HIkyuu数据库并导入股票数据")

                except Exception as e:
                    self.results['stock_count'] = 0
                    self.issues.append(f"无法获取股票数量: {e}")
                    print(f"  ✗ 获取股票数量失败: {e}")
            else:
                self.results['stock_manager_available'] = False
                self.issues.append("StockManager未初始化")
                print("  ✗ StockManager未初始化")

        except ImportError as e:
            self.results['hikyuu_import'] = False
            self.issues.append(f"HIkyuu框架导入失败: {e}")
            print(f"  ✗ HIkyuu框架导入失败: {e}")
        except Exception as e:
            self.results['hikyuu_import'] = False
            self.issues.append(f"HIkyuu框架检查失败: {e}")
            print(f"  ✗ HIkyuu框架检查失败: {e}")

    def check_data_managers(self):
        """检查数据管理器"""
        print("\n2. 检查数据管理器...")

        # 检查HIkyuu数据管理器
        try:
            from core.data.hikyuu_data_manager import HikyuuDataManager

            hikyuu_manager = HikyuuDataManager()
            self.results['hikyuu_data_manager'] = True
            print("  ✓ HIkyuu数据管理器创建成功")

            # 测试连接
            connection_test = hikyuu_manager.test_connection()
            self.results['hikyuu_connection_test'] = connection_test

            if connection_test:
                print("  ✓ HIkyuu数据管理器连接测试通过")

                # 测试股票列表获取
                try:
                    stock_list = hikyuu_manager.get_stock_list()
                    stock_list_count = len(stock_list)
                    self.results['hikyuu_stock_list_count'] = stock_list_count
                    print(f"  ✓ HIkyuu股票列表数量: {stock_list_count}")

                    if stock_list_count == 0:
                        self.issues.append("HIkyuu数据管理器返回空股票列表")

                except Exception as e:
                    self.issues.append(f"HIkyuu股票列表获取失败: {e}")
                    print(f"  ✗ HIkyuu股票列表获取失败: {e}")

            else:
                print("  ✗ HIkyuu数据管理器连接测试失败")
                self.issues.append("HIkyuu数据管理器连接测试失败")

        except Exception as e:
            self.results['hikyuu_data_manager'] = False
            self.issues.append(f"HIkyuu数据管理器创建失败: {e}")
            print(f"  ✗ HIkyuu数据管理器创建失败: {e}")

        # 检查默认数据管理器
        try:
            from core.data_manager import DataManager

            default_manager = DataManager()
            self.results['default_data_manager'] = True
            print("  ✓ 默认数据管理器创建成功")

        except Exception as e:
            self.results['default_data_manager'] = False
            self.issues.append(f"默认数据管理器创建失败: {e}")
            print(f"  ✗ 默认数据管理器创建失败: {e}")

    def check_data_access_layer(self):
        """检查数据访问层"""
        print("\n3. 检查数据访问层...")

        try:
            from core.data.data_access import DataAccess

            # 测试默认数据访问层
            data_access = DataAccess()
            connection_result = data_access.connect()

            self.results['data_access_connection'] = connection_result
            if connection_result:
                print("  ✓ 数据访问层连接成功")
            else:
                print("  ✗ 数据访问层连接失败")
                self.issues.append("数据访问层连接失败")

            # 测试带HIkyuu数据管理器的数据访问层
            try:
                from core.data.hikyuu_data_manager import HikyuuDataManager
                hikyuu_manager = HikyuuDataManager()

                hikyuu_data_access = DataAccess(hikyuu_manager)
                hikyuu_connection_result = hikyuu_data_access.connect()

                self.results['hikyuu_data_access_connection'] = hikyuu_connection_result
                if hikyuu_connection_result:
                    print("  ✓ HIkyuu数据访问层连接成功")
                else:
                    print("  ✗ HIkyuu数据访问层连接失败")
                    self.issues.append("HIkyuu数据访问层连接失败")

            except Exception as e:
                self.results['hikyuu_data_access_connection'] = False
                self.issues.append(f"HIkyuu数据访问层测试失败: {e}")
                print(f"  ✗ HIkyuu数据访问层测试失败: {e}")

        except Exception as e:
            self.results['data_access_layer'] = False
            self.issues.append(f"数据访问层检查失败: {e}")
            print(f"  ✗ 数据访问层检查失败: {e}")

    def check_service_layer(self):
        """检查服务层"""
        print("\n4. 检查服务层...")

        try:
            from core.events.event_bus import EventBus
            from core.services.stock_service import StockService

            # 创建事件总线
            event_bus = EventBus()

            # 创建股票服务
            stock_service = StockService(event_bus=event_bus)

            # 初始化服务
            stock_service.initialize()

            self.results['stock_service_init'] = True
            print("  ✓ 股票服务初始化成功")

            # 检查是否使用模拟数据
            use_mock_data = getattr(stock_service, 'use_mock_data', False)
            self.results['use_mock_data'] = use_mock_data

            if use_mock_data:
                print("  ⚠ 股票服务使用模拟数据模式")
                self.issues.append("股票服务运行在模拟数据模式")
                self.recommendations.append("需要修复HIkyuu数据连接以使用真实数据")
            else:
                print("  ✓ 股票服务使用真实数据模式")

            # 测试股票列表获取
            try:
                stock_list = stock_service.get_stock_list()
                service_stock_count = len(stock_list)
                self.results['service_stock_count'] = service_stock_count
                print(f"  ✓ 服务层股票列表数量: {service_stock_count}")

                if service_stock_count == 0:
                    self.issues.append("服务层返回空股票列表")

            except Exception as e:
                self.issues.append(f"服务层股票列表获取失败: {e}")
                print(f"  ✗ 服务层股票列表获取失败: {e}")

        except Exception as e:
            self.results['stock_service_init'] = False
            self.issues.append(f"服务层检查失败: {e}")
            print(f"  ✗ 服务层检查失败: {e}")

    def test_stock_data_access(self):
        """测试股票数据获取"""
        print("\n5. 测试股票数据获取...")

        test_stocks = ['000001', 'sz000001', '600000', 'sh600000', '000595', 'sz000595']

        try:
            from core.events.event_bus import EventBus
            from core.services.stock_service import StockService

            # 创建事件总线和股票服务
            event_bus = EventBus()
            stock_service = StockService(event_bus=event_bus)
            stock_service.initialize()

            self.results['stock_data_tests'] = {}

            for stock_code in test_stocks:
                try:
                    print(f"  测试股票: {stock_code}")

                    # 测试股票数据获取
                    stock_data = stock_service.get_stock_data(stock_code, period='D', count=10)

                    if stock_data is not None and not stock_data.empty:
                        data_count = len(stock_data)
                        self.results['stock_data_tests'][stock_code] = {
                            'success': True,
                            'data_count': data_count
                        }
                        print(f"    ✓ 获取到 {data_count} 条数据")
                    else:
                        self.results['stock_data_tests'][stock_code] = {
                            'success': False,
                            'error': '无数据'
                        }
                        print(f"    ✗ 无数据")

                except Exception as e:
                    self.results['stock_data_tests'][stock_code] = {
                        'success': False,
                        'error': str(e)
                    }
                    print(f"    ✗ 错误: {e}")

            # 统计成功率
            total_tests = len(test_stocks)
            successful_tests = sum(1 for result in self.results['stock_data_tests'].values()
                                   if result['success'])
            success_rate = (successful_tests / total_tests) * 100

            self.results['data_access_success_rate'] = success_rate
            print(f"\n  数据获取成功率: {success_rate:.1f}% ({successful_tests}/{total_tests})")

            if success_rate < 50:
                self.issues.append("股票数据获取成功率过低")
                self.recommendations.append("需要检查HIkyuu数据库配置和股票数据")

        except Exception as e:
            self.issues.append(f"股票数据获取测试失败: {e}")
            print(f"  ✗ 股票数据获取测试失败: {e}")

    def generate_report(self):
        """生成诊断报告"""
        print("\n" + "=" * 60)
        print("诊断报告")
        print("=" * 60)

        # 系统状态概览
        print("\n📊 系统状态概览:")
        hikyuu_status = "✓ 正常" if self.results.get('hikyuu_import', False) else "✗ 异常"
        data_manager_status = "✓ 正常" if self.results.get('hikyuu_data_manager', False) else "✗ 异常"
        service_status = "✓ 正常" if self.results.get('stock_service_init', False) else "✗ 异常"

        print(f"  HIkyuu框架: {hikyuu_status}")
        print(f"  数据管理器: {data_manager_status}")
        print(f"  服务层: {service_status}")

        if self.results.get('use_mock_data', False):
            print("  ⚠ 当前使用模拟数据模式")

        # 数据统计
        print("\n📈 数据统计:")
        if 'stock_count' in self.results:
            print(f"  HIkyuu股票数量: {self.results['stock_count']}")
        if 'hikyuu_stock_list_count' in self.results:
            print(f"  数据管理器股票数量: {self.results['hikyuu_stock_list_count']}")
        if 'service_stock_count' in self.results:
            print(f"  服务层股票数量: {self.results['service_stock_count']}")
        if 'data_access_success_rate' in self.results:
            print(f"  数据获取成功率: {self.results['data_access_success_rate']:.1f}%")

        # 发现的问题
        if self.issues:
            print("\n🚨 发现的问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")

        # 修复建议
        if self.recommendations:
            print("\n💡 修复建议:")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"  {i}. {rec}")

        # 总结
        print("\n📋 总结:")
        if not self.issues:
            print("  ✓ 系统运行正常，未发现严重问题")
        else:
            print(f"  ⚠ 发现 {len(self.issues)} 个问题需要修复")

        print("\n" + "=" * 60)
        print(f"诊断完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


def main():
    """主函数"""
    diagnostic = DataAccessDiagnostic()
    results = diagnostic.run_full_diagnostic()

    # 保存诊断结果
    import json
    with open('diagnostic_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n诊断结果已保存到: diagnostic_results.json")

    return results


if __name__ == "__main__":
    main()
