"""
ai_stock_selector.py
AI智能选股模块

用法示例：
    selector = AIStockSelector(model_type='ml')
    stock_df = ...  # 股票特征DataFrame
    criteria = {'industry': '科技', '市值_min': 100e8}
    selected = selector.select_stocks(stock_df, criteria)
    for code in selected:
        print(code, selector.explain_selection(code))
"""
from typing import List, Dict, Any
import pandas as pd


class AIStockSelector:
    """
    智能选股主类，支持多因子、机器学习、深度学习等多种选股方式。

    参数:
        model_type: 选股模型类型（'ml', 'dl', 'factor'等）
        model_params: 模型参数字典
    """

    def __init__(self, model_type: str = 'ml', model_params: Dict[str, Any] = None):
        """
        初始化AI选股器
        :param model_type: 选股模型类型（'ml', 'dl', 'factor'等）
        :param model_params: 模型参数
        """
        self.model_type = model_type
        self.model_params = model_params or {}
        # TODO: 初始化模型/因子/特征工程等

    def select_stocks(self, stock_data: pd.DataFrame, criteria: Dict[str, Any]) -> List[str]:
        """
        根据输入数据和选股条件，返回推荐股票列表
        :param stock_data: 股票特征数据（DataFrame，需包含code列）
        :param criteria: 选股条件（如行业、市值、因子阈值等）
        :return: 推荐股票代码列表
        """
        df = self._kdata_preprocess(stock_data, context="AI选股")
        if df is None or df.empty:
            return []
        # 行业筛选
        if 'industry' in criteria and criteria['industry']:
            df = df[df['industry'] == criteria['industry']]
        # 市值筛选
        if '市值_min' in criteria:
            if 'market_cap' in df.columns:
                df = df[df['market_cap'] >= criteria['市值_min']]
        if '市值_max' in criteria:
            if 'market_cap' in df.columns:
                df = df[df['market_cap'] <= criteria['市值_max']]
        # PE筛选
        if 'pe_min' in criteria:
            if 'pe' in df.columns:
                df = df[df['pe'] >= criteria['pe_min']]
        if 'pe_max' in criteria:
            if 'pe' in df.columns:
                df = df[df['pe'] <= criteria['pe_max']]
        # PB筛选
        if 'pb_min' in criteria:
            if 'pb' in df.columns:
                df = df[df['pb'] >= criteria['pb_min']]
        if 'pb_max' in criteria:
            if 'pb' in df.columns:
                df = df[df['pb'] <= criteria['pb_max']]
        # ROE筛选
        if 'roe_min' in criteria:
            if 'roe' in df.columns:
                df = df[df['roe'] >= criteria['roe_min']]
        if 'roe_max' in criteria:
            if 'roe' in df.columns:
                df = df[df['roe'] <= criteria['roe_max']]
        # 其他可扩展因子...
        return df['code'].tolist() if 'code' in df.columns else []

    def explain_selection(self, stock_code: str) -> str:
        """
        返回指定股票的AI选股理由/因子解释
        :param stock_code: 股票代码
        :return: 解释说明
        """
        # TODO: 实现可解释性分析
        return "满足多因子筛选条件"

    def _kdata_preprocess(self, df: pd.DataFrame, context="分析") -> pd.DataFrame:
        """DataFrame字段和数值预处理，异常时详细日志，返回修正后DataFrame或空DataFrame"""
        import pandas as pd
        from datetime import datetime

        if not isinstance(df, pd.DataFrame):
            return df

        # 检查datetime是否在索引中或列中
        has_datetime = False
        datetime_in_index = False

        # 检查datetime是否在索引中
        if isinstance(df.index, pd.DatetimeIndex) or (hasattr(df.index, 'name') and df.index.name == 'datetime'):
            has_datetime = True
            datetime_in_index = True
        # 检查datetime是否在列中
        elif 'datetime' in df.columns:
            has_datetime = True
            datetime_in_index = False

        # 如果datetime不存在，尝试从索引推断或创建
        if not has_datetime:
            if isinstance(df.index, pd.DatetimeIndex):
                # 索引是DatetimeIndex但名称不是datetime，复制到列中
                df = df.copy()
                df['datetime'] = df.index
                has_datetime = True
                print(f"[{context}] 从DatetimeIndex推断datetime字段")
            else:
                # 完全没有datetime信息，需要补全
                print(f"[{context}] 缺少datetime字段，自动补全")
                df = df.copy()
                df['datetime'] = pd.date_range(start='2023-01-01', periods=len(df), freq='D')
                has_datetime = True

        # 检查其他必要字段
        required_cols = ['code', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"[{context}] 缺少字段: {missing_cols}，自动补全为默认值")
            df = df.copy()
            for col in missing_cols:
                if col == 'code':
                    df['code'] = ''
                elif col == 'volume':
                    df[col] = 0.0
                elif col in ['open', 'high', 'low', 'close']:
                    # 用收盘价填充其他价格字段
                    if 'close' in df.columns:
                        df[col] = df['close']
                    else:
                        df[col] = 0.0
                else:
                    df[col] = 0.0

        # 检查数值字段异常
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                before = len(df)
                df = df[df[col].notna() & (df[col] >= 0)]
                after = len(df)
                if after < before:
                    print(f"[{context}] 已过滤{before-after}行{col}异常数据")

        # 检查code字段
        if 'code' in df.columns:
            df = df[df['code'].notna() & (df['code'] != '')]

        if df.empty:
            print(f"[{context}] 数据全部无效，返回空")
            return df

        # 修复：如果datetime在索引中，确保在重置索引前将其复制到列中
        if datetime_in_index and 'datetime' not in df.columns:
            df = df.copy()
            df['datetime'] = df.index
            print(f"[{context}] 将索引中的datetime复制到列中")

        # 重置索引，但保留datetime列
        return df.reset_index(drop=True)

# 后续可扩展：模型训练、自动调参、批量选股等
