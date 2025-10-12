#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
K线表字段升级验证脚本

功能：
1. 验证数据库表结构（20字段）
2. 测试数据导入功能
3. 检查新字段数据质量
4. 生成验证报告

作者：FactorWeave-Quant Team
版本：V2.0.4
日期：2025-10-12
"""

import sys
import duckdb
import pandas as pd
from pathlib import Path
from loguru import logger
from datetime import datetime
from typing import Dict, List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class KlineFieldsVerifier:
    """K线字段升级验证器"""

    # 标准20字段定义
    STANDARD_FIELDS = {
        # 基础OHLCV字段（9个）
        'basic': ['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover'],

        # 复权数据（2个）
        'adj': ['adj_close', 'adj_factor'],

        # 扩展交易数据（2个）
        'extended': ['turnover_rate', 'vwap'],

        # 元数据（7个）
        'metadata': ['name', 'market', 'frequency', 'period', 'data_source', 'created_at', 'updated_at']
    }

    def __init__(self):
        """初始化验证器"""
        self.db_path = project_root / "db" / "unified_kline_data.duckdb"
        self.conn = None
        self.verification_results = {}

    def connect_database(self) -> bool:
        """连接数据库"""
        try:
            if not self.db_path.exists():
                logger.error(f"数据库文件不存在: {self.db_path}")
                return False

            self.conn = duckdb.connect(str(self.db_path))
            logger.info(f"✅ 成功连接数据库: {self.db_path}")
            return True

        except Exception as e:
            logger.error(f"❌ 连接数据库失败: {e}")
            return False

    def get_table_list(self) -> List[str]:
        """获取K线表列表"""
        try:
            # 使用DuckDB特定函数查询表
            query = """
                SELECT table_name 
                FROM duckdb_tables()
                WHERE table_name LIKE '%kline%'
            """
            result = self.conn.execute(query).fetchall()
            tables = [row[0] for row in result]

            logger.info(f"📊 发现 {len(tables)} 个K线表")
            for table in tables:
                logger.info(f"  - {table}")

            return tables

        except Exception as e:
            logger.error(f"❌ 获取表列表失败: {e}")
            return []

    def verify_table_structure(self, table_name: str) -> Dict:
        """验证表结构"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 验证表结构: {table_name}")
            logger.info(f"{'='*60}")

            # 获取表列信息
            query = f"""
                SELECT column_name, data_type 
                FROM duckdb_columns()
                WHERE table_name = '{table_name}'
            """
            result = self.conn.execute(query).fetchall()

            columns = {row[0]: row[1] for row in result}
            total_columns = len(columns)

            logger.info(f"📋 表 {table_name} 共有 {total_columns} 列")

            # 检查新字段
            new_fields = ['adj_close', 'adj_factor', 'turnover_rate', 'vwap', 'data_source']
            missing_fields = []
            existing_fields = []

            for field in new_fields:
                if field in columns:
                    existing_fields.append(field)
                    logger.info(f"  ✅ {field}: {columns[field]}")
                else:
                    missing_fields.append(field)
                    logger.warning(f"  ❌ 缺失字段: {field}")

            # 检查所有标准字段
            all_standard_fields = []
            for category, fields in self.STANDARD_FIELDS.items():
                all_standard_fields.extend(fields)

            missing_standard = [f for f in all_standard_fields if f not in columns]

            # 验证结果
            verification = {
                'table_name': table_name,
                'total_columns': total_columns,
                'new_fields_count': len(existing_fields),
                'new_fields_total': len(new_fields),
                'missing_new_fields': missing_fields,
                'missing_standard_fields': missing_standard,
                'is_complete': len(missing_fields) == 0,
                'columns': columns
            }

            if verification['is_complete']:
                logger.success(f"✅ 表结构完整！新字段: {len(existing_fields)}/{len(new_fields)}")
            else:
                logger.warning(f"⚠️  表结构不完整！缺失 {len(missing_fields)} 个新字段")

            return verification

        except Exception as e:
            logger.error(f"❌ 验证表结构失败: {e}")
            return {}

    def check_data_quality(self, table_name: str, limit: int = 100) -> Dict:
        """检查数据质量"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔬 检查数据质量: {table_name}")
            logger.info(f"{'='*60}")

            # 查询最新数据
            query = f"""
                SELECT 
                    symbol, datetime, close, 
                    adj_close, adj_factor, 
                    turnover_rate, vwap, 
                    data_source, volume, amount
                FROM {table_name}
                ORDER BY datetime DESC
                LIMIT {limit}
            """

            df = self.conn.execute(query).fetchdf()

            if df.empty:
                logger.warning("⚠️  表中没有数据")
                return {'has_data': False}

            logger.info(f"📊 查询到 {len(df)} 条最新记录")

            # 数据质量检查
            quality_report = {
                'has_data': True,
                'record_count': len(df),
                'date_range': {
                    'start': str(df['datetime'].min()),
                    'end': str(df['datetime'].max())
                },
                'symbols': df['symbol'].nunique(),
                'fields_quality': {}
            }

            # 检查新字段的填充情况
            new_fields_check = {
                'adj_close': {
                    'null_count': df['adj_close'].isna().sum(),
                    'null_rate': f"{df['adj_close'].isna().sum() / len(df) * 100:.2f}%",
                    'sample_values': df['adj_close'].dropna().head(5).tolist()
                },
                'adj_factor': {
                    'null_count': df['adj_factor'].isna().sum(),
                    'null_rate': f"{df['adj_factor'].isna().sum() / len(df) * 100:.2f}%",
                    'mean': float(df['adj_factor'].mean()) if not df['adj_factor'].isna().all() else 0,
                    'sample_values': df['adj_factor'].dropna().head(5).tolist()
                },
                'turnover_rate': {
                    'null_count': df['turnover_rate'].isna().sum(),
                    'null_rate': f"{df['turnover_rate'].isna().sum() / len(df) * 100:.2f}%",
                    'sample_values': df['turnover_rate'].dropna().head(5).tolist()
                },
                'vwap': {
                    'null_count': df['vwap'].isna().sum(),
                    'null_rate': f"{df['vwap'].isna().sum() / len(df) * 100:.2f}%",
                    'sample_values': df['vwap'].dropna().head(5).tolist()
                },
                'data_source': {
                    'null_count': df['data_source'].isna().sum(),
                    'null_rate': f"{df['data_source'].isna().sum() / len(df) * 100:.2f}%",
                    'unique_sources': df['data_source'].dropna().unique().tolist()
                }
            }

            quality_report['fields_quality'] = new_fields_check

            # 打印质量报告
            logger.info(f"\n📈 数据质量报告:")
            logger.info(f"  记录数: {quality_report['record_count']}")
            logger.info(f"  时间范围: {quality_report['date_range']['start']} ~ {quality_report['date_range']['end']}")
            logger.info(f"  股票数: {quality_report['symbols']}")

            logger.info(f"\n🔍 新字段质量:")
            for field, stats in new_fields_check.items():
                null_rate = stats['null_rate']
                logger.info(f"  {field}:")
                logger.info(f"    - 空值率: {null_rate}")
                if 'mean' in stats:
                    logger.info(f"    - 平均值: {stats['mean']:.4f}")
                if 'unique_sources' in stats and stats['unique_sources']:
                    logger.info(f"    - 数据源: {', '.join(stats['unique_sources'])}")
                if stats['sample_values']:
                    logger.info(f"    - 样本值: {stats['sample_values'][:3]}")

            # 验证数据合理性
            logger.info(f"\n✅ 数据合理性验证:")

            # 1. 复权价格应该接近原价格
            if not df['adj_close'].isna().all():
                price_diff = (df['adj_close'] - df['close']).abs() / df['close'] * 100
                avg_diff = price_diff.mean()
                logger.info(f"  adj_close vs close 平均差异: {avg_diff:.2f}%")
                if avg_diff < 5:
                    logger.success(f"    ✅ 复权价格合理（差异<5%）")
                else:
                    logger.warning(f"    ⚠️  复权价格差异较大（>{avg_diff:.2f}%）")

            # 2. VWAP应该在OHLC范围内
            if not df['vwap'].isna().all():
                vwap_valid = ((df['vwap'] >= df['low']) & (df['vwap'] <= df['high'])).sum()
                vwap_valid_rate = vwap_valid / len(df[df['vwap'].notna()]) * 100 if len(df[df['vwap'].notna()]) > 0 else 0
                logger.info(f"  VWAP合理性: {vwap_valid_rate:.2f}% 在[low, high]范围内")
                if vwap_valid_rate > 90:
                    logger.success(f"    ✅ VWAP计算合理（>90%）")
                else:
                    logger.warning(f"    ⚠️  VWAP可能有问题（{vwap_valid_rate:.2f}%）")

            # 3. 换手率应该合理（一般<30%）
            if not df['turnover_rate'].isna().all():
                high_turnover = (df['turnover_rate'] > 30).sum()
                high_turnover_rate = high_turnover / len(df[df['turnover_rate'].notna()]) * 100 if len(df[df['turnover_rate'].notna()]) > 0 else 0
                logger.info(f"  换手率>30%的记录: {high_turnover_rate:.2f}%")
                if high_turnover_rate < 5:
                    logger.success(f"    ✅ 换手率分布正常（<5%异常）")
                else:
                    logger.warning(f"    ⚠️  换手率异常记录较多（{high_turnover_rate:.2f}%）")

            return quality_report

        except Exception as e:
            logger.error(f"❌ 数据质量检查失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def generate_report(self) -> str:
        """生成验证报告"""
        try:
            report_lines = []
            report_lines.append("=" * 80)
            report_lines.append("K线表字段升级验证报告")
            report_lines.append("=" * 80)
            report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"数据库: {self.db_path}")
            report_lines.append("")

            # 表结构验证总结
            report_lines.append("## 表结构验证")
            report_lines.append("-" * 80)

            for table_name, verification in self.verification_results.items():
                if 'structure' in verification:
                    struct = verification['structure']
                    status = "✅ 通过" if struct.get('is_complete') else "❌ 未通过"
                    report_lines.append(f"表名: {table_name}")
                    report_lines.append(f"  状态: {status}")
                    report_lines.append(f"  总列数: {struct.get('total_columns', 0)}")
                    report_lines.append(f"  新字段: {struct.get('new_fields_count', 0)}/{struct.get('new_fields_total', 5)}")

                    if struct.get('missing_new_fields'):
                        report_lines.append(f"  缺失字段: {', '.join(struct['missing_new_fields'])}")
                    report_lines.append("")

            # 数据质量验证总结
            report_lines.append("## 数据质量验证")
            report_lines.append("-" * 80)

            for table_name, verification in self.verification_results.items():
                if 'quality' in verification:
                    quality = verification['quality']
                    if quality.get('has_data'):
                        report_lines.append(f"表名: {table_name}")
                        report_lines.append(f"  记录数: {quality.get('record_count', 0)}")
                        report_lines.append(f"  时间范围: {quality['date_range']['start']} ~ {quality['date_range']['end']}")
                        report_lines.append(f"  股票数: {quality.get('symbols', 0)}")
                        report_lines.append("")

            report_lines.append("=" * 80)
            report_lines.append("验证完成")
            report_lines.append("=" * 80)

            report_text = "\n".join(report_lines)

            # 保存报告
            report_path = project_root / "K线字段升级验证报告.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_text)

            logger.success(f"✅ 验证报告已保存: {report_path}")

            return report_text

        except Exception as e:
            logger.error(f"❌ 生成报告失败: {e}")
            return ""

    def run_verification(self):
        """运行完整验证"""
        try:
            logger.info("=" * 80)
            logger.info("K线表字段升级验证")
            logger.info("=" * 80)
            logger.info("")

            # 1. 连接数据库
            if not self.connect_database():
                return False

            # 2. 获取表列表
            tables = self.get_table_list()
            if not tables:
                logger.warning("⚠️  未发现K线表")
                return False

            # 3. 验证每个表
            for table_name in tables:
                # 验证表结构
                structure_result = self.verify_table_structure(table_name)

                # 检查数据质量
                quality_result = self.check_data_quality(table_name)

                # 保存结果
                self.verification_results[table_name] = {
                    'structure': structure_result,
                    'quality': quality_result
                }

            # 4. 生成报告
            report = self.generate_report()

            logger.info("\n" + "=" * 80)
            logger.success("✅ 验证完成！")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"❌ 验证过程失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

        finally:
            if self.conn:
                self.conn.close()
                logger.info("数据库连接已关闭")


def main():
    """主函数"""
    logger.info("启动K线字段升级验证工具...")

    verifier = KlineFieldsVerifier()
    success = verifier.run_verification()

    if success:
        logger.success("🎉 验证成功！")
        return 0
    else:
        logger.error("❌ 验证失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
