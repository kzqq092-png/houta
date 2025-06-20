"""
advanced_analysis.py
高级分析模块

用法示例：
    analyzer = AdvancedAnalyzer()
    result = analyzer.comprehensive_analysis('sh000001')
    print(result['technical_analysis'])
    print(result['risk_analysis'])
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 尝试导入hikyuu相关模块
try:
    from hikyuu import *
    from hikyuu.indicator import *
    HIKYUU_AVAILABLE = True
except ImportError:
    HIKYUU_AVAILABLE = False
    print("Warning: hikyuu not available, some features may be limited")


class AdvancedAnalyzer:
    """
    高级分析器，提供技术分析、风险分析、波动率分析等功能
    """

    def __init__(self):
        """初始化分析器"""
        self.indicators = {}
        self.analysis_cache = {}

    def comprehensive_analysis(self, stock_code: str,
                               start_date: str = None,
                               end_date: str = None) -> Dict[str, Any]:
        """
        综合分析
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 综合分析结果
        """
        try:
            # 获取数据
            data = self._get_stock_data(stock_code, start_date, end_date)
            if data is None or data.empty:
                return {"error": "无法获取股票数据"}

            # 执行各种分析
            result = {
                'stock_code': stock_code,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_period': {
                    'start': data.index[0].strftime('%Y-%m-%d') if not data.empty else None,
                    'end': data.index[-1].strftime('%Y-%m-%d') if not data.empty else None,
                    'total_days': len(data)
                },
                'technical_analysis': self.technical_analysis(data),
                'risk_analysis': self.risk_analysis(data),
                'volatility_analysis': self.volatility_analysis(data),
                'trend_analysis': self.trend_analysis(data),
                'support_resistance': self.support_resistance_analysis(data),
                'pattern_recognition': self.pattern_recognition(data),
                'momentum_analysis': self.momentum_analysis(data)
            }

            return result

        except Exception as e:
            return {"error": f"分析过程出错: {str(e)}"}

    def technical_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        技术分析
        :param data: 股票数据
        :return: 技术分析结果
        """
        try:
            result = {}

            # 基础价格信息
            current_price = data['close'].iloc[-1]
            prev_price = data['close'].iloc[-2] if len(data) > 1 else current_price
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0

            result['price_info'] = {
                'current_price': round(current_price, 2),
                'price_change': round(price_change, 2),
                'price_change_pct': round(price_change_pct, 2)
            }

            # 移动平均线
            ma_periods = [5, 10, 20, 50, 200]
            ma_values = {}
            for period in ma_periods:
                if len(data) >= period:
                    ma_values[f'MA{period}'] = round(data['close'].rolling(period).mean().iloc[-1], 2)

            result['moving_averages'] = ma_values

            # MACD
            if len(data) >= 26:
                exp1 = data['close'].ewm(span=12).mean()
                exp2 = data['close'].ewm(span=26).mean()
                macd_line = exp1 - exp2
                signal_line = macd_line.ewm(span=9).mean()
                histogram = macd_line - signal_line

                result['macd'] = {
                    'macd_line': round(macd_line.iloc[-1], 4),
                    'signal_line': round(signal_line.iloc[-1], 4),
                    'histogram': round(histogram.iloc[-1], 4),
                    'signal': 'BUY' if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0 else
                    'SELL' if histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0 else 'HOLD'
                }

            # RSI
            if len(data) >= 14:
                delta = data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))

                result['rsi'] = {
                    'value': round(rsi.iloc[-1], 2),
                    'signal': 'OVERSOLD' if rsi.iloc[-1] < 30 else
                    'OVERBOUGHT' if rsi.iloc[-1] > 70 else 'NEUTRAL'
                }

            # 布林带
            if len(data) >= 20:
                ma20 = data['close'].rolling(20).mean()
                std20 = data['close'].rolling(20).std()
                upper_band = ma20 + (std20 * 2)
                lower_band = ma20 - (std20 * 2)

                result['bollinger_bands'] = {
                    'upper_band': round(upper_band.iloc[-1], 2),
                    'middle_band': round(ma20.iloc[-1], 2),
                    'lower_band': round(lower_band.iloc[-1], 2),
                    'position': 'UPPER' if current_price > upper_band.iloc[-1] else
                    'LOWER' if current_price < lower_band.iloc[-1] else 'MIDDLE'
                }

            return result

        except Exception as e:
            return {"error": f"技术分析失败: {str(e)}"}

    def risk_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        风险分析
        :param data: 股票数据
        :return: 风险分析结果
        """
        try:
            result = {}

            # 计算收益率
            returns = data['close'].pct_change().dropna()

            if len(returns) > 0:
                # 基础风险指标
                result['volatility'] = {
                    'daily_volatility': round(returns.std(), 4),
                    'annual_volatility': round(returns.std() * np.sqrt(252), 4)
                }

                # VaR计算
                confidence_levels = [0.95, 0.99]
                var_results = {}
                for conf in confidence_levels:
                    var_value = np.percentile(returns, (1 - conf) * 100)
                    var_results[f'VaR_{int(conf*100)}%'] = round(var_value, 4)

                result['value_at_risk'] = var_results

                # 最大回撤
                cumulative_returns = (1 + returns).cumprod()
                rolling_max = cumulative_returns.expanding().max()
                drawdown = (cumulative_returns - rolling_max) / rolling_max
                max_drawdown = drawdown.min()

                result['drawdown'] = {
                    'max_drawdown': round(max_drawdown, 4),
                    'current_drawdown': round(drawdown.iloc[-1], 4)
                }

                # 夏普比率（假设无风险利率为3%）
                risk_free_rate = 0.03 / 252  # 日无风险利率
                excess_returns = returns - risk_free_rate
                if returns.std() != 0:
                    sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252)
                    result['sharpe_ratio'] = round(sharpe_ratio, 4)

            return result

        except Exception as e:
            return {"error": f"风险分析失败: {str(e)}"}

    def volatility_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        波动率分析
        :param data: 股票数据
        :return: 波动率分析结果
        """
        try:
            result = {}

            # 计算不同周期的波动率
            returns = data['close'].pct_change().dropna()

            if len(returns) > 0:
                periods = [5, 10, 20, 60]
                volatility_by_period = {}

                for period in periods:
                    if len(returns) >= period:
                        rolling_vol = returns.rolling(period).std()
                        volatility_by_period[f'{period}d'] = {
                            'current': round(rolling_vol.iloc[-1], 4),
                            'mean': round(rolling_vol.mean(), 4),
                            'percentile_90': round(rolling_vol.quantile(0.9), 4)
                        }

                result['rolling_volatility'] = volatility_by_period

                # 波动率聚类检测
                vol_threshold = returns.std() * 2
                high_vol_periods = returns[abs(returns) > vol_threshold]
                result['volatility_clustering'] = {
                    'high_vol_days': len(high_vol_periods),
                    'high_vol_ratio': round(len(high_vol_periods) / len(returns), 4)
                }

            return result

        except Exception as e:
            return {"error": f"波动率分析失败: {str(e)}"}

    def trend_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        趋势分析
        :param data: 股票数据
        :return: 趋势分析结果
        """
        try:
            result = {}

            # 价格趋势
            periods = [5, 10, 20, 50]
            trend_analysis = {}

            for period in periods:
                if len(data) >= period:
                    start_price = data['close'].iloc[-period]
                    end_price = data['close'].iloc[-1]
                    trend_return = (end_price - start_price) / start_price

                    trend_analysis[f'{period}d'] = {
                        'return': round(trend_return, 4),
                        'direction': 'UP' if trend_return > 0.02 else 'DOWN' if trend_return < -0.02 else 'SIDEWAYS'
                    }

            result['price_trends'] = trend_analysis

            # 成交量趋势
            if 'volume' in data.columns:
                volume_ma = data['volume'].rolling(20).mean()
                current_volume = data['volume'].iloc[-1]
                avg_volume = volume_ma.iloc[-1] if not volume_ma.empty else current_volume

                result['volume_trend'] = {
                    'current_vs_average': round(current_volume / avg_volume, 2) if avg_volume != 0 else 1,
                    'trend': 'HIGH' if current_volume > avg_volume * 1.5 else
                    'LOW' if current_volume < avg_volume * 0.5 else 'NORMAL'
                }

            return result

        except Exception as e:
            return {"error": f"趋势分析失败: {str(e)}"}

    def support_resistance_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        支撑阻力分析
        :param data: 股票数据
        :return: 支撑阻力分析结果
        """
        try:
            result = {}

            # 计算支撑阻力位
            highs = data['high'].values
            lows = data['low'].values
            closes = data['close'].values

            # 简单的支撑阻力计算
            recent_high = np.max(highs[-20:]) if len(highs) >= 20 else np.max(highs)
            recent_low = np.min(lows[-20:]) if len(lows) >= 20 else np.min(lows)
            current_price = closes[-1]

            # 计算斐波那契回撤位
            diff = recent_high - recent_low
            fib_levels = {
                '23.6%': recent_high - diff * 0.236,
                '38.2%': recent_high - diff * 0.382,
                '50%': recent_high - diff * 0.5,
                '61.8%': recent_high - diff * 0.618,
                '78.6%': recent_high - diff * 0.786
            }

            result['key_levels'] = {
                'recent_high': round(recent_high, 2),
                'recent_low': round(recent_low, 2),
                'fibonacci_retracements': {k: round(v, 2) for k, v in fib_levels.items()}
            }

            # 判断当前价格位置
            price_position = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
            result['price_position'] = {
                'percentage': round(price_position * 100, 1),
                'level': 'HIGH' if price_position > 0.8 else 'LOW' if price_position < 0.2 else 'MIDDLE'
            }

            return result

        except Exception as e:
            return {"error": f"支撑阻力分析失败: {str(e)}"}

    def pattern_recognition(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        形态识别
        :param data: 股票数据
        :return: 形态识别结果
        """
        try:
            result = {}

            if len(data) < 10:
                return {"error": "数据不足，无法进行形态识别"}

            # 简单的形态识别
            patterns = []

            # 检测双底/双顶
            lows = data['low'].values[-20:]
            highs = data['high'].values[-20:]

            if len(lows) >= 10:
                # 寻找低点
                local_mins = []
                for i in range(1, len(lows) - 1):
                    if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                        local_mins.append((i, lows[i]))

                if len(local_mins) >= 2:
                    # 检查是否为双底
                    last_two_mins = local_mins[-2:]
                    if abs(last_two_mins[0][1] - last_two_mins[1][1]) / last_two_mins[0][1] < 0.02:
                        patterns.append("双底形态")

            # 检测突破
            if len(data) >= 20:
                ma20 = data['close'].rolling(20).mean()
                current_price = data['close'].iloc[-1]
                ma20_current = ma20.iloc[-1]

                if current_price > ma20_current * 1.02:
                    patterns.append("向上突破20日均线")
                elif current_price < ma20_current * 0.98:
                    patterns.append("向下跌破20日均线")

            result['detected_patterns'] = patterns

            return result

        except Exception as e:
            return {"error": f"形态识别失败: {str(e)}"}

    def momentum_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        动量分析
        :param data: 股票数据
        :return: 动量分析结果
        """
        try:
            result = {}

            # 价格动量
            periods = [1, 5, 10, 20]
            momentum = {}

            for period in periods:
                if len(data) > period:
                    current_price = data['close'].iloc[-1]
                    past_price = data['close'].iloc[-period-1]
                    mom_value = (current_price - past_price) / past_price

                    momentum[f'{period}d'] = round(mom_value, 4)

            result['price_momentum'] = momentum

            # 成交量动量
            if 'volume' in data.columns and len(data) >= 10:
                volume_momentum = {}
                for period in [5, 10]:
                    if len(data) > period:
                        current_vol = data['volume'].iloc[-period:].mean()
                        past_vol = data['volume'].iloc[-period*2:-period].mean()
                        vol_mom = (current_vol - past_vol) / past_vol if past_vol != 0 else 0

                        volume_momentum[f'{period}d'] = round(vol_mom, 4)

                result['volume_momentum'] = volume_momentum

            return result

        except Exception as e:
            return {"error": f"动量分析失败: {str(e)}"}

    def _get_stock_data(self, stock_code: str,
                        start_date: str = None,
                        end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取股票数据
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 股票数据DataFrame
        """
        try:
            # 这里需要根据实际的数据源来实现
            # 示例实现：
            if HIKYUU_AVAILABLE:
                try:
                    stock = Stock(stock_code)
                    query = Query(-250)  # 默认获取最近250个交易日
                    if start_date and end_date:
                        query = Query(Datetime(start_date), Datetime(end_date))

                    kdata = stock.get_kdata(query)
                    df = kdata.to_df()
                    return df
                except Exception as e:
                    print(f"使用hikyuu获取数据失败: {str(e)}")

            # 如果hikyuu不可用，返回模拟数据
            print("使用模拟数据进行分析")
            dates = pd.date_range('2023-01-01', periods=100, freq='D')
            np.random.seed(42)
            prices = 100 + np.random.randn(100).cumsum()

            data = pd.DataFrame({
                'open': prices + np.random.randn(100) * 0.5,
                'high': prices + np.abs(np.random.randn(100)) * 0.8,
                'low': prices - np.abs(np.random.randn(100)) * 0.8,
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, 100)
            }, index=dates)

            return data

        except Exception as e:
            print(f"获取股票数据失败: {str(e)}")
            return None


# 使用示例
if __name__ == "__main__":
    analyzer = AdvancedAnalyzer()

    # 执行综合分析
    result = analyzer.comprehensive_analysis('sh000001')

    # 打印结果
    if 'error' not in result:
        print(f"分析股票: {result['stock_code']}")
        print(f"数据周期: {result['data_period']['start']} 到 {result['data_period']['end']}")
        print(f"当前价格: {result['technical_analysis']['price_info']['current_price']}")
        print(f"价格变化: {result['technical_analysis']['price_info']['price_change_pct']:.2f}%")

        if 'rsi' in result['technical_analysis']:
            print(f"RSI: {result['technical_analysis']['rsi']['value']} ({result['technical_analysis']['rsi']['signal']})")

        if 'max_drawdown' in result['risk_analysis']:
            print(f"最大回撤: {result['risk_analysis']['drawdown']['max_drawdown']:.2%}")
    else:
        print(f"分析失败: {result['error']}")
