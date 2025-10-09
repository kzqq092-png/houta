"""
修复关键数据请求错误

问题1: DataQualityRiskManager缺少execute_with_monitoring方法
问题2: 只有4个插件被发现，而系统中有39个插件文件

作者: FactorWeave-Quant团队
日期: 2024-09-30
"""

import os
import sys
from pathlib import Path
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("logs/critical_fix_{time}.log", rotation="10 MB", level="DEBUG")


class CriticalDataRequestFixer:
    """关键数据请求错误修复器"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.fixes_applied = []
        self.errors = []

    def run(self):
        """执行所有修复"""
        logger.info("="*80)
        logger.info("开始修复关键数据请求错误")
        logger.info("="*80)

        # 修复1: 添加缺失的execute_with_monitoring方法
        self.fix_data_quality_risk_manager()

        # 修复2: 检查并修复插件发现机制
        self.check_plugin_discovery_issue()

        # 修复3: 验证数据源插件接口实现
        self.verify_plugin_interfaces()

        # 生成报告
        self.generate_report()

    def fix_data_quality_risk_manager(self):
        """修复DataQualityRiskManager缺少execute_with_monitoring方法"""
        logger.info("\n" + "="*60)
        logger.info("修复1: 添加execute_with_monitoring方法到DataQualityRiskManager")
        logger.info("="*60)

        try:
            risk_manager_file = self.project_root / "core" / "data_quality_risk_manager.py"

            if not risk_manager_file.exists():
                self.errors.append("data_quality_risk_manager.py文件不存在")
                return

            with open(risk_manager_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否已经有这个方法
            if 'def execute_with_monitoring' in content:
                logger.info("✓ execute_with_monitoring方法已存在，跳过")
                return

            # 找到合适的插入位置（在assess_risk方法之后）
            insert_position = content.find('    def _calculate_risk_score')

            if insert_position == -1:
                self.errors.append("无法找到合适的插入位置")
                return

            # 新增方法代码
            new_method = '''    def execute_with_monitoring(self, plugin_id: str, method: Callable, **kwargs) -> Tuple[Any, Any]:
        """
        执行插件方法并监控数据质量
        
        Args:
            plugin_id: 插件ID
            method: 要执行的方法
            **kwargs: 方法参数
            
        Returns:
            Tuple[Any, Any]: (执行结果, 验证结果)
        """
        import time
        from datetime import datetime
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 执行方法
            result = method(**kwargs)
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 评估数据质量
            context = {
                'plugin_id': plugin_id,
                'execution_time': execution_time,
                'timestamp': datetime.now()
            }
            
            # 进行风险评估
            assessment = self.assess_risk(
                data=result,
                data_source=plugin_id,
                data_type=kwargs.get('data_type', 'unknown'),
                context=context
            )
            
            # 创建验证结果
            validation_result = type('ValidationResult', (), {
                'is_valid': assessment.risk_level.value not in ['critical', 'high'],
                'quality_score': assessment.quality_report.overall_score,
                'risk_level': assessment.risk_level.value,
                'assessment': assessment
            })()
            
            return result, validation_result
            
        except Exception as e:
            self.logger.error(f"执行插件方法时出错 {plugin_id}: {e}")
            
            # 创建失败的验证结果
            validation_result = type('ValidationResult', (), {
                'is_valid': False,
                'quality_score': 0.0,
                'risk_level': 'critical',
                'error': str(e)
            })()
            
            return None, validation_result

'''

            # 插入新方法
            new_content = content[:insert_position] + new_method + '\n' + content[insert_position:]

            # 备份原文件
            backup_file = risk_manager_file.with_suffix('.py.backup_critical_fix')
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # 写入修改后的内容
            with open(risk_manager_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            logger.info("✓ 成功添加execute_with_monitoring方法")
            logger.info(f"✓ 原文件已备份到: {backup_file}")
            self.fixes_applied.append({
                'file': str(risk_manager_file),
                'description': '添加execute_with_monitoring方法',
                'backup': str(backup_file)
            })

        except Exception as e:
            logger.error(f"✗ 修复失败: {e}")
            self.errors.append(f"修复DataQualityRiskManager失败: {e}")

    def check_plugin_discovery_issue(self):
        """检查插件发现问题"""
        logger.info("\n" + "="*60)
        logger.info("修复2: 检查插件发现机制")
        logger.info("="*60)

        try:
            plugins_dir = self.project_root / "plugins"

            # 统计各目录的插件数量
            plugin_stats = {}

            for subdir in ['data_sources', 'examples', 'indicators', 'strategies', 'sentiment_data_sources']:
                subdir_path = plugins_dir / subdir
                if subdir_path.exists():
                    plugin_files = list(subdir_path.glob('*.py'))
                    # 过滤掉__init__.py等非插件文件
                    plugin_files = [f for f in plugin_files
                                    if not f.name.startswith('__')
                                    and f.name not in ['plugin_interface.py', 'plugin_market.py']]
                    plugin_stats[subdir] = len(plugin_files)

                    logger.info(f"{subdir}: {len(plugin_files)} 个插件文件")
                    for pf in plugin_files[:5]:  # 只显示前5个
                        logger.info(f"  - {pf.name}")
                    if len(plugin_files) > 5:
                        logger.info(f"  ... 还有 {len(plugin_files) - 5} 个")

            total_plugins = sum(plugin_stats.values())
            logger.info(f"\n总计: {total_plugins} 个插件文件")
            logger.info(f"实际被发现: 4 个插件")
            logger.info(f"差异: {total_plugins - 4} 个插件未被发现")

            # 分析原因
            logger.info("\n可能原因:")
            logger.info("1. data_sources目录下的插件可能没有正确实现IDataSourcePlugin接口")
            logger.info("2. PluginCenter的_is_data_source_plugin检查过于严格")
            logger.info("3. 某些插件在加载时出现错误")

            self.fixes_applied.append({
                'analysis': 'plugin_discovery',
                'total_files': total_plugins,
                'discovered': 4,
                'missing': total_plugins - 4,
                'stats': plugin_stats
            })

        except Exception as e:
            logger.error(f"✗ 检查失败: {e}")
            self.errors.append(f"检查插件发现机制失败: {e}")

    def verify_plugin_interfaces(self):
        """验证插件接口实现"""
        logger.info("\n" + "="*60)
        logger.info("修复3: 验证插件接口实现")
        logger.info("="*60)

        try:
            # 检查几个关键的data_sources插件
            plugins_to_check = [
                'plugins/data_sources/eastmoney_plugin.py',
                'plugins/data_sources/akshare_plugin.py',
                'plugins/data_sources/tongdaxin_plugin.py',
                'plugins/data_sources/sina_plugin.py'
            ]

            interface_check_results = []

            for plugin_path in plugins_to_check:
                full_path = self.project_root / plugin_path
                if not full_path.exists():
                    logger.warning(f"插件不存在: {plugin_path}")
                    continue

                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 检查关键方法
                has_get_plugin_info = 'def get_plugin_info' in content
                has_get_supported_data_types = 'def get_supported_data_types' in content
                has_fetch_data = 'def fetch_data' in content
                has_test_connection = 'def test_connection' in content

                # 检查是否继承自正确的基类
                implements_interface = (
                    'IDataSourcePlugin' in content or
                    'StandardDataSourcePlugin' in content
                )

                result = {
                    'plugin': plugin_path,
                    'implements_interface': implements_interface,
                    'has_get_plugin_info': has_get_plugin_info,
                    'has_get_supported_data_types': has_get_supported_data_types,
                    'has_fetch_data': has_fetch_data,
                    'has_test_connection': has_test_connection,
                    'complete': all([
                        implements_interface,
                        has_get_plugin_info,
                        has_get_supported_data_types,
                        has_fetch_data
                    ])
                }

                interface_check_results.append(result)

                status = "✓" if result['complete'] else "✗"
                logger.info(f"{status} {plugin_path}")
                logger.info(f"  - 实现接口: {implements_interface}")
                logger.info(f"  - get_plugin_info: {has_get_plugin_info}")
                logger.info(f"  - get_supported_data_types: {has_get_supported_data_types}")
                logger.info(f"  - fetch_data: {has_fetch_data}")
                logger.info(f"  - test_connection: {has_test_connection}")

            complete_count = sum(1 for r in interface_check_results if r['complete'])
            logger.info(f"\n完整实现接口的插件: {complete_count}/{len(interface_check_results)}")

            self.fixes_applied.append({
                'verification': 'plugin_interfaces',
                'results': interface_check_results,
                'complete_count': complete_count,
                'total_checked': len(interface_check_results)
            })

        except Exception as e:
            logger.error(f"✗ 验证失败: {e}")
            self.errors.append(f"验证插件接口失败: {e}")

    def generate_report(self):
        """生成修复报告"""
        logger.info("\n" + "="*80)
        logger.info("修复报告")
        logger.info("="*80)

        logger.info(f"\n成功应用的修复: {len(self.fixes_applied)}")
        for i, fix in enumerate(self.fixes_applied, 1):
            logger.info(f"{i}. {fix}")

        if self.errors:
            logger.warning(f"\n遇到的错误: {len(self.errors)}")
            for i, error in enumerate(self.errors, 1):
                logger.warning(f"{i}. {error}")
        else:
            logger.info("\n✓ 没有遇到错误")

        # 生成详细报告文件
        report_file = self.project_root / f"error_fix_report_{sys.platform}_{Path(__file__).stem}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 关键数据请求错误修复报告\n\n")
            f.write(f"修复时间: {__import__('datetime').datetime.now()}\n\n")

            f.write("## 问题分析\n\n")
            f.write("### 问题1: DataQualityRiskManager缺少execute_with_monitoring方法\n\n")
            f.write("**错误信息**: `'DataQualityRiskManager' object has no attribute 'execute_with_monitoring'`\n\n")
            f.write("**根本原因**: `uni_plugin_data_manager.py`第820行调用了`self.risk_manager.execute_with_monitoring()`，")
            f.write("但`DataQualityRiskManager`类中没有实现这个方法。\n\n")
            f.write("**修复方案**: 在`DataQualityRiskManager`类中添加`execute_with_monitoring`方法，")
            f.write("该方法执行插件方法并返回结果和验证信息。\n\n")

            f.write("### 问题2: 只有4个插件被发现\n\n")
            f.write("**现象**: 系统注册了39个插件文件，但只有4个被发现：\n")
            f.write("- `data_sources.sina_plugin`\n")
            f.write("- `examples.custom_data_plugin`\n")
            f.write("- `examples.mysteel_data_plugin`\n")
            f.write("- `examples.wenhua_data_plugin`\n\n")

            f.write("**根本原因分析**:\n")
            f.write("1. `PluginManager.load_all_plugins()`扫描了多个目录（data_sources, examples等）\n")
            f.write("2. 但`PluginCenter._is_data_source_plugin()`检查过于严格，很多插件未通过验证\n")
            f.write("3. 检查标准:\n")
            f.write("   - 实现`IDataSourcePlugin`接口\n")
            f.write("   - 或包含`get_supported_data_types`和`fetch_data`方法\n")
            f.write("   - 或plugin_info中标记为DATA_SOURCE类型\n\n")

            f.write("## 修复详情\n\n")
            for i, fix in enumerate(self.fixes_applied, 1):
                f.write(f"### 修复{i}\n\n")
                f.write(f"```python\n{fix}\n```\n\n")

            if self.errors:
                f.write("## 遇到的错误\n\n")
                for i, error in enumerate(self.errors, 1):
                    f.write(f"{i}. {error}\n")

            f.write("\n## 建议的进一步行动\n\n")
            f.write("1. **验证修复效果**: 重新启动应用，查看是否还有相同错误\n")
            f.write("2. **增强插件加载日志**: 在PluginManager中添加更详细的日志，记录每个插件的加载状态\n")
            f.write("3. **放宽插件发现条件**: 考虑修改`_is_data_source_plugin`检查逻辑，使更多插件能被发现\n")
            f.write("4. **修复未被发现的插件**: 检查data_sources目录下的插件，确保它们实现了必要的接口\n")
            f.write("5. **添加插件健康检查**: 在插件加载后立即进行健康检查，及时发现问题\n")

        logger.info(f"\n详细报告已生成: {report_file}")


def main():
    """主函数"""
    fixer = CriticalDataRequestFixer()
    fixer.run()


if __name__ == "__main__":
    main()
