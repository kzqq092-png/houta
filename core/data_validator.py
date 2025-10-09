from loguru import logger
"""
专业级数据验证器模块
确保量化交易系统中数据的真实性、准确性和有效性
对标行业专业软件标准
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import warnings
# 纯Loguru架构，移除旧的日志导入

class ValidationLevel(Enum):
    """验证级别枚举"""
    BASIC = "basic"          # 基础验证
    STANDARD = "standard"    # 标准验证
    STRICT = "strict"        # 严格验证
    PROFESSIONAL = "professional"  # 专业级验证

class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"  # 优秀 (95-100%)
    GOOD = "good"           # 良好 (85-94%)
    FAIR = "fair"           # 一般 (70-84%)
    POOR = "poor"           # 较差 (<70%)

@dataclass
class ValidationResult:
    """验证结果数据类"""
    is_valid: bool
    quality_score: float  # 0-100分
    quality_level: DataQuality
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    metrics: Dict[str, Any]
    validation_time: datetime

class ProfessionalDataValidator:
    """
    专业级数据验证器
    对标行业专业软件标准，提供全面的数据质量控制
    """

    def __init__(self,
                 validation_level: ValidationLevel = ValidationLevel.PROFESSIONAL):
        """
        初始化专业级数据验证器

        Args:
            # log_manager: 已迁移到Loguru日志系统
            validation_level: 验证级别
        """
        # 纯Loguru架构，移除log_manager依赖
        self.validation_level = validation_level
        self.validation_rules = self._initialize_validation_rules()

    def _initialize_validation_rules(self) -> Dict[str, Dict]:
        """初始化验证规则"""
        return {
            "kline_data": {
                "required_columns": ["open", "high", "low", "close", "volume"],
                "optional_columns": ["amount", "datetime", "date"],
                "price_columns": ["open", "high", "low", "close"],
                "volume_columns": ["volume", "amount"],
                "min_records": 30,  # 最少记录数
                "max_price_change": 0.2,  # 最大单日涨跌幅 20%
                "max_volume_ratio": 50,   # 最大成交量比率
            },
            "financial_data": {
                "required_columns": ["pe", "pb", "roe", "eps"],
                "valid_ranges": {
                    "pe": (-100, 1000),
                    "pb": (0, 50),
                    "roe": (-1, 1),
                    "eps": (-10, 100)
                }
            },
            "industry_data": {
                "required_fields": ["code", "name", "industry"],
                "code_patterns": {
                    "SH": r"^(600|601|603|605|688)\d{3}$",
                    "SZ": r"^(000|001|002|003|300)\d{3}$",
                    "BJ": r"^[48]\d{5}$"
                }
            }
        }

    def validate_kline_data(self, data: pd.DataFrame,
                            stock_code: str = None) -> ValidationResult:
        """
        验证K线数据

        Args:
            data: K线数据DataFrame
            stock_code: 股票代码

        Returns:
            ValidationResult: 验证结果
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        suggestions = []
        metrics = {}

        try:
            # 1. 结构验证
            structure_score = self._validate_structure(
                data, "kline_data", errors, warnings)
            metrics["structure_score"] = structure_score

            # 2. 完整性验证
            completeness_score = self._validate_completeness(
                data, errors, warnings)
            metrics["completeness_score"] = completeness_score

            # 3. 一致性验证
            consistency_score = self._validate_consistency(
                data, errors, warnings)
            metrics["consistency_score"] = consistency_score

            # 4. 合理性验证
            reasonableness_score = self._validate_reasonableness(
                data, stock_code, errors, warnings)
            metrics["reasonableness_score"] = reasonableness_score

            # 5. 时间序列验证
            timeseries_score = self._validate_timeseries(
                data, errors, warnings)
            metrics["timeseries_score"] = timeseries_score

            # 计算总体质量分数
            quality_score = np.mean([
                structure_score, completeness_score, consistency_score,
                reasonableness_score, timeseries_score
            ])

            # 确定质量等级
            quality_level = self._determine_quality_level(quality_score)

            # 生成改进建议
            suggestions = self._generate_suggestions(metrics, errors, warnings)

            # 记录验证结果
            logger.info(
                f"K线数据验证完成 - 股票: {stock_code}, 质量分数: {quality_score:.2f}, "
                f"等级: {quality_level.value}, 错误: {len(errors)}, 警告: {len(warnings)}"
            )

            return ValidationResult(
                is_valid=len(errors) == 0,
                quality_score=quality_score,
                quality_level=quality_level,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                metrics=metrics,
                validation_time=start_time
            )

        except Exception as e:
            logger.error(f"数据验证异常: {str(e)}")
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                quality_level=DataQuality.POOR,
                errors=[f"验证过程异常: {str(e)}"],
                warnings=[],
                suggestions=["请检查数据格式和完整性"],
                metrics={},
                validation_time=start_time
            )

    def _validate_structure(self, data: pd.DataFrame, data_type: str,
                            errors: List[str], warnings: List[str]) -> float:
        """验证数据结构"""
        if data is None or data.empty:
            errors.append("数据为空")
            return 0.0

        rules = self.validation_rules.get(data_type, {})
        required_columns = rules.get("required_columns", [])

        # 检查必需列
        missing_columns = [
            col for col in required_columns if col not in data.columns]
        if missing_columns:
            errors.append(f"缺少必需列: {missing_columns}")
            return 0.0

        # 检查数据类型
        score = 100.0
        for col in required_columns:
            if col in data.columns:
                if not pd.api.types.is_numeric_dtype(data[col]):
                    warnings.append(f"列 {col} 应为数值类型")
                    score -= 10

        return max(0, score)

    def _validate_completeness(self, data: pd.DataFrame,
                               errors: List[str], warnings: List[str]) -> float:
        """验证数据完整性"""
        if data.empty:
            return 0.0

        total_cells = data.size
        missing_cells = data.isnull().sum().sum()
        completeness_ratio = 1 - (missing_cells / total_cells)

        score = completeness_ratio * 100

        if completeness_ratio < 0.95:
            warnings.append(f"数据完整性较低: {completeness_ratio:.2%}")
        if completeness_ratio < 0.8:
            errors.append(f"数据缺失严重: {completeness_ratio:.2%}")

        return score

    def _validate_consistency(self, data: pd.DataFrame,
                              errors: List[str], warnings: List[str]) -> float:
        """验证数据一致性"""
        score = 100.0

        # 检查OHLC关系
        if all(col in data.columns for col in ["open", "high", "low", "close"]):
            # High应该是最高价
            invalid_high = (
                data["high"] < data[["open", "close"]].max(axis=1)).sum()
            if invalid_high > 0:
                errors.append(f"发现 {invalid_high} 条记录的最高价不正确")
                score -= 20

            # Low应该是最低价
            invalid_low = (
                data["low"] > data[["open", "close"]].min(axis=1)).sum()
            if invalid_low > 0:
                errors.append(f"发现 {invalid_low} 条记录的最低价不正确")
                score -= 20

        # 检查成交量
        if "volume" in data.columns:
            negative_volume = (data["volume"] < 0).sum()
            if negative_volume > 0:
                errors.append(f"发现 {negative_volume} 条负成交量记录")
                score -= 15

        return max(0, score)

    def _validate_reasonableness(self, data: pd.DataFrame, stock_code: str,
                                 errors: List[str], warnings: List[str]) -> float:
        """验证数据合理性"""
        score = 100.0

        if "close" in data.columns and len(data) > 1:
            # 计算日收益率
            returns = data["close"].pct_change().dropna()

            # 检查异常涨跌幅
            max_change = self.validation_rules["kline_data"]["max_price_change"]
            extreme_changes = (abs(returns) > max_change).sum()

            if extreme_changes > 0:
                warnings.append(
                    f"发现 {extreme_changes} 个异常涨跌幅 (>{max_change:.1%})")
                score -= min(30, extreme_changes * 5)

            # 检查价格连续性
            zero_changes = (returns == 0).sum()
            if zero_changes > len(returns) * 0.1:  # 超过10%的交易日无变化
                warnings.append(f"价格变化异常: {zero_changes} 个交易日无变化")
                score -= 10

        return max(0, score)

    def _validate_timeseries(self, data: pd.DataFrame,
                             errors: List[str], warnings: List[str]) -> float:
        """验证时间序列数据"""
        score = 100.0

        # 检查时间列
        time_columns = ["datetime", "date"]
        time_col = None
        for col in time_columns:
            if col in data.columns:
                time_col = col
                break

        if time_col is None:
            warnings.append("未找到时间列，无法验证时间序列")
            return 80.0

        try:
            # 转换为datetime
            if not pd.api.types.is_datetime64_any_dtype(data[time_col]):
                time_series = pd.to_datetime(data[time_col])
            else:
                time_series = data[time_col]

            # 检查时间顺序
            if not time_series.is_monotonic_increasing:
                errors.append("时间序列不是递增的")
                score -= 30

            # 检查重复时间
            duplicates = time_series.duplicated().sum()
            if duplicates > 0:
                errors.append(f"发现 {duplicates} 个重复时间点")
                score -= 20

        except Exception as e:
            warnings.append(f"时间序列验证异常: {str(e)}")
            score -= 20

        return max(0, score)

    def _determine_quality_level(self, score: float) -> DataQuality:
        """确定数据质量等级"""
        if score >= 95:
            return DataQuality.EXCELLENT
        elif score >= 85:
            return DataQuality.GOOD
        elif score >= 70:
            return DataQuality.FAIR
        else:
            return DataQuality.POOR

    def _generate_suggestions(self, metrics: Dict[str, Any],
                              errors: List[str], warnings: List[str]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于分数生成建议
        if metrics.get("structure_score", 100) < 90:
            suggestions.append("建议检查数据结构和列名规范")

        if metrics.get("completeness_score", 100) < 90:
            suggestions.append("建议补充缺失数据或使用插值方法")

        if metrics.get("consistency_score", 100) < 90:
            suggestions.append("建议检查OHLC数据的逻辑一致性")

        if metrics.get("reasonableness_score", 100) < 90:
            suggestions.append("建议检查异常价格变动和数据来源")

        if metrics.get("timeseries_score", 100) < 90:
            suggestions.append("建议检查时间序列的连续性和准确性")

        # 基于错误和警告生成建议
        if len(errors) > 0:
            suggestions.append("存在严重数据问题，建议重新获取数据")

        if len(warnings) > 5:
            suggestions.append("数据质量问题较多，建议进行数据清洗")

        return suggestions

    def validate_batch_data(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, ValidationResult]:
        """
        批量验证数据

        Args:
            data_dict: 数据字典，键为股票代码，值为K线数据

        Returns:
            Dict[str, ValidationResult]: 验证结果字典
        """
        results = {}

        logger.info(f"开始批量验证 {len(data_dict)} 只股票的数据")

        for stock_code, data in data_dict.items():
            try:
                result = self.validate_kline_data(data, stock_code)
                results[stock_code] = result
            except Exception as e:
                logger.error(
                    f"验证股票 {stock_code} 数据失败: {str(e)}")
                results[stock_code] = ValidationResult(
                    is_valid=False,
                    quality_score=0.0,
                    quality_level=DataQuality.POOR,
                    errors=[f"验证异常: {str(e)}"],
                    warnings=[],
                    suggestions=["请检查数据格式"],
                    metrics={},
                    validation_time=datetime.now()
                )

        # 生成批量验证报告
        self._generate_batch_report(results)

        return results

    def _generate_batch_report(self, results: Dict[str, ValidationResult]) -> None:
        """生成批量验证报告"""
        total_stocks = len(results)
        valid_stocks = sum(1 for r in results.values() if r.is_valid)
        avg_score = np.mean([r.quality_score for r in results.values()])

        quality_distribution = {}
        for level in DataQuality:
            count = sum(1 for r in results.values()
                        if r.quality_level == level)
            quality_distribution[level.value] = count

        logger.info(
            f"批量验证报告 - 总数: {total_stocks}, 有效: {valid_stocks}, "
            f"平均分数: {avg_score:.2f}, 质量分布: {quality_distribution}"
        )

def create_data_validator(validation_level: ValidationLevel = ValidationLevel.PROFESSIONAL) -> ProfessionalDataValidator:
    """
    创建数据验证器实例

    Args:
        validation_level: 验证级别

    Returns:
        ProfessionalDataValidator: 数据验证器实例
    """
    return ProfessionalDataValidator(validation_level=validation_level)

# 创建别名以保持向后兼容
DataValidator = ProfessionalDataValidator

# 便捷函数

def validate_kline_data(data: pd.DataFrame, stock_code: str = None) -> ValidationResult:
    """
    快速验证K线数据

    Args:
        data: K线数据
        stock_code: 股票代码

    Returns:
        ValidationResult: 验证结果
    """
    validator = create_data_validator()
    return validator.validate_kline_data(data, stock_code)

def get_data_quality_report(data: pd.DataFrame, stock_code: str = None) -> Dict[str, Any]:
    """
    获取数据质量报告

    Args:
        data: K线数据
        stock_code: 股票代码

    Returns:
        Dict[str, Any]: 质量报告
    """
    result = validate_kline_data(data, stock_code)

    return {
        "stock_code": stock_code,
        "is_valid": result.is_valid,
        "quality_score": result.quality_score,
        "quality_level": result.quality_level.value,
        "error_count": len(result.errors),
        "warning_count": len(result.warnings),
        "suggestion_count": len(result.suggestions),
        "metrics": result.metrics,
        "validation_time": result.validation_time.isoformat()
    }
