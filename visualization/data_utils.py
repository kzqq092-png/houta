import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger


class DataUtils:
    def __init__(self):
        self.data = None
        # log_manager已迁移到Loguru

        # 使用Loguru日志系统
        try:
            # 纯Loguru架构，移除log_manager依赖
            pass
        except ImportError:
            # 创建简单的日志记录器
            class SimpleLogger:
                def info(self, msg): logger.info(f"[INFO] {msg}")
                def warning(self, msg): logger.info(f"[WARNING] {msg}")
                def error(self, msg): logger.info(f"[ERROR] {msg}")
            # log_manager已迁移到Loguru

    def load_data(self, data):
        """Load and prepare data for analysis"""
        if isinstance(data, pd.DataFrame):
            self.data = data
            logger.info(f"加载DataFrame数据，共{len(data)}行")
        else:
            # Convert to DataFrame if needed
            self.data = pd.DataFrame({
                'datetime': [d.datetime for d in data],
                'open': [d.open for d in data],
                'high': [d.high for d in data],
                'low': [d.low for d in data],
                'close': [d.close for d in data],
                'volume': [d.volume for d in data]
            })
            self.data.set_index('datetime', inplace=True)
            logger.info(f"转换数据为DataFrame格式，共{len(self.data)}行")
        return self.data

    def calculate_indicators(self):
        """计算技术指标 - 使用统一的指标计算模块"""
        if self.data is None:
            logger.warning("数据为空，无法计算指标")
            return None

        try:
            # 使用统一的数据预处理模块
            from utils.data_preprocessing import calculate_basic_indicators

            df = self.data.copy()
            logger.info("开始使用统一模块计算技术指标")

            # 使用统一的指标计算函数
            df_with_indicators = calculate_basic_indicators(df)
            logger.info("技术指标计算完成")
            return df_with_indicators

        except ImportError as e:
            logger.error(f"无法导入统一指标计算模块: {e}")
            return self._calculate_simple_indicators_fallback(self.data.copy())
        except Exception as e:
            logger.error(f"指标计算失败: {e}")
            return self._calculate_simple_indicators_fallback(self.data.copy())

    def _calculate_simple_indicators_fallback(self, df):
        """简单指标计算作为后备方案"""
        logger.info("使用后备方案计算基础指标")

        # 计算Simple Moving Average (SMA)
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()

        # 计算Relative Strength Index (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 计算Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']

        logger.info("后备指标计算完成")
        return df

    def get_signals(self, df=None):
        """Generate trading signals based on indicators"""
        if df is None:
            df = self.calculate_indicators()

        if df is None:
            logger.warning("无法生成交易信号，数据为空")
            return None

        signals = pd.DataFrame(index=df.index)
        signals['signal'] = 0
        signal_count = 0

        # Generate signals based on SMA crossover
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            buy_signals = df['sma_20'] > df['sma_50']
            sell_signals = df['sma_20'] < df['sma_50']
            signals.loc[buy_signals, 'signal'] = 1
            signals.loc[sell_signals, 'signal'] = -1
            signal_count += buy_signals.sum() + sell_signals.sum()

        # Add RSI overbought/oversold signals
        if 'rsi' in df.columns:
            overbought = df['rsi'] > 70
            oversold = df['rsi'] < 30
            signals.loc[overbought, 'signal'] = -1
            signals.loc[oversold, 'signal'] = 1
            signal_count += overbought.sum() + oversold.sum()

        logger.info(f"生成交易信号完成，共{signal_count}个信号")
        return signals
