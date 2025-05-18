"""
选股策略核心类

实现选股策略的筛选逻辑,包括技术指标筛选、基本面筛选、资金流向筛选等
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from hikyuu.interactive import *
from hikyuu.indicator import *
from core.data_manager import DataManager
from core.logger import LogManager, LogLevel
import os
import json
from indicators_algo import calc_ma, calc_macd, calc_rsi, calc_kdj, calc_boll, calc_atr, calc_obv, calc_cci, get_talib_indicator_list, get_talib_category, get_all_indicators_by_category, calc_talib_indicator
import ptvsd


class StockScreener:
    """选股策略核心类"""

    def __init__(self, data_manager: DataManager, log_manager: LogManager):
        """初始化选股策略

        Args:
            data_manager: 数据管理器实例
            log_manager: 日志管理器实例
        """
        self.data_manager = data_manager
        self.log_manager = log_manager

    def screen_stocks(self,
                      strategy_type: str,
                      template: str,
                      technical_params: Dict[str, Any],
                      fundamental_params: Dict[str, Any],
                      capital_params: Dict[str, Any]) -> pd.DataFrame:
        """筛选股票

        Args:
            strategy_type: 策略类型
            template: 策略模板
            technical_params: 技术指标参数
            fundamental_params: 基本面参数
            capital_params: 资金流向参数

        Returns:
            筛选结果DataFrame
        """
        try:
            # 获取股票列表
            stock_list = self.data_manager.get_stock_list()

            # 根据策略类型选择筛选方法
            if strategy_type == "技术指标筛选":
                results = self.screen_by_technical(
                    stock_list, technical_params)
            elif strategy_type == "基本面筛选":
                results = self.screen_by_fundamental(
                    stock_list, fundamental_params)
            elif strategy_type == "资金流向筛选":
                results = self.screen_by_capital(stock_list, capital_params)
            else:  # 综合筛选
                results = self.screen_by_all(stock_list,
                                             technical_params,
                                             fundamental_params,
                                             capital_params)

            # 根据模板进一步筛选
            if template:
                results = self.apply_template(results, template)

            return results

        except Exception as e:
            self.log_manager.log(f"筛选股票失败: {str(e)}", LogLevel.ERROR)
            return pd.DataFrame()

    def screen_by_technical(self, stock_list: List[str], params: Dict[str, Any]) -> pd.DataFrame:
        """技术指标筛选，全部用ta-lib封装，分类与主界面一致，修复可见指标数为0问题"""
        results = []
        talib_list = get_talib_indicator_list()
        category_map = get_all_indicators_by_category()
        visible_count = {cat: len(names)
                         for cat, names in category_map.items() if names}
        for cat, count in visible_count.items():
            self.log_manager.log(f"筛选分类: {cat}，可见指标数: {count}", LogLevel.INFO)
        if not talib_list or not category_map:
            self.log_manager.log(
                "未检测到任何ta-lib指标，请检查ta-lib安装（需C库和Python包都正确）！如需帮助请参考README或联系技术支持。", LogLevel.ERROR)
            print("【错误】未检测到任何ta-lib指标，请检查ta-lib安装（需C库和Python包都正确）！如需帮助请参考README或联系技术支持。")
            return pd.DataFrame()
        for stock in stock_list:
            try:
                kdata = self.data_manager.get_kdata(stock)
                if kdata.empty or len(kdata) < 30:
                    self.log_manager.log(
                        f"股票 {stock} K线数据为空或不足30根，跳过。", LogLevel.WARNING)
                    continue
                # 动态遍历所有ta-lib指标
                indicator_values = {}
                for name in talib_list:
                    try:
                        val = calc_talib_indicator(name, kdata)
                        if isinstance(val, pd.DataFrame):
                            for col in val.columns:
                                indicator_values[f"{name}_{col}".upper(
                                )] = val[col]
                        else:
                            indicator_values[name.upper()] = val
                    except Exception as e:
                        self.log_manager.log(
                            f"股票 {stock} 指标 {name} 计算失败: {str(e)}", LogLevel.WARNING)
                        continue
                # 兼容常见指标名称
                ma_short = indicator_values.get('MA', None) or indicator_values.get(
                    'MA5', None) or indicator_values.get('MA_5', None)
                ma_long = indicator_values.get('EMA', None) or indicator_values.get(
                    'EMA12', None) or indicator_values.get('EMA_12', None)
                # MACD 兼容多种命名
                macd = (indicator_values.get('MACD_1', None) or indicator_values.get('MACD', None) or
                        indicator_values.get('MACD_DIF', None) or indicator_values.get('MACD_DEA', None))
                # RSI 兼容
                rsi = indicator_values.get('RSI', None) or indicator_values.get(
                    'RSI6', None) or indicator_values.get('RSI_6', None)

                def last_val(x):
                    if x is None:
                        return None
                    if isinstance(x, pd.Series):
                        return x.dropna().iloc[-1] if not x.dropna().empty else None
                    if isinstance(x, pd.DataFrame):
                        # 取第一个非空列的最后一个值
                        for col in x.columns:
                            col_data = x[col].dropna()
                            if not col_data.empty:
                                return col_data.iloc[-1]
                        return None
                    if isinstance(x, (list, np.ndarray)):
                        arr = np.array(x)
                        arr = arr[~np.isnan(arr)]
                        return arr[-1] if arr.size > 0 else None
                    return x

                # 增加日志，便于排查
                self.log_manager.log(
                    f"股票 {stock} 指标取值: MA={last_val(ma_short)}, EMA={last_val(ma_long)}, MACD={last_val(macd)}, RSI={last_val(rsi)}", LogLevel.INFO)

                if all(x is not None for x in [ma_short, ma_long, macd, rsi]):
                    try:
                        ma_short_val = last_val(ma_short)
                        ma_long_val = last_val(ma_long)
                        macd_val = last_val(macd)
                        rsi_val = last_val(rsi)
                        if ma_short_val is None or ma_long_val is None or macd_val is None or rsi_val is None:
                            self.log_manager.log(
                                f"股票 {stock} 指标有空值，跳过。", LogLevel.WARNING)
                            continue
                        if ma_short_val > ma_long_val and macd_val > 0 and rsi_val > params.get('rsi_value', 50):
                            info = self.data_manager.get_stock_info(stock)
                            results.append({
                                'code': stock,
                                'name': info['name'],
                                'industry': info['industry'],
                                'price': kdata['close'].iloc[-1],
                                'change': (kdata['close'].iloc[-1] / kdata['close'].iloc[-2] - 1) * 100,
                                'pe': info['pe'],
                                'pb': info['pb'],
                                'roe': info['roe'],
                                'main_force': self.get_main_force(stock),
                                'north_money': self.get_north_money(stock)
                            })
                    except Exception as e:
                        self.log_manager.log(
                            f"股票 {stock} 指标筛选判断异常: {str(e)}", LogLevel.WARNING)
                        continue
                else:
                    self.log_manager.log(
                        f"股票 {stock} 指标缺失，未参与筛选。", LogLevel.WARNING)
            except Exception as e:
                self.log_manager.log(
                    f"处理股票 {stock} 失败: {str(e)}", LogLevel.WARNING)
                continue
        return pd.DataFrame(results)

    def screen_by_fundamental(self,
                              stock_list: List[str],
                              params: Dict[str, Any]) -> pd.DataFrame:
        """基本面筛选

        Args:
            stock_list: 股票列表
            params: 基本面参数

        Returns:
            筛选结果DataFrame
        """
        results = []

        for stock in stock_list:
            try:
                # 获取股票信息
                info = self.data_manager.get_stock_info(stock)
                if not info:
                    continue

                # 检查条件
                if (params['pe_min'] <= info['pe'] <= params['pe_max'] and
                    params['pb_min'] <= info['pb'] <= params['pb_max'] and
                        info['roe'] >= params['roe_min']):
                    # 获取K线数据
                    kdata = self.data_manager.get_kdata(stock)
                    results.append({
                        'code': stock,
                        'name': info['name'],
                        'industry': info['industry'],
                        'price': kdata['close'].iloc[-1],
                        'change': (kdata['close'].iloc[-1] / kdata['close'].iloc[-2] - 1) * 100,
                        'pe': info['pe'],
                        'pb': info['pb'],
                        'roe': info['roe'],
                        'main_force': self.get_main_force(stock),
                        'north_money': self.get_north_money(stock)
                    })

            except Exception as e:
                self.log_manager.log(
                    f"处理股票 {stock} 失败: {str(e)}", LogLevel.WARNING)
                continue

        return pd.DataFrame(results)

    def screen_by_capital(self,
                          stock_list: List[str],
                          params: Dict[str, Any]) -> pd.DataFrame:
        """资金流向筛选

        Args:
            stock_list: 股票列表
            params: 资金流向参数

        Returns:
            筛选结果DataFrame
        """
        results = []

        for stock in stock_list:
            try:
                # 获取资金流向数据
                main_force = self.get_main_force(
                    stock, params['main_force_days'])
                north_money = self.get_north_money(stock, params['north_days'])

                # 检查条件
                if (main_force >= params['main_force_amount'] and
                        north_money >= params['north_amount']):
                    # 获取股票信息
                    info = self.data_manager.get_stock_info(stock)
                    # 获取K线数据
                    kdata = self.data_manager.get_kdata(stock)
                    results.append({
                        'code': stock,
                        'name': info['name'],
                        'industry': info['industry'],
                        'price': kdata['close'].iloc[-1],
                        'change': (kdata['close'].iloc[-1] / kdata['close'].iloc[-2] - 1) * 100,
                        'pe': info['pe'],
                        'pb': info['pb'],
                        'roe': info['roe'],
                        'main_force': main_force,
                        'north_money': north_money
                    })

            except Exception as e:
                self.log_manager.log(
                    f"处理股票 {stock} 失败: {str(e)}", LogLevel.WARNING)
                continue

        return pd.DataFrame(results)

    def screen_by_all(self,
                      stock_list: List[str],
                      technical_params: Dict[str, Any],
                      fundamental_params: Dict[str, Any],
                      capital_params: Dict[str, Any]) -> pd.DataFrame:
        """综合筛选

        Args:
            stock_list: 股票列表
            technical_params: 技术指标参数
            fundamental_params: 基本面参数
            capital_params: 资金流向参数

        Returns:
            筛选结果DataFrame
        """
        # 分别进行筛选
        technical_results = self.screen_by_technical(
            stock_list, technical_params)
        fundamental_results = self.screen_by_fundamental(
            stock_list, fundamental_params)
        capital_results = self.screen_by_capital(stock_list, capital_params)

        # 合并结果
        results = pd.concat(
            [technical_results, fundamental_results, capital_results])
        results = results.drop_duplicates(subset=['code'])

        return results

    def apply_template(self, results: pd.DataFrame, template: str) -> pd.DataFrame:
        """应用策略模板

        Args:
            results: 筛选结果
            template: 策略模板

        Returns:
            应用模板后的结果
        """
        if template == "强势股筛选":
            # 筛选涨幅大于5%的股票
            results = results[results['change'] > 5]
        elif template == "价值投资":
            # 筛选低市盈率、高ROE的股票
            results = results[(results['pe'] < 20) & (results['roe'] > 15)]
        elif template == "成长股筛选":
            # 筛选高ROE、高增长的股票
            results = results[(results['roe'] > 20) & (results['change'] > 0)]
        elif template == "反转策略":
            # 筛选超跌反弹的股票
            results = results[results['change'] < -5]
        elif template == "动量策略":
            # 筛选连续上涨的股票
            results = results[results['change'] > 0]

        return results

    def check_ma_cross(self, ma_short: pd.Series, ma_long: pd.Series) -> bool:
        """检查均线金叉

        Args:
            ma_short: 短期均线
            ma_long: 长期均线

        Returns:
            是否金叉
        """
        if len(ma_short) < 2 or len(ma_long) < 2:
            return False

        return ma_short.iloc[-2] < ma_long.iloc[-2] and ma_short.iloc[-1] > ma_long.iloc[-1]

    def check_macd_signal(self, macd: pd.DataFrame, signal: str) -> bool:
        """检查MACD信号

        Args:
            macd: MACD指标
            signal: 信号类型

        Returns:
            是否符合信号
        """
        if len(macd) < 2:
            return False

        if signal == "金叉":
            return macd['DIF'].iloc[-2] < macd['DEA'].iloc[-2] and macd['DIF'].iloc[-1] > macd['DEA'].iloc[-1]
        elif signal == "死叉":
            return macd['DIF'].iloc[-2] > macd['DEA'].iloc[-2] and macd['DIF'].iloc[-1] < macd['DEA'].iloc[-1]
        elif signal == "多头":
            return macd['DIF'].iloc[-1] > 0 and macd['DEA'].iloc[-1] > 0
        else:  # 空头
            return macd['DIF'].iloc[-1] < 0 and macd['DEA'].iloc[-1] < 0

    def check_rsi_condition(self, rsi: pd.Series, operator: str, value: int) -> bool:
        """检查RSI条件

        Args:
            rsi: RSI指标
            operator: 比较运算符
            value: 比较值

        Returns:
            是否符合条件
        """
        if len(rsi) < 1:
            return False

        if operator == ">":
            return rsi.iloc[-1] > value
        elif operator == "<":
            return rsi.iloc[-1] < value
        elif operator == ">=":
            return rsi.iloc[-1] >= value
        else:  # "<="
            return rsi.iloc[-1] <= value

    def get_main_force(self, stock: str, days: int = 5) -> float:
        """获取主力资金净流入

        Args:
            stock: 股票代码
            days: 天数

        Returns:
            净流入金额(万)
        """
        try:
            # 获取资金流向数据
            capital_flow = self.data_manager.get_capital_flow(stock)
            if capital_flow.empty:
                return 0

            # 计算最近days天的净流入
            return capital_flow['main_force'].tail(days).sum()

        except Exception as e:
            self.log_manager.log(f"获取主力资金失败: {str(e)}", LogLevel.WARNING)
            return 0

    def get_north_money(self, stock: str, days: int = 5) -> float:
        """获取北向资金净流入

        Args:
            stock: 股票代码
            days: 天数

        Returns:
            净流入金额(万)
        """
        try:
            # 获取北向资金数据
            north_money = self.data_manager.get_north_money(stock)
            if north_money.empty:
                return 0

            # 计算最近days天的净流入
            return north_money['amount'].tail(days).sum()

        except Exception as e:
            self.log_manager.log(f"获取北向资金失败: {str(e)}", LogLevel.WARNING)
            return 0

    def save_strategy(self, strategy_type: str, conditions: dict, template_name: str = None):
        """保存选股策略

        Args:
            strategy_type: 策略类型
            conditions: 选股条件
            template_name: 模板名称，如果为None则使用默认名称
        """
        try:
            if template_name is None:
                template_name = f"{strategy_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            template = {
                "strategy_type": strategy_type,
                "conditions": conditions,
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 保存到文件
            template_dir = "templates/stock_screener"
            os.makedirs(template_dir, exist_ok=True)
            template_path = os.path.join(template_dir, f"{template_name}.json")

            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=4)

            self.log_manager.log(f"策略模板已保存: {template_name}")

        except Exception as e:
            self.log_manager.log(f"保存策略模板失败: {str(e)}", LogLevel.ERROR)

    def load_strategy(self, template_name: str) -> tuple:
        """加载选股策略模板

        Args:
            template_name: 模板名称

        Returns:
            (strategy_type, conditions): 策略类型和条件
        """
        try:
            template_path = os.path.join(
                "templates/stock_screener", f"{template_name}.json")
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"模板文件不存在: {template_name}")

            with open(template_path, "r", encoding="utf-8") as f:
                template = json.load(f)

            return template["strategy_type"], template["conditions"]

        except Exception as e:
            self.log_manager.log(f"加载策略模板失败: {str(e)}", LogLevel.ERROR)
            return None, None

    def list_templates(self) -> list:
        """获取所有策略模板列表

        Returns:
            list: 模板名称列表
        """
        try:
            template_dir = "templates/stock_screener"
            if not os.path.exists(template_dir):
                return []

            templates = []
            for filename in os.listdir(template_dir):
                if filename.endswith(".json"):
                    template_name = os.path.splitext(filename)[0]
                    templates.append(template_name)

            return sorted(templates)

        except Exception as e:
            self.log_manager.log(f"获取策略模板列表失败: {str(e)}", LogLevel.ERROR)
            return []

    def delete_template(self, template_name: str):
        """删除策略模板

        Args:
            template_name: 模板名称
        """
        try:
            template_path = os.path.join(
                "templates/stock_screener", f"{template_name}.json")
            if os.path.exists(template_path):
                os.remove(template_path)
                self.log_manager.log(f"策略模板已删除: {template_name}")

        except Exception as e:
            self.log_manager.log(f"删除策略模板失败: {str(e)}", LogLevel.ERROR)

    def get_indicator_categories(self):
        """获取所有指标分类及其指标列表，确保与ta-lib分类一致"""
        from indicators_algo import get_all_indicators_by_category
        return get_all_indicators_by_category()
