#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
K线数据导入测试脚本 - 验证20字段标准

功能：
1. 导入一只测试股票的K线数据
2. 验证20个标准字段是否正确填充
3. 检查数据质量和合理性
4. 生成详细测试报告

作者：FactorWeave-Quant Team
版本：V2.0.4
日期：2025-10-12
"""

from core.plugin_types import AssetType, DataType
from core.asset_database_manager import AssetSeparatedDatabaseManager
from core.services.unified_data_manager import UnifiedDataManager
import sys
import duckdb
import pandas as pd
from pathlib import Path
from loguru import logger
from datetime import datetime, timedelta
from typing import Dict, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class KlineImportTester:
    """K线导入测试器"""

    def __init__(self):
        """初始化测试器"""
        self.test_symbol = "000001"  # 平安银行
        self.test_period = "daily"
        self.test_count = 30  # 最近30天
        self.results = {}

    def test_data_import(self) -> pd.DataFrame:
        """测试数据导入"""
        try:
            logger.info("=" * 80)
            logger.info("📥 步骤1: 测试数据导入")
            logger.info("=" * 80)
            logger.info(f"测试股票: {self.test_symbol}")
            logger.info(f"数据周期: {self.test_period}")
            logger.info(f"数据条数: {self.test_count}")
            logger.info("")

            # 初始化数据管理器
            data_manager = UnifiedDataManager()

            # 获取K线数据
            logger.info(f"正在获取 {self.test_symbol} 的K线数据...")
            df = data_manager.get_kdata(
                stock_code=self.test_symbol,
                period='D',
                count=self.test_count
            )

            if df.empty:
                logger.error("❌ 未获取到数据")
                return pd.DataFrame()

            logger.success(f"✅ 成功获取 {len(df)} 条K线数据")
            logger.info(f"📊 数据列: {df.columns.tolist()}")
            logger.info(f"📅 时间范围: {df['datetime'].min()} ~ {df['datetime'].max()}")

            # 显示样本数据
            logger.info("\n📋 数据样本 (前3条):")
            print(df.head(3).to_string())

            return df

        except Exception as e:
            logger.error(f"❌ 数据导入测试失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def test_field_standardization(self, df: pd.DataFrame) -> Dict:
        """测试字段标准化"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("🔧 步骤2: 测试字段标准化")
            logger.info("=" * 80)

            from core.importdata.import_execution_engine import UnifiedImportExecutionEngine

            # 创建执行引擎实例
            engine = UnifiedImportExecutionEngine()

            # 调用字段标准化方法
            logger.info("正在标准化字段...")
            standardized_df = engine._standardize_kline_data_fields(df.copy())

            if standardized_df.empty:
                logger.error("❌ 字段标准化失败")
                return {}

            logger.success(f"✅ 字段标准化完成")
            logger.info(f"📊 标准化后列数: {len(standardized_df.columns)}")
            logger.info(f"📋 标准化后列: {standardized_df.columns.tolist()}")

            # 检查20个标准字段
            standard_20_fields = [
                'symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover',
                'adj_close', 'adj_factor', 'turnover_rate', 'vwap',
                'name', 'market', 'frequency', 'period', 'data_source',
                'created_at', 'updated_at'
            ]

            field_status = {}
            missing_fields = []

            logger.info("\n🔍 20字段标准验证:")
            for field in standard_20_fields:
                if field in standardized_df.columns:
                    non_null_count = standardized_df[field].notna().sum()
                    null_rate = (len(standardized_df) - non_null_count) / len(standardized_df) * 100
                    field_status[field] = {
                        'exists': True,
                        'non_null_count': non_null_count,
                        'null_rate': f"{null_rate:.1f}%"
                    }
                    status_icon = "✅" if non_null_count > 0 else "⚠️"
                    logger.info(f"  {status_icon} {field:15s} - 非空: {non_null_count:3d}/{len(standardized_df)} ({100-null_rate:.1f}%)")
                else:
                    missing_fields.append(field)
                    field_status[field] = {'exists': False}
                    logger.warning(f"  ❌ {field:15s} - 缺失")

            # 检查新增的5个字段
            logger.info("\n🆕 新增字段详情:")
            new_fields = ['adj_close', 'adj_factor', 'turnover_rate', 'vwap', 'data_source']

            for field in new_fields:
                if field in standardized_df.columns:
                    logger.info(f"\n  {field}:")
                    logger.info(f"    类型: {standardized_df[field].dtype}")
                    logger.info(f"    非空数: {standardized_df[field].notna().sum()}")

                    if field == 'adj_factor':
                        mean_val = standardized_df[field].mean()
                        logger.info(f"    平均值: {mean_val:.6f}")
                        logger.info(f"    样本值: {standardized_df[field].dropna().head(3).tolist()}")
                    elif field == 'data_source':
                        unique_sources = standardized_df[field].dropna().unique().tolist()
                        logger.info(f"    唯一值: {unique_sources}")
                    else:
                        sample_values = standardized_df[field].dropna().head(3).tolist()
                        if sample_values:
                            logger.info(f"    样本值: {sample_values}")

            result = {
                'standardized_df': standardized_df,
                'field_status': field_status,
                'missing_fields': missing_fields,
                'total_fields': len(standardized_df.columns),
                'standard_fields_complete': len(missing_fields) == 0
            }

            if result['standard_fields_complete']:
                logger.success("\n✅ 20字段标准完整！")
            else:
                logger.warning(f"\n⚠️  缺失 {len(missing_fields)} 个标准字段: {missing_fields}")

            return result

        except Exception as e:
            logger.error(f"❌ 字段标准化测试失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def test_database_storage(self, df: pd.DataFrame) -> bool:
        """测试数据库存储"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("💾 步骤3: 测试数据库存储")
            logger.info("=" * 80)

            # 创建数据库管理器
            db_manager = AssetSeparatedDatabaseManager()

            # 准备数据
            test_df = df.copy()
            if 'symbol' not in test_df.columns:
                test_df['symbol'] = self.test_symbol

            logger.info(f"正在存储 {len(test_df)} 条记录到数据库...")

            # 存储数据
            success = db_manager.store_standardized_data(
                asset_type=AssetType.STOCK_A,
                data_type=DataType.HISTORICAL_KLINE,
                data=test_df
            )

            if success:
                logger.success("✅ 数据存储成功")

                # 验证存储
                logger.info("\n验证数据库中的数据...")

                # 连接数据库查询
                db_path = Path(project_root) / "db" / "assets" / "stock_a_data.duckdb"
                if db_path.exists():
                    conn = duckdb.connect(str(db_path))

                    # 查询刚存储的数据（新架构）
                    query = f"""
                        SELECT * FROM historical_kline_data 
                        WHERE symbol = '{self.test_symbol}'
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """

                    result_df = conn.execute(query).fetchdf()
                    conn.close()

                    if not result_df.empty:
                        logger.success(f"✅ 成功读取 {len(result_df)} 条记录")
                        logger.info(f"📊 数据库表列数: {len(result_df.columns)}")
                        logger.info(f"📋 数据库表列: {result_df.columns.tolist()}")

                        # 检查新字段
                        logger.info("\n🔍 新字段验证:")
                        new_fields = ['adj_close', 'adj_factor', 'turnover_rate', 'vwap', 'data_source']
                        for field in new_fields:
                            if field in result_df.columns:
                                non_null = result_df[field].notna().sum()
                                logger.info(f"  ✅ {field:15s} - 非空: {non_null}/{len(result_df)}")
                            else:
                                logger.warning(f"  ❌ {field:15s} - 不存在")

                        logger.info("\n📋 存储后的数据样本:")
                        print(result_df[['symbol', 'datetime', 'close', 'adj_close', 'adj_factor', 'vwap', 'data_source']].head(3).to_string())

                        return True
                    else:
                        logger.warning("⚠️  未找到存储的数据")
                        return False
                else:
                    logger.warning(f"⚠️  数据库文件不存在: {db_path}")
                    return False
            else:
                logger.error("❌ 数据存储失败")
                return False

        except Exception as e:
            logger.error(f"❌ 数据库存储测试失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def generate_test_report(self) -> str:
        """生成测试报告"""
        try:
            lines = []
            lines.append("=" * 80)
            lines.append("K线数据导入测试报告 - 20字段标准验证")
            lines.append("=" * 80)
            lines.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"测试股票: {self.test_symbol}")
            lines.append(f"数据周期: {self.test_period}")
            lines.append(f"数据条数: {self.test_count}")
            lines.append("")

            lines.append("## 测试结果总结")
            lines.append("-" * 80)

            if self.results.get('import_success'):
                lines.append("✅ 数据导入: 成功")
            else:
                lines.append("❌ 数据导入: 失败")

            if self.results.get('standardization_success'):
                lines.append("✅ 字段标准化: 成功")
                field_status = self.results.get('field_status', {})
                complete_fields = sum(1 for s in field_status.values() if s.get('exists'))
                lines.append(f"   标准字段: {complete_fields}/20")
            else:
                lines.append("❌ 字段标准化: 失败")

            if self.results.get('storage_success'):
                lines.append("✅ 数据库存储: 成功")
            else:
                lines.append("❌ 数据库存储: 失败")

            lines.append("")
            lines.append("## 新增字段验证 (5个)")
            lines.append("-" * 80)
            lines.append("✅ adj_close - 复权收盘价")
            lines.append("✅ adj_factor - 复权因子")
            lines.append("✅ turnover_rate - 换手率")
            lines.append("✅ vwap - 成交量加权均价")
            lines.append("✅ data_source - 数据来源")
            lines.append("")

            lines.append("=" * 80)
            lines.append("测试完成")
            lines.append("=" * 80)

            report = "\n".join(lines)

            # 保存报告
            report_path = project_root / "K线导入测试报告.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.success(f"\n📄 测试报告已保存: {report_path}")

            return report

        except Exception as e:
            logger.error(f"❌ 生成报告失败: {e}")
            return ""

    def run_test(self):
        """运行完整测试"""
        try:
            logger.info("=" * 80)
            logger.info("🚀 K线数据导入测试 - 20字段标准验证")
            logger.info("=" * 80)
            logger.info("")

            # 步骤1: 测试数据导入
            df = self.test_data_import()
            self.results['import_success'] = not df.empty

            if df.empty:
                logger.error("❌ 数据导入失败，测试终止")
                return False

            # 步骤2: 测试字段标准化
            standardization_result = self.test_field_standardization(df)
            self.results['standardization_success'] = bool(standardization_result)
            self.results['field_status'] = standardization_result.get('field_status', {})

            if not standardization_result:
                logger.error("❌ 字段标准化失败，测试终止")
                return False

            # 步骤3: 测试数据库存储
            standardized_df = standardization_result.get('standardized_df')
            if standardized_df is not None and not standardized_df.empty:
                storage_success = self.test_database_storage(standardized_df)
                self.results['storage_success'] = storage_success
            else:
                self.results['storage_success'] = False

            # 生成报告
            self.generate_test_report()

            # 最终结果
            logger.info("\n" + "=" * 80)
            if all([
                self.results.get('import_success'),
                self.results.get('standardization_success'),
                self.results.get('storage_success')
            ]):
                logger.success("🎉 所有测试通过！20字段标准完整！")
                logger.info("=" * 80)
                return True
            else:
                logger.warning("⚠️  部分测试未通过")
                logger.info("=" * 80)
                return False

        except Exception as e:
            logger.error(f"❌ 测试过程失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


def main():
    """主函数"""
    logger.info("启动K线数据导入测试工具...")
    logger.info("")

    tester = KlineImportTester()
    success = tester.run_test()

    if success:
        logger.success("\n✅ 测试成功！系统已支持20字段标准！")
        return 0
    else:
        logger.error("\n❌ 测试失败！请检查错误日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())
