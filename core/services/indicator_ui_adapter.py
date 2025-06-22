"""
指标服务UI适配器
用于连接新的指标计算服务和现有的UI组件，提供向后兼容的接口
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import logging

from .indicator_service import get_indicator_service, IndicatorInfo, IndicatorCategory


class IndicatorUIAdapter:
    """指标服务UI适配器 - 完全基于新架构"""

    def __init__(self):
        """初始化适配器"""
        self.logger = logging.getLogger(__name__)
        self.indicator_service = get_indicator_service()

    def get_indicator_list(self, use_chinese: bool = False) -> List[str]:
        """获取指标列表 - UI适配方法"""
        try:
            return self.indicator_service.get_indicator_list(use_chinese=use_chinese)
        except Exception as e:
            self.logger.error(f"获取指标列表失败: {e}")
            return []

    def get_indicators_by_category(self, use_chinese: bool = False) -> Dict[str, List[str]]:
        """按分类获取指标 - UI适配方法"""
        try:
            return self.indicator_service.get_indicators_by_category(use_chinese=use_chinese)
        except Exception as e:
            self.logger.error(f"获取指标分类失败: {e}")
            return {}

    def get_indicator_categories(self, use_chinese: bool = False) -> List[str]:
        """获取指标分类列表 - UI适配方法"""
        try:
            categories_dict = self.indicator_service.get_indicators_by_category(use_chinese=use_chinese)
            return list(categories_dict.keys())
        except Exception as e:
            self.logger.error(f"获取指标分类列表失败: {e}")
            # 返回默认分类
            if use_chinese:
                return ["趋势类", "震荡类", "成交量类", "其他"]
            else:
                return ["trend", "oscillator", "volume", "other"]

    def get_indicator_category(self, indicator_name: str) -> str:
        """获取指标分类 - UI适配方法"""
        try:
            info = self.indicator_service.get_indicator_info(indicator_name)
            if info and hasattr(info, 'category'):
                return info.category.value if hasattr(info.category, 'value') else str(info.category)
            else:
                # 根据指标名称推断分类
                return self._get_indicator_category(indicator_name)
        except Exception as e:
            self.logger.error(f"获取指标分类失败: {e}")
            return self._get_indicator_category(indicator_name)

    def get_available_indicators(self) -> List[str]:
        """获取可用指标列表 - UI适配方法"""
        try:
            return self.indicator_service.get_indicator_list(use_chinese=False)
        except Exception as e:
            self.logger.error(f"获取可用指标列表失败: {e}")
            return []

    def get_indicator_chinese_name(self, english_name: str) -> Optional[str]:
        """获取指标中文名称 - UI适配方法"""
        try:
            return self.indicator_service.get_chinese_name(english_name)
        except Exception as e:
            self.logger.error(f"获取指标中文名称失败: {e}")
            return None

    def get_indicator_english_name(self, chinese_name: str) -> Optional[str]:
        """获取指标英文名称 - UI适配方法"""
        try:
            return self.indicator_service.get_english_name(chinese_name)
        except Exception as e:
            self.logger.error(f"获取指标英文名称失败: {e}")
            return None

    def calculate_indicator_for_ui(self,
                                   indicator_name: str,
                                   kdata: pd.DataFrame,
                                   **parameters) -> Optional[Dict[str, Any]]:
        """为UI组件计算指标 - 适配方法"""
        try:
            if kdata is None or kdata.empty:
                self.logger.warning("K线数据为空")
                return None

            # 使用新的指标服务计算
            response = self.indicator_service.calculate_indicator(
                indicator_name=indicator_name,
                data=kdata,
                **parameters
            )

            if not response.success:
                self.logger.error(f"指标计算失败: {response.error_message}")
                return None

            # 转换结果格式为UI兼容格式
            return self._format_result_for_ui(indicator_name, response.result)

        except Exception as e:
            self.logger.error(f"UI指标计算失败: {e}")
            return None

    def _format_result_for_ui(self, indicator_name: str, result: Any) -> Dict[str, Any]:
        """将指标结果格式化为UI兼容格式"""
        try:
            formatted_result = {
                "indicator_name": indicator_name,
                "success": True,
                "data": {}
            }

            # 处理不同类型的结果
            if isinstance(result, pd.Series):
                # 单一序列结果
                formatted_result["data"][indicator_name.lower()] = result
                formatted_result["type"] = "series"

            elif isinstance(result, dict):
                # 多序列结果（如MACD、KDJ等）
                for key, value in result.items():
                    if isinstance(value, pd.Series):
                        formatted_result["data"][key.lower()] = value
                    else:
                        formatted_result["data"][key.lower()] = pd.Series(value, dtype=float)
                formatted_result["type"] = "multi_series"

            elif isinstance(result, pd.DataFrame):
                # DataFrame结果
                for column in result.columns:
                    formatted_result["data"][column.lower()] = result[column]
                formatted_result["type"] = "dataframe"

            else:
                # 其他类型转换为Series
                formatted_result["data"][indicator_name.lower()] = pd.Series([result], dtype=float)
                formatted_result["type"] = "series"

            return formatted_result

        except Exception as e:
            self.logger.error(f"结果格式化失败: {e}")
            return {
                "indicator_name": indicator_name,
                "success": False,
                "error": str(e),
                "data": {}
            }

    def batch_calculate_indicators(self,
                                   indicators: List[Dict[str, Any]],
                                   kdata: pd.DataFrame) -> Dict[str, Any]:
        """批量计算指标 - UI批处理方法"""
        results = {}

        try:
            for indicator_config in indicators:
                indicator_name = indicator_config.get('name', '')
                parameters = indicator_config.get('params', {})

                if not indicator_name:
                    continue

                result = self.calculate_indicator_for_ui(
                    indicator_name=indicator_name,
                    kdata=kdata,
                    **parameters
                )

                if result and result.get('success', False):
                    results[indicator_name] = result

        except Exception as e:
            self.logger.error(f"批量计算指标失败: {e}")

        return results

    def get_indicator_display_info(self, indicator_name: str) -> Dict[str, Any]:
        """获取指标显示信息 - UI显示适配方法"""
        try:
            info = self.indicator_service.get_indicator_info(indicator_name)
            if not info:
                # 创建默认信息
                return self._create_default_indicator_info(indicator_name)

            return {
                "name": info.name,
                "chinese_name": info.chinese_name,
                "category": info.category.value,
                "description": info.description,
                "parameters": info.parameters,
                "is_main_chart": self._is_main_chart_indicator(indicator_name),
                "is_sub_chart": self._is_sub_chart_indicator(indicator_name)
            }

        except Exception as e:
            self.logger.error(f"获取指标显示信息失败: {e}")
            return self._create_default_indicator_info(indicator_name)

    def _create_default_indicator_info(self, indicator_name: str) -> Dict[str, Any]:
        """创建默认指标信息"""
        return {
            "name": indicator_name,
            "chinese_name": indicator_name,
            "category": "other",
            "description": f"{indicator_name} 指标",
            "parameters": {},
            "is_main_chart": self._is_main_chart_indicator(indicator_name),
            "is_sub_chart": self._is_sub_chart_indicator(indicator_name)
        }

    def _is_main_chart_indicator(self, indicator_name: str) -> bool:
        """判断是否为主图指标"""
        main_chart_indicators = {
            'MA', 'SMA', 'EMA', 'WMA', 'BOLL', 'BBANDS', 'SAR', 'KAMA'
        }
        return indicator_name.upper() in main_chart_indicators or indicator_name.upper().startswith('MA')

    def _is_sub_chart_indicator(self, indicator_name: str) -> bool:
        """判断是否为副图指标"""
        sub_chart_indicators = {
            'MACD', 'RSI', 'KDJ', 'STOCH', 'CCI', 'WILLR', 'ATR',
            'OBV', 'ROC', 'MOM', 'DMI', 'BIAS', 'PSY'
        }
        return indicator_name.upper() in sub_chart_indicators

    def clear_cache(self):
        """清除指标缓存"""
        try:
            self.indicator_service.clear_cache()
            self.logger.info("UI适配器缓存已清除")
        except Exception as e:
            self.logger.error(f"清除缓存失败: {e}")

    def get_supported_indicators(self) -> List[str]:
        """获取支持的指标列表"""
        try:
            return self.indicator_service.get_supported_indicators()
        except Exception as e:
            self.logger.error(f"获取支持的指标列表失败: {e}")
            return []

    def calculate_indicator_for_chart(self,
                                      indicator_name: str,
                                      kdata: pd.DataFrame,
                                      **parameters) -> Optional[Dict[str, Any]]:
        """为图表计算指标（别名方法）"""
        return self.calculate_indicator_for_ui(indicator_name, kdata, **parameters)

    def get_indicator_list_for_ui(self, use_chinese: bool = False) -> List[Dict[str, Any]]:
        """获取UI格式的指标列表"""
        try:
            indicator_list = []

            # 获取所有指标信息
            for indicator_name in self.indicator_service.get_indicator_list():
                info = self.indicator_service.get_indicator_info(indicator_name)
                if info:
                    indicator_list.append({
                        'name': info.name,
                        'chinese_name': info.chinese_name,
                        'category': info.category.value,
                        'description': info.description
                    })
                else:
                    # 如果没有详细信息，创建基本信息
                    indicator_list.append({
                        'name': indicator_name,
                        'chinese_name': indicator_name,
                        'category': 'other',
                        'description': f"{indicator_name} 指标"
                    })

            return indicator_list

        except Exception as e:
            self.logger.error(f"获取UI指标列表失败: {e}")
            return []

    def _get_indicator_category(self, indicator_name: str) -> str:
        """获取指标分类"""
        try:
            info = self.indicator_service.get_indicator_info(indicator_name)
            return info.category.value if info else "other"
        except Exception:
            return "other"

    def validate_indicator_parameters(self, indicator_name: str, parameters: Dict[str, Any]) -> bool:
        """验证指标参数"""
        try:
            info = self.indicator_service.get_indicator_info(indicator_name)
            if not info:
                return True  # 如果没有参数定义，则认为有效

            # 检查必需参数
            for param_name, default_value in info.parameters.items():
                if param_name not in parameters:
                    # 如果参数缺失但有默认值，则可以接受
                    if default_value is None:
                        self.logger.warning(f"指标 {indicator_name} 缺少必需参数: {param_name}")
                        return False

            return True

        except Exception as e:
            self.logger.error(f"验证指标参数失败: {e}")
            return False


# 全局适配器实例
_indicator_ui_adapter = None


def get_indicator_ui_adapter() -> IndicatorUIAdapter:
    """获取全局UI适配器实例"""
    global _indicator_ui_adapter
    if _indicator_ui_adapter is None:
        _indicator_ui_adapter = IndicatorUIAdapter()
    return _indicator_ui_adapter


# 兼容性函数（向后兼容旧接口）
def calculate_indicator_for_chart(indicator_name: str,
                                  kdata: pd.DataFrame,
                                  **parameters) -> Optional[Dict[str, Any]]:
    """为图表计算指标（兼容性函数）"""
    adapter = get_indicator_ui_adapter()
    return adapter.calculate_indicator_for_chart(indicator_name, kdata, **parameters)


def get_indicator_list_for_ui(use_chinese: bool = False) -> List[str]:
    """获取UI指标列表（兼容性函数）"""
    adapter = get_indicator_ui_adapter()
    return adapter.get_indicator_list(use_chinese=use_chinese)


def get_indicators_by_category_for_ui(use_chinese: bool = False) -> Dict[str, List[str]]:
    """按分类获取指标（兼容性函数）"""
    adapter = get_indicator_ui_adapter()
    return adapter.get_indicators_by_category(use_chinese=use_chinese)


def batch_calculate_for_chart(indicators: List[Dict[str, Any]],
                              kdata: pd.DataFrame) -> Dict[str, Any]:
    """批量计算指标（兼容性函数）"""
    adapter = get_indicator_ui_adapter()
    return adapter.batch_calculate_indicators(indicators, kdata)
