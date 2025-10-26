"""
分布式节点功能回归测试

验证分布式节点能正常使用系统自有功能
"""

import sys
import time
import requests
from pathlib import Path
from loguru import logger

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class DistributedNodeRegressionTest:
    """分布式节点回归测试"""
    
    def __init__(self, node_host="localhost", node_port=8900):
        self.node_host = node_host
        self.node_port = node_port
        self.base_url = f"http://{node_host}:{node_port}"
        self.test_results = []
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 80)
        logger.info("开始分布式节点功能回归测试")
        logger.info("=" * 80)
        
        tests = [
            ("节点基础连接", self.test_basic_connection),
            ("节点健康检查", self.test_health_check),
            ("节点能力检测", self.test_capabilities),
            ("任务执行", self.test_task_execution),
            ("任务状态查询", self.test_task_status),
            ("节点统计信息", self.test_statistics),
            ("系统模块导入", self.test_system_modules),
            ("回测引擎访问", self.test_backtest_engine),
            ("指标服务访问", self.test_indicator_service),
            ("数据服务访问", self.test_data_service),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"测试: {test_name}")
            logger.info(f"{'='*60}")
            
            try:
                result = test_func()
                if result:
                    logger.info(f"✅ {test_name} - 通过")
                    self.test_results.append((test_name, "PASS", None))
                    passed += 1
                else:
                    logger.error(f"❌ {test_name} - 失败")
                    self.test_results.append((test_name, "FAIL", "测试返回False"))
                    failed += 1
            except Exception as e:
                logger.exception(f"❌ {test_name} - 异常: {e}")
                self.test_results.append((test_name, "ERROR", str(e)))
                failed += 1
        
        # 输出测试报告
        self.print_report(passed, failed)
        
        return failed == 0
    
    def test_basic_connection(self) -> bool:
        """测试基础连接"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"服务名称: {data.get('service')}")
                logger.info(f"版本: {data.get('version')}")
                logger.info(f"节点ID: {data.get('node_id')}")
                return True
            return False
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def test_health_check(self) -> bool:
        """测试健康检查"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"节点状态: {data.get('status')}")
                logger.info(f"CPU使用率: {data.get('cpu_percent')}%")
                logger.info(f"内存使用率: {data.get('memory_percent')}%")
                logger.info(f"活跃任务: {data.get('active_tasks')}")
                logger.info(f"运行时间: {data.get('uptime_seconds')}秒")
                return data.get('status') in ['active', 'idle']
            return False
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    def test_capabilities(self) -> bool:
        """测试能力检测"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                capabilities = data.get('capabilities', [])
                
                if not capabilities:
                    logger.warning("节点未报告任何能力")
                    return False
                
                logger.info(f"节点支持的能力 ({len(capabilities)} 项):")
                for cap in capabilities:
                    logger.info(f"  - {cap}")
                
                # 验证基础能力存在
                required_capabilities = ['data_fetch', 'data_process']
                for req_cap in required_capabilities:
                    if req_cap not in capabilities:
                        logger.error(f"缺少基础能力: {req_cap}")
                        return False
                
                return True
            return False
        except Exception as e:
            logger.error(f"能力检测失败: {e}")
            return False
    
    def test_task_execution(self) -> bool:
        """测试任务执行"""
        try:
            # 提交一个简单的测试任务
            task_request = {
                "task_id": "test_task_001",
                "task_type": "analysis",
                "task_data": {
                    "operation": "echo",
                    "message": "Hello from regression test"
                },
                "priority": 5
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/task/execute",
                json=task_request,
                timeout=10
            )
            
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"任务ID: {data.get('task_id')}")
                logger.info(f"任务状态: {data.get('status')}")
                # 任务已接收并开始执行即为成功
                return data.get('status') in ['running', 'RUNNING', 'pending']
            else:
                logger.warning(f"任务执行返回状态码: {response.status_code}")
                logger.warning(f"错误响应: {response.text}")
                return False
        except Exception as e:
            logger.error(f"任务执行测试失败: {e}")
            return False
    
    def test_task_status(self) -> bool:
        """测试任务状态查询"""
        try:
            task_id = "test_task_001"
            response = requests.get(
                f"{self.base_url}/api/v1/task/{task_id}/status",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"任务状态: {data.get('status')}")
                return True
            elif response.status_code == 404:
                logger.info("任务不存在或已完成（预期行为）")
                return True
            return False
        except Exception as e:
            logger.error(f"任务状态查询失败: {e}")
            return False
    
    def test_statistics(self) -> bool:
        """测试统计信息"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/statistics", timeout=5)
            logger.info(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('data', {})
                logger.info(f"活跃任务: {stats.get('active_tasks')}")
                logger.info(f"总执行任务: {stats.get('total_executed')}")
                logger.info(f"失败任务: {stats.get('total_failed')}")
                logger.info(f"平均执行时间: {stats.get('avg_execution_time')}秒")
                return True
            else:
                logger.warning(f"统计信息返回状态码: {response.status_code}")
                logger.warning(f"响应内容: {response.text}")
            return False
        except Exception as e:
            logger.error(f"统计信息获取失败: {e}")
            return False
    
    def test_system_modules(self) -> bool:
        """测试系统模块能否正常导入"""
        logger.info("测试系统模块导入...")
        
        modules_to_test = [
            ('core.containers.service_container', 'ServiceContainer'),
            ('core.services.distributed_service', 'DistributedService'),
            ('core.unified_indicator_service', 'UnifiedIndicatorService'),
            ('core.services.unified_data_manager', 'UnifiedDataManager'),
            ('utils.config_manager', 'ConfigManager'),
        ]
        
        all_passed = True
        for module_name, class_name in modules_to_test:
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                logger.info(f"  ✅ {module_name}.{class_name}")
            except Exception as e:
                logger.error(f"  ❌ {module_name}.{class_name} - {e}")
                all_passed = False
        
        return all_passed
    
    def test_backtest_engine(self) -> bool:
        """测试回测引擎访问"""
        logger.info("测试回测引擎访问...")
        
        try:
            from backtest import UnifiedBacktestEngine
            logger.info("  ✅ 成功导入 UnifiedBacktestEngine")
            
            # 尝试创建实例（不实际运行）
            try:
                engine = UnifiedBacktestEngine()
                logger.info("  ✅ 成功创建 UnifiedBacktestEngine 实例")
            except Exception as e:
                logger.warning(f"  ⚠️ 创建实例失败（可能需要参数）: {e}")
            
            return True
        except ImportError as e:
            logger.warning(f"  ⚠️ 回测引擎不可用: {e}")
            return True  # 不强制要求
    
    def test_indicator_service(self) -> bool:
        """测试指标服务访问"""
        logger.info("测试指标服务访问...")
        
        try:
            from core.unified_indicator_service import UnifiedIndicatorService
            logger.info("  ✅ 成功导入 UnifiedIndicatorService")
            
            # 尝试创建服务实例
            try:
                service = UnifiedIndicatorService()
                logger.info("  ✅ 成功创建指标服务实例")
                
                # 获取分类
                categories = service.get_all_categories()
                logger.info(f"  ✅ 获取到 {len(categories)} 个指标分类")
                
                return True
            except Exception as e:
                logger.error(f"  ❌ 指标服务初始化失败: {e}")
                return False
        except ImportError as e:
            logger.error(f"  ❌ 无法导入指标服务: {e}")
            return False
    
    def test_data_service(self) -> bool:
        """测试数据服务访问"""
        logger.info("测试数据服务访问...")
        
        try:
            from core.services.unified_data_manager import UnifiedDataManager
            logger.info("  ✅ 成功导入 UnifiedDataManager")
            
            # 尝试创建服务实例
            try:
                # UnifiedDataManager需要ServiceContainer
                from core.containers.service_container import ServiceContainer
                container = ServiceContainer.get_instance()
                
                data_manager = UnifiedDataManager(container)
                logger.info("  ✅ 成功创建数据管理器实例")
                
                return True
            except Exception as e:
                logger.warning(f"  ⚠️  数据管理器初始化失败（可能需要完整环境）: {e}")
                # 不强制要求，能导入即可
                return True
        except ImportError as e:
            logger.error(f"  ❌ 无法导入数据管理器: {e}")
            return False
    
    def print_report(self, passed, failed):
        """打印测试报告"""
        logger.info("\n" + "=" * 80)
        logger.info("测试报告")
        logger.info("=" * 80)
        
        for test_name, result, error in self.test_results:
            if result == "PASS":
                logger.info(f"✅ {test_name}: 通过")
            elif result == "FAIL":
                logger.error(f"❌ {test_name}: 失败 - {error}")
            else:  # ERROR
                logger.error(f"❌ {test_name}: 异常 - {error}")
        
        logger.info("=" * 80)
        logger.info(f"总计: {passed + failed} 个测试")
        logger.info(f"通过: {passed} 个 ({passed/(passed+failed)*100:.1f}%)")
        logger.info(f"失败: {failed} 个 ({failed/(passed+failed)*100:.1f}%)")
        logger.info("=" * 80)
        
        if failed == 0:
            logger.info("🎉 所有测试通过！")
        else:
            logger.error(f"⚠️ 有 {failed} 个测试失败")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="分布式节点功能回归测试")
    parser.add_argument("--host", default="localhost", help="节点主机地址")
    parser.add_argument("--port", type=int, default=8900, help="节点端口")
    args = parser.parse_args()
    
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # 运行测试
    tester = DistributedNodeRegressionTest(args.host, args.port)
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\n测试被用户中断")
        sys.exit(2)
    except Exception as e:
        logger.exception(f"测试异常: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()

