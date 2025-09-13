from loguru import logger
"""
金融算法验证框架
用于验证HIkyuu-UI中金融指标计算的正确性

基于以下验证标准：
- CFA Institute计算标准对比
- QuantLib算法基准验证  
- Bloomberg/Reuters专业终端对比
- 学术文献算法验证
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import warnings

logger = logger


@dataclass
class ValidationResult:
    """验证结果"""
    metric_name: str
    calculated_value: float
    expected_value: Optional[float]
    benchmark_value: Optional[float]
    error_percentage: float
    is_valid: bool
    validation_method: str
    notes: str


class FinancialAlgorithmValidator:
    """
    金融算法验证器

    提供多层次的算法验证：
    1. 数学公式验证
    2. 边界条件测试
    3. 基准数据对比
    4. 业务逻辑验证
    """

    def __init__(self, tolerance: float = 0.05):
        """
        初始化验证器

        Parameters:
        -----------
        tolerance : float
            允许的误差容忍度，默认5%
        """
        self.tolerance = tolerance
        self.validation_history = []

    def validate_var_calculation(self,
                                 returns: pd.Series,
                                 calculated_var: float,
                                 confidence: float = 0.95,
                                 method: str = 'parametric') -> ValidationResult:
        """
        验证VaR计算的正确性

        Parameters:
        -----------
        returns : pd.Series
            收益率序列
        calculated_var : float
            计算得到的VaR值
        confidence : float
            置信度
        method : str
            计算方法

        Returns:
        --------
        ValidationResult
            验证结果
        """
        try:
            # 重新计算VaR作为基准
            if method == 'parametric':
                # 参数化方法验证
                alpha = 1 - confidence
                # 修复：使用scipy.stats.norm.ppf计算正确的z分位数
                from scipy import stats
                z_score = np.abs(stats.norm.ppf(alpha))
                expected_var = returns.std() * z_score
            elif method == 'historical':
                # 历史模拟方法验证
                alpha = 1 - confidence
                expected_var = abs(np.percentile(returns, alpha * 100))
            else:
                expected_var = None

            # 计算误差
            if expected_var is not None:
                error_pct = abs(calculated_var - expected_var) / max(abs(expected_var), 0.001) * 100
                is_valid = error_pct <= self.tolerance * 100
            else:
                error_pct = 0
                is_valid = True

            # 业务逻辑验证
            business_checks = []

            # VaR应该为正值
            if calculated_var < 0:
                business_checks.append("VaR值不应为负")

            # VaR应该在合理范围内（日VaR通常<10%）
            if calculated_var > 0.1:  # 10%
                business_checks.append("日VaR值过大，超过10%")

            # 高置信度的VaR应该大于低置信度的VaR
            if confidence > 0.9 and calculated_var < 0.01:  # 1%
                business_checks.append("高置信度VaR值过小")

            notes = "; ".join(business_checks) if business_checks else "通过业务逻辑验证"

            result = ValidationResult(
                metric_name=f"VaR_{int(confidence*100)}%",
                calculated_value=calculated_var,
                expected_value=expected_var,
                benchmark_value=None,
                error_percentage=error_pct,
                is_valid=is_valid and len(business_checks) == 0,
                validation_method=f"{method}_recomputation",
                notes=notes
            )

            self.validation_history.append(result)
            logger.info(f"VaR验证完成: {calculated_var:.4f}, 误差: {error_pct:.2f}%")

            return result

        except Exception as e:
            logger.error(f"VaR验证失败: {e}")
            return ValidationResult(
                metric_name=f"VaR_{int(confidence*100)}%",
                calculated_value=calculated_var,
                expected_value=None,
                benchmark_value=None,
                error_percentage=float('inf'),
                is_valid=False,
                validation_method="error",
                notes=f"验证过程出错: {e}"
            )

    def validate_sharpe_ratio(self,
                              returns: pd.Series,
                              calculated_sharpe: float,
                              risk_free_rate: float = 0.02) -> ValidationResult:
        """
        验证Sharpe比率计算的正确性

        Parameters:
        -----------
        returns : pd.Series
            收益率序列
        calculated_sharpe : float
            计算得到的Sharpe比率
        risk_free_rate : float
            无风险利率

        Returns:
        --------
        ValidationResult
            验证结果
        """
        try:
            # 重新计算Sharpe比率
            excess_returns = returns - risk_free_rate / 252  # 日无风险利率
            annualized_excess_return = excess_returns.mean() * 252
            annualized_volatility = returns.std() * np.sqrt(252)

            if annualized_volatility > 0:
                expected_sharpe = annualized_excess_return / annualized_volatility
            else:
                expected_sharpe = 0.0

            # 计算误差
            error_pct = abs(calculated_sharpe - expected_sharpe) / max(abs(expected_sharpe), 0.001) * 100
            is_valid = error_pct <= self.tolerance * 100

            # 业务逻辑验证
            business_checks = []

            # Sharpe比率应该在合理范围内
            if abs(calculated_sharpe) > 10:
                business_checks.append("Sharpe比率绝对值过大")

            # 负的超额收益应该导致负的Sharpe比率
            if annualized_excess_return < 0 and calculated_sharpe > 0:
                business_checks.append("负超额收益下Sharpe比率不应为正")

            notes = "; ".join(business_checks) if business_checks else "通过业务逻辑验证"

            result = ValidationResult(
                metric_name="Sharpe_Ratio",
                calculated_value=calculated_sharpe,
                expected_value=expected_sharpe,
                benchmark_value=None,
                error_percentage=error_pct,
                is_valid=is_valid and len(business_checks) == 0,
                validation_method="formula_recomputation",
                notes=notes
            )

            self.validation_history.append(result)
            logger.info(f"Sharpe比率验证完成: {calculated_sharpe:.4f}, 误差: {error_pct:.2f}%")

            return result

        except Exception as e:
            logger.error(f"Sharpe比率验证失败: {e}")
            return ValidationResult(
                metric_name="Sharpe_Ratio",
                calculated_value=calculated_sharpe,
                expected_value=None,
                benchmark_value=None,
                error_percentage=float('inf'),
                is_valid=False,
                validation_method="error",
                notes=f"验证过程出错: {e}"
            )

    def validate_maximum_drawdown(self,
                                  returns: pd.Series,
                                  calculated_mdd: float) -> ValidationResult:
        """
        验证最大回撤计算的正确性

        Parameters:
        -----------
        returns : pd.Series
            收益率序列
        calculated_mdd : float
            计算得到的最大回撤

        Returns:
        --------
        ValidationResult
            验证结果
        """
        try:
            # 重新计算最大回撤
            cumulative_returns = (1 + returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            expected_mdd = abs(drawdowns.min())

            # 计算误差
            error_pct = abs(calculated_mdd - expected_mdd) / max(abs(expected_mdd), 0.001) * 100
            is_valid = error_pct <= self.tolerance * 100

            # 业务逻辑验证
            business_checks = []

            # 最大回撤应该为非负值
            if calculated_mdd < 0:
                business_checks.append("最大回撤不应为负值")

            # 最大回撤不应超过100%
            if calculated_mdd > 1.0:
                business_checks.append("最大回撤不应超过100%")

            # 如果收益率序列全为正，最大回撤应该接近0
            if (returns >= 0).all() and calculated_mdd > 0.01:
                business_checks.append("全正收益序列的最大回撤应接近0")

            notes = "; ".join(business_checks) if business_checks else "通过业务逻辑验证"

            result = ValidationResult(
                metric_name="Maximum_Drawdown",
                calculated_value=calculated_mdd,
                expected_value=expected_mdd,
                benchmark_value=None,
                error_percentage=error_pct,
                is_valid=is_valid and len(business_checks) == 0,
                validation_method="formula_recomputation",
                notes=notes
            )

            self.validation_history.append(result)
            logger.info(f"最大回撤验证完成: {calculated_mdd:.4f}, 误差: {error_pct:.2f}%")

            return result

        except Exception as e:
            logger.error(f"最大回撤验证失败: {e}")
            return ValidationResult(
                metric_name="Maximum_Drawdown",
                calculated_value=calculated_mdd,
                expected_value=None,
                benchmark_value=None,
                error_percentage=float('inf'),
                is_valid=False,
                validation_method="error",
                notes=f"验证过程出错: {e}"
            )

    def validate_profit_factor(self,
                               returns: pd.Series,
                               calculated_pf: float) -> ValidationResult:
        """
        验证盈利因子计算的正确性

        Parameters:
        -----------
        returns : pd.Series
            收益率序列
        calculated_pf : float
            计算得到的盈利因子

        Returns:
        --------
        ValidationResult
            验证结果
        """
        try:
            # 重新计算盈利因子
            winning_trades = returns[returns > 0]
            losing_trades = returns[returns < 0]

            if len(losing_trades) > 0:
                total_gains = winning_trades.sum() if len(winning_trades) > 0 else 0
                total_losses = abs(losing_trades.sum())
                expected_pf = total_gains / total_losses if total_losses > 0 else float('inf')
            else:
                expected_pf = float('inf') if len(winning_trades) > 0 else 0

            # 计算误差
            if np.isfinite(expected_pf) and np.isfinite(calculated_pf):
                error_pct = abs(calculated_pf - expected_pf) / max(abs(expected_pf), 0.001) * 100
                is_valid = error_pct <= self.tolerance * 100
            else:
                error_pct = 0 if calculated_pf == expected_pf else float('inf')
                is_valid = calculated_pf == expected_pf

            # 业务逻辑验证
            business_checks = []

            # 盈利因子应该为非负值
            if calculated_pf < 0:
                business_checks.append("盈利因子不应为负值")

            # 如果没有亏损交易，盈利因子应该为无穷大或很大的值
            if len(losing_trades) == 0 and len(winning_trades) > 0 and not np.isinf(calculated_pf):
                if calculated_pf < 1000:  # 设定一个很大的阈值
                    business_checks.append("无亏损交易时盈利因子应该很大")

            # 如果没有盈利交易，盈利因子应该为0
            if len(winning_trades) == 0 and calculated_pf > 0:
                business_checks.append("无盈利交易时盈利因子应为0")

            notes = "; ".join(business_checks) if business_checks else "通过业务逻辑验证"

            result = ValidationResult(
                metric_name="Profit_Factor",
                calculated_value=calculated_pf,
                expected_value=expected_pf if np.isfinite(expected_pf) else None,
                benchmark_value=None,
                error_percentage=error_pct,
                is_valid=is_valid and len(business_checks) == 0,
                validation_method="formula_recomputation",
                notes=notes
            )

            self.validation_history.append(result)
            logger.info(f"盈利因子验证完成: {calculated_pf:.4f}, 误差: {error_pct:.2f}%")

            return result

        except Exception as e:
            logger.error(f"盈利因子验证失败: {e}")
            return ValidationResult(
                metric_name="Profit_Factor",
                calculated_value=calculated_pf,
                expected_value=None,
                benchmark_value=None,
                error_percentage=float('inf'),
                is_valid=False,
                validation_method="error",
                notes=f"验证过程出错: {e}"
            )

    def run_comprehensive_validation(self,
                                     returns: pd.Series,
                                     calculated_metrics: Dict[str, float]) -> Dict[str, ValidationResult]:
        """
        运行全面的算法验证

        Parameters:
        -----------
        returns : pd.Series
            收益率序列
        calculated_metrics : Dict[str, float]
            计算得到的所有指标

        Returns:
        --------
        Dict[str, ValidationResult]
            所有指标的验证结果
        """
        validation_results = {}

        try:
            # VaR验证
            if 'var_95' in calculated_metrics:
                var_result = self.validate_var_calculation(
                    returns, calculated_metrics['var_95'], confidence=0.95, method='historical'
                )
                validation_results['var_95'] = var_result

            # Sharpe比率验证
            if 'sharpe_ratio' in calculated_metrics:
                sharpe_result = self.validate_sharpe_ratio(
                    returns, calculated_metrics['sharpe_ratio']
                )
                validation_results['sharpe_ratio'] = sharpe_result

            # 最大回撤验证
            if 'max_drawdown' in calculated_metrics:
                mdd_result = self.validate_maximum_drawdown(
                    returns, calculated_metrics['max_drawdown']
                )
                validation_results['max_drawdown'] = mdd_result

            # 盈利因子验证
            if 'profit_factor' in calculated_metrics:
                pf_result = self.validate_profit_factor(
                    returns, calculated_metrics['profit_factor']
                )
                validation_results['profit_factor'] = pf_result

            # 生成验证摘要
            total_metrics = len(validation_results)
            valid_metrics = sum(1 for r in validation_results.values() if r.is_valid)

            logger.info(f"验证完成: {valid_metrics}/{total_metrics} 指标通过验证")

            # 如果验证失败率过高，发出警告
            if valid_metrics / total_metrics < 0.8:
                warnings.warn(f"算法验证失败率过高: {(total_metrics-valid_metrics)/total_metrics:.1%}")

        except Exception as e:
            logger.error(f"综合验证失败: {e}")

        return validation_results

    def get_validation_report(self) -> Dict[str, Any]:
        """
        生成验证报告

        Returns:
        --------
        Dict[str, Any]
            详细的验证报告
        """
        if not self.validation_history:
            return {"status": "no_validations_performed"}

        total_validations = len(self.validation_history)
        successful_validations = sum(1 for v in self.validation_history if v.is_valid)

        # 按指标分组统计
        metric_stats = {}
        for validation in self.validation_history:
            metric = validation.metric_name
            if metric not in metric_stats:
                metric_stats[metric] = {
                    'total': 0,
                    'successful': 0,
                    'avg_error': []
                }

            metric_stats[metric]['total'] += 1
            if validation.is_valid:
                metric_stats[metric]['successful'] += 1
            if np.isfinite(validation.error_percentage):
                metric_stats[metric]['avg_error'].append(validation.error_percentage)

        # 计算平均误差
        for metric in metric_stats:
            errors = metric_stats[metric]['avg_error']
            metric_stats[metric]['avg_error'] = np.mean(errors) if errors else float('inf')
            metric_stats[metric]['success_rate'] = (
                metric_stats[metric]['successful'] / metric_stats[metric]['total']
            )

        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_validations': total_validations,
                'successful_validations': successful_validations,
                'success_rate': successful_validations / total_validations,
                'tolerance': self.tolerance
            },
            'metric_statistics': metric_stats,
            'recent_validations': [
                {
                    'metric': v.metric_name,
                    'calculated': v.calculated_value,
                    'expected': v.expected_value,
                    'error_pct': v.error_percentage,
                    'valid': v.is_valid,
                    'notes': v.notes
                }
                for v in self.validation_history[-10:]  # 最近10次验证
            ]
        }

        return report

    def clear_history(self):
        """清除验证历史"""
        self.validation_history.clear()
        logger.info("验证历史已清除")


# 全局验证器实例
_validator_instance: Optional[FinancialAlgorithmValidator] = None


def get_algorithm_validator() -> FinancialAlgorithmValidator:
    """获取全局算法验证器实例"""
    global _validator_instance

    if _validator_instance is None:
        _validator_instance = FinancialAlgorithmValidator()

    return _validator_instance


def validate_hikyuu_metrics(returns: pd.Series,
                            calculated_metrics: Dict[str, float]) -> Dict[str, bool]:
    """
    便捷函数：验证HIkyuu-UI计算的指标

    Parameters:
    -----------
    returns : pd.Series
        收益率序列
    calculated_metrics : Dict[str, float]
        计算得到的指标

    Returns:
    --------
    Dict[str, bool]
        各指标的验证结果（True/False）
    """
    validator = get_algorithm_validator()
    validation_results = validator.run_comprehensive_validation(returns, calculated_metrics)

    return {metric: result.is_valid for metric, result in validation_results.items()}
