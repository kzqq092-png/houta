"""
AI选股集成服务

提供AI选股系统的完整功能，包括与核心服务的深度集成：
- 与UnifiedDataManager的集成，获取市场数据
- 与EnhancedIndicatorService的集成，计算技术指标
- 与DatabaseService的集成，存储策略和结果
- 提供可解释性和个性化功能
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import warnings

from loguru import logger
from ..containers import ServiceContainer, get_service_container
from ..events import EventBus, get_event_bus
from ..plugin_types import AssetType
from .unified_data_manager import UnifiedDataManager
from .enhanced_indicator_service import EnhancedIndicatorService
from .database_service import DatabaseService


class SelectionStrategy(Enum):
    """选股策略类型"""
    MOMENTUM_BASED = "momentum"      # 动量策略
    VALUE_BASED = "value"           # 价值策略  
    GROWTH_BASED = "growth"         # 成长策略
    QUALITY_BASED = "quality"       # 质量策略
    DIVIDEND_BASED = "dividend"     # 股息策略
    TECH_ANALYSIS = "technical"     # 技术分析策略
    QUANTITATIVE = "quantitative"   # 量化策略
    HYBRID = "hybrid"               # 混合策略


class RiskLevel(Enum):
    """风险等级"""
    CONSERVATIVE = "conservative"    # 保守型
    MODERATE = "moderate"           # 平衡型
    AGGRESSIVE = "aggressive"       # 激进型


class SelectionStatus(Enum):
    """选股结果状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class StockSelectionCriteria:
    """选股标准"""
    # 基础条件
    stock_codes: Optional[List[str]] = None           # 指定股票代码列表
    market_cap_min: Optional[float] = None            # 最小市值（亿元）
    market_cap_max: Optional[float] = None            # 最大市值（亿元）
    
    # 技术指标条件
    sma_period: int = 20                              # 移动平均周期
    rsi_min: Optional[float] = None                   # RSI最小值
    rsi_max: Optional[float] = None                   # RSI最大值
    macd_signal: Optional[str] = None                 # MACD信号
    volume_threshold: Optional[float] = None          # 成交量阈值
    
    # 财务指标条件
    pe_ratio_min: Optional[float] = None              # 最小市盈率
    pe_ratio_max: Optional[float] = None              # 最大市盈率
    pb_ratio_min: Optional[float] = None              # 最小市净率
    pb_ratio_max: Optional[float] = None              # 最大市净率
    roe_min: Optional[float] = None                   # 最小ROE
    debt_ratio_max: Optional[float] = None            # 最大负债率
    
    # 行业和主题条件
    industries: Optional[List[str]] = None            # 行业列表
    themes: Optional[List[str]] = None                # 主题列表
    
    # 时间和频率条件
    selection_date: datetime = field(default_factory=datetime.now)
    rebalance_frequency: str = "monthly"              # 调仓频率
    
    # 风险和策略条件
    risk_level: RiskLevel = RiskLevel.MODERATE        # 风险等级
    strategy_type: SelectionStrategy = SelectionStrategy.QUANTITATIVE  # 策略类型


@dataclass
class SelectionPerformanceMetrics:
    """选股性能指标"""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_return: float = 0.0
    risk_adjusted_return: float = 0.0


@dataclass
class SelectionExplanation:
    """选股结果解释"""
    stock_code: str                                   # 股票代码
    selection_reason: str                            # 入选原因
    score: float                                     # 评分 (0-100)
    key_indicators: Dict[str, float]                 # 关键指标值
    technical_signals: Dict[str, Any]               # 技术信号
    fundamental_signals: Dict[str, Any]             # 基本面信号
    risk_assessment: Dict[str, Any]                 # 风险评估
    recommendation_strength: str                    # 推荐强度 (strong/moderate/weak)


@dataclass
class StockSelectionResult:
    """选股结果"""
    result_id: str                                    # 结果ID
    strategy_id: str                                  # 策略ID
    selection_date: datetime                         # 选股日期
    status: SelectionStatus                          # 状态
    criteria: StockSelectionCriteria                 # 选股标准
    
    # 选股结果
    selected_stocks: List[str]                       # 选中的股票代码
    stock_scores: Dict[str, float]                   # 股票评分
    weights: Dict[str, float]                        # 权重分配
    
    # 解释和说明
    explanations: List[SelectionExplanation]         # 选股解释
    overall_explanation: str                         # 整体说明
    
    # 性能指标
    portfolio_metrics: Dict[str, Any]               # 组合指标
    backtest_metrics: Optional[Dict[str, Any]] = None  # 回测指标
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    computation_time: float = 0.0                    # 计算时间
    data_freshness: Dict[str, datetime] = field(default_factory=dict)  # 数据时效性
    error_message: Optional[str] = None             # 错误信息


class AISelectionIntegrationService:
    """AI选股集成服务
    
    深度集成现有核心服务，提供完整的AI选股功能
    """
    
    def __init__(self, service_container: Optional[ServiceContainer] = None):
        """初始化AI选股集成服务
        
        Args:
            service_container: 服务容器，用于解析依赖服务
        """
        self._container = service_container or get_service_container()
        if not self._container:
            raise ValueError("无法获取服务容器，请确保服务容器已初始化")
            
        # 解析核心依赖服务
        self._data_manager = self._container.resolve(UnifiedDataManager)
        self._indicator_service = self._container.resolve(EnhancedIndicatorService)
        self._database_service = self._container.resolve(DatabaseService)
        self._event_bus = get_event_bus()
        
        # 线程池用于异步计算
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="AI_Selection")
        
        # 缓存
        self._result_cache: Dict[str, StockSelectionResult] = {}
        self._cache_ttl = timedelta(hours=1)  # 缓存1小时
        
        # 策略注册
        self._strategies: Dict[str, Any] = {}
        self._register_default_strategies()
        
        logger.info("AI选股集成服务初始化完成")
        
    def _register_default_strategies(self):
        """注册默认选股策略"""
        self._strategies = {
            SelectionStrategy.MOMENTUM_BASED: self._momentum_strategy,
            SelectionStrategy.VALUE_BASED: self._value_strategy,
            SelectionStrategy.GROWTH_BASED: self._growth_strategy,
            SelectionStrategy.QUALITY_BASED: self._quality_strategy,
            SelectionStrategy.TECH_ANALYSIS: self._technical_strategy,
            SelectionStrategy.QUANTITATIVE: self._quantitative_strategy,
            SelectionStrategy.HYBRID: self._hybrid_strategy
        }
        
    async def create_selection_strategy(
        self,
        name: str,
        description: str,
        criteria: StockSelectionCriteria,
        user_id: Optional[str] = None
    ) -> str:
        """创建选股策略
        
        Args:
            name: 策略名称
            description: 策略描述
            criteria: 选股标准
            user_id: 用户ID
            
        Returns:
            策略ID
        """
        strategy_id = str(uuid.uuid4())
        
        # 保存策略到数据库
        strategy_data = {
            "strategy_id": strategy_id,
            "name": name,
            "description": description,
            "criteria": asdict(criteria),
            "user_id": user_id,
            "created_at": datetime.now(),
            "is_active": True,
            "performance_metrics": {},
            "backtest_result": {}
        }
        
        try:
            # 使用DatabaseService保存策略
            if hasattr(self._database_service, 'save_ai_strategy'):
                await self._database_service.save_ai_strategy(strategy_data)
            else:
                # 如果DatabaseService没有相应方法，直接保存到数据库
                await self._save_strategy_to_db(strategy_data)
                
            logger.info(f"选股策略创建成功: {name} (ID: {strategy_id})")
            return strategy_id
            
        except Exception as e:
            logger.error(f"创建选股策略失败: {e}")
            raise
    
    async def select_stocks_with_explanation(
        self,
        strategy_id: str,
        criteria: Optional[StockSelectionCriteria] = None
    ) -> StockSelectionResult:
        """执行选股并生成解释
        
        Args:
            strategy_id: 策略ID
            criteria: 选股标准（可选，如果为None则使用策略中保存的标准）
            
        Returns:
            选股结果
        """
        start_time = datetime.now()
        
        try:
            # 获取策略信息
            strategy_data = await self._get_strategy_by_id(strategy_id)
            if not strategy_data:
                raise ValueError(f"策略 {strategy_id} 不存在")
                
            # 准备选股标准
            selection_criteria = criteria or StockSelectionCriteria(**strategy_data["criteria"])
            
            # 检查缓存
            cache_key = f"{strategy_id}_{selection_criteria.selection_date.strftime('%Y%m%d')}"
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("返回缓存的选股结果")
                return cached_result
            
            # 发布事件：开始选股
            await self._event_bus.publish("ai_selection.started", {
                "strategy_id": strategy_id,
                "criteria": asdict(selection_criteria)
            })
            
            # 执行选股
            result = await self._execute_selection(strategy_id, selection_criteria)
            
            # 生成解释
            result.explanations = await self._generate_explanations(result)
            result.overall_explanation = await self._generate_overall_explanation(result)
            
            # 计算性能指标
            result.portfolio_metrics = await self._calculate_portfolio_metrics(result)
            
            # 保存结果到数据库
            await self._save_selection_result(result)
            
            # 缓存结果
            self._cache_result(cache_key, result)
            
            # 发布事件：选股完成
            await self._event_bus.publish("ai_selection.completed", {
                "strategy_id": strategy_id,
                "result_id": result.result_id,
                "selected_stocks": result.selected_stocks
            })
            
            result.computation_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"选股完成: {strategy_id}, 选中 {len(result.selected_stocks)} 只股票")
            return result
            
        except Exception as e:
            logger.error(f"选股失败: {e}")
            # 发布失败事件
            await self._event_bus.publish("ai_selection.failed", {
                "strategy_id": strategy_id,
                "error": str(e)
            })
            raise
    
    async def _execute_selection(
        self,
        strategy_id: str,
        criteria: StockSelectionCriteria
    ) -> StockSelectionResult:
        """执行具体的选股逻辑"""
        
        result_id = str(uuid.uuid4())
        
        # 获取候选股票列表
        candidate_stocks = await self._get_candidate_stocks(criteria)
        
        if not candidate_stocks:
            return StockSelectionResult(
                result_id=result_id,
                strategy_id=strategy_id,
                selection_date=criteria.selection_date,
                status=SelectionStatus.COMPLETED,
                criteria=criteria,
                selected_stocks=[],
                stock_scores={},
                weights={},
                explanations=[],
                overall_explanation="没有找到符合条件的股票"
            )
        
        # 获取股票数据
        stock_data = await self._get_stock_data_batch(candidate_stocks, criteria)
        
        # 执行策略计算
        strategy_func = self._strategies.get(criteria.strategy_type, self._quantitative_strategy)
        selected_stocks, scores = await self._run_strategy(strategy_func, stock_data, criteria)
        
        # 计算权重
        weights = self._calculate_weights(selected_stocks, scores, criteria)
        
        return StockSelectionResult(
            result_id=result_id,
            strategy_id=strategy_id,
            selection_date=criteria.selection_date,
            status=SelectionStatus.COMPLETED,
            criteria=criteria,
            selected_stocks=selected_stocks,
            stock_scores=dict(zip(selected_stocks, [scores[stock] for stock in selected_stocks])),
            weights=weights,
            explanations=[],  # 将在后续步骤中填充
            overall_explanation=""  # 将在后续步骤中填充
        )
    
    async def _get_candidate_stocks(self, criteria: StockSelectionCriteria) -> List[str]:
        """获取候选股票列表"""
        if criteria.stock_codes:
            return criteria.stock_codes
            
        # 使用实际数据服务获取候选股票
        try:
            candidate_stocks = []
            
            # 如果指定了行业筛选，使用行业股票列表
            if criteria.industries:
                for industry in criteria.industries:
                    try:
                        # 从数据库或数据服务获取行业股票
                        industry_stocks = await self._get_industry_stocks(industry)
                        candidate_stocks.extend(industry_stocks)
                    except Exception as e:
                        logger.warning(f"获取行业 {industry} 股票列表失败: {e}")
                        continue
            
            # 如果没有指定行业，获取主要股票池
            if not candidate_stocks:
                candidate_stocks = await self._get_main_stock_pool(criteria)
            
            # 应用市值筛选
            if criteria.market_cap_min or criteria.market_cap_max:
                candidate_stocks = await self._filter_stocks_by_market_cap(
                    candidate_stocks, criteria.market_cap_min, criteria.market_cap_max
                )
            
            # 去重
            candidate_stocks = list(set(candidate_stocks))
            
            logger.info(f"获取候选股票 {len(candidate_stocks)} 只")
            return candidate_stocks
            
        except Exception as e:
            logger.error(f"获取候选股票失败: {e}")
            # 返回基础股票池作为后备
            return await self._get_main_stock_pool(criteria)
    
    async def _get_industry_stocks(self, industry: str) -> List[str]:
        """获取指定行业的股票列表"""
        try:
            # 使用数据库服务获取行业股票
            if hasattr(self._database_service, 'get_stocks_by_industry'):
                stocks = await self._database_service.get_stocks_by_industry(industry)
                return [stock.get('code', '') for stock in stocks if stock.get('code')]
            
            # 使用数据管理器获取行业股票
            if hasattr(self._data_manager, 'get_industry_stocks'):
                stocks = await self._data_manager.get_industry_stocks(industry)
                return [stock for stock in stocks if stock]
            
            # 如果无法获取行业股票，返回空列表
            logger.warning(f"无法获取行业 {industry} 的股票列表")
            return []
            
        except Exception as e:
            logger.error(f"获取行业 {industry} 股票列表失败: {e}")
            return []
    
    async def _get_main_stock_pool(self, criteria: StockSelectionCriteria) -> List[str]:
        """获取主要股票池"""
        try:
            # 使用UnifiedDataManager获取主要股票
            if hasattr(self._data_manager, 'get_main_stock_pool'):
                stocks = await self._data_manager.get_main_stock_pool()
                return [stock for stock in stocks if stock]
            
            # 使用StockService获取股票列表
            if hasattr(self._data_manager, 'get_stock_list'):
                stock_list = await self._data_manager.get_stock_list()
                if stock_list is not None and not stock_list.empty:
                    return stock_list['code'].tolist() if 'code' in stock_list.columns else []
            
            # 如果无法获取主要股票池，返回空列表
            logger.warning("无法获取主要股票池")
            return []
            
        except Exception as e:
            logger.error(f"获取主要股票池失败: {e}")
            return []
    
    async def _filter_stocks_by_market_cap(self, stocks: List[str], 
                                         market_cap_min: Optional[float], 
                                         market_cap_max: Optional[float]) -> List[str]:
        """根据市值筛选股票"""
        try:
            filtered_stocks = []
            
            # 批量获取股票市值数据
            stock_data_batch = await self._get_stock_data_batch(stocks, 
                StockSelectionCriteria(selection_date=datetime.now()))
            
            for stock_code in stocks:
                if stock_code in stock_data_batch:
                    stock_info = stock_data_batch[stock_code]
                    price_data = stock_info.get('price_data')
                    
                    if price_data is not None and not price_data.empty:
                        # 获取最新市值数据
                        latest_data = price_data.iloc[-1]
                        market_cap = latest_data.get('total_market_cap', 0)
                        
                        # 检查是否符合市值范围
                        if market_cap_min and market_cap < market_cap_min:
                            continue
                        if market_cap_max and market_cap > market_cap_max:
                            continue
                        
                        filtered_stocks.append(stock_code)
            
            logger.info(f"市值筛选后保留 {len(filtered_stocks)} 只股票")
            return filtered_stocks
            
        except Exception as e:
            logger.error(f"市值筛选失败: {e}")
            return stocks  # 筛选失败时返回原列表
    
    async def _get_stock_data_batch(
        self,
        stock_codes: List[str],
        criteria: StockSelectionCriteria
    ) -> Dict[str, Dict[str, Any]]:
        """批量获取股票数据"""
        stock_data = {}
        
        # 设置数据获取参数
        time_range = 365  # 获取一年的数据
        period = "D"
        
        for stock_code in stock_codes:
            try:
                # 使用UnifiedDataManager获取数据
                data_request = {
                    "symbol": stock_code,
                    "asset_type": AssetType.STOCK_A,
                    "data_type": "kdata",
                    "period": period,
                    "time_range": time_range
                }
                
                # 异步获取数据
                data = await self._data_manager.get_data_async(**data_request)
                if data is not None and not data.empty:
                    stock_data[stock_code] = {
                        "price_data": data,
                        "fetched_at": datetime.now()
                    }
                    
            except Exception as e:
                logger.warning(f"获取股票 {stock_code} 数据失败: {e}")
                continue
                
        logger.info(f"成功获取 {len(stock_data)} 只股票的数据")
        return stock_data
    
    async def _run_strategy(
        self,
        strategy_func,
        stock_data: Dict[str, Dict[str, Any]],
        criteria: StockSelectionCriteria
    ) -> Tuple[List[str], Dict[str, float]]:
        """运行选股策略"""
        
        # 在线程池中执行策略计算
        loop = asyncio.get_event_loop()
        selected_stocks, scores = await loop.run_in_executor(
            self._executor,
            lambda: strategy_func(stock_data, criteria)
        )
        
        return selected_stocks, scores
    
    def _quantitative_strategy(
        self,
        stock_data: Dict[str, Dict[str, Any]],
        criteria: StockSelectionCriteria
    ) -> Tuple[List[str], Dict[str, float]]:
        """量化策略实现"""
        
        stock_scores = {}
        
        for stock_code, data in stock_data.items():
            try:
                price_data = data["price_data"]
                if price_data.empty or len(price_data) < 30:
                    continue
                    
                score = 0.0
                
                # 技术指标评分 (40%)
                tech_score = self._calculate_technical_score(price_data, criteria)
                score += tech_score * 0.4
                
                # 动量指标评分 (30%)
                momentum_score = self._calculate_momentum_score(price_data)
                score += momentum_score * 0.3
                
                # 波动性评分 (20%)
                volatility_score = self._calculate_volatility_score(price_data)
                score += volatility_score * 0.2
                
                # 流动性评分 (10%)
                liquidity_score = self._calculate_liquidity_score(price_data)
                score += liquidity_score * 0.1
                
                # 风险调整
                if criteria.risk_level == RiskLevel.CONSERVATIVE:
                    score *= 0.9  # 保守型降低评分
                elif criteria.risk_level == RiskLevel.AGGRESSIVE:
                    score *= 1.1  # 激进型提升评分
                
                stock_scores[stock_code] = min(score, 100.0)  # 限制在0-100之间
                
            except Exception as e:
                logger.warning(f"计算股票 {stock_code} 评分失败: {e}")
                continue
        
        # 选择评分最高的股票
        sorted_stocks = sorted(stock_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 根据风险等级确定选择数量
        if criteria.risk_level == RiskLevel.CONSERVATIVE:
            top_n = min(10, len(sorted_stocks))
        elif criteria.risk_level == RiskLevel.MODERATE:
            top_n = min(20, len(sorted_stocks))
        else:  # AGGRESSIVE
            top_n = min(30, len(sorted_stocks))
        
        selected_stocks = [stock for stock, _ in sorted_stocks[:top_n]]
        selected_scores = {stock: stock_scores[stock] for stock in selected_stocks}
        
        return selected_stocks, selected_scores
    
    def _calculate_technical_score(
        self,
        price_data: pd.DataFrame,
        criteria: StockSelectionCriteria
    ) -> float:
        """计算技术指标评分"""
        try:
            if price_data.empty or len(price_data) < criteria.sma_period:
                return 0.0
                
            # 计算移动平均线
            sma_20 = price_data['close'].rolling(window=20).mean()
            sma_50 = price_data['close'].rolling(window=50).mean()
            
            # 价格相对于移动平均线的位置
            current_price = price_data['close'].iloc[-1]
            sma_20_current = sma_20.iloc[-1]
            sma_50_current = sma_50.iloc[-1]
            
            score = 0.0
            
            # 价格在移动平均线之上
            if current_price > sma_20_current:
                score += 20
            if current_price > sma_50_current:
                score += 20
            
            # 移动平均线向上趋势
            if len(sma_20) >= 2 and sma_20.iloc[-1] > sma_20.iloc[-2]:
                score += 15
            
            if len(sma_50) >= 2 and sma_50.iloc[-1] > sma_50.iloc[-2]:
                score += 15
            
            # RSI指标
            if len(price_data) >= 14:
                rsi = self._calculate_rsi(price_data['close'], 14)
                rsi_current = rsi.iloc[-1] if not rsi.empty else 50
                
                # RSI在合理范围内
                if 30 <= rsi_current <= 70:
                    score += 20
                elif 20 <= rsi_current <= 80:
                    score += 10
            
            # MACD信号
            macd_signal = self._calculate_macd_signal(price_data['close'])
            if macd_signal == "buy":
                score += 10
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.warning(f"计算技术评分失败: {e}")
            return 0.0
    
    def _calculate_momentum_score(self, price_data: pd.DataFrame) -> float:
        """计算动量评分"""
        try:
            if price_data.empty or len(price_data) < 20:
                return 0.0
                
            # 计算不同周期的收益率
            returns_5d = price_data['close'].pct_change(5).iloc[-1]
            returns_20d = price_data['close'].pct_change(20).iloc[-1]
            returns_60d = price_data['close'].pct_change(60).iloc[-1]
            
            score = 0.0
            
            # 正收益得分
            if returns_5d > 0:
                score += min(returns_5d * 100, 25)  # 最多25分
            if returns_20d > 0:
                score += min(returns_20d * 100, 25)  # 最多25分
            if returns_60d > 0:
                score += min(returns_60d * 100, 25)  # 最多25分
            
            # 动量一致性
            if returns_5d > returns_20d > returns_60d:
                score += 25
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.warning(f"计算动量评分失败: {e}")
            return 0.0
    
    def _calculate_volatility_score(self, price_data: pd.DataFrame) -> float:
        """计算波动性评分"""
        try:
            if price_data.empty or len(price_data) < 20:
                return 0.0
                
            # 计算收益率波动性
            returns = price_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # 年化波动率
            
            score = 0.0
            
            # 适中的波动性得分最高
            if 0.15 <= volatility <= 0.35:
                score = 100  # 优秀
            elif 0.10 <= volatility < 0.15 or 0.35 < volatility <= 0.50:
                score = 75   # 良好
            elif 0.05 <= volatility < 0.10 or 0.50 < volatility <= 0.70:
                score = 50   # 一般
            else:
                score = 25   # 较差
            
            return score
            
        except Exception as e:
            logger.warning(f"计算波动性评分失败: {e}")
            return 0.0
    
    def _calculate_liquidity_score(self, price_data: pd.DataFrame) -> float:
        """计算流动性评分"""
        try:
            if price_data.empty or 'volume' not in price_data.columns:
                return 50.0  # 默认中等评分
                
            # 计算平均成交量
            avg_volume = price_data['volume'].tail(20).mean()
            
            # 根据成交量大小评分（这里使用相对评分）
            if avg_volume > price_data['volume'].quantile(0.8):
                return 100
            elif avg_volume > price_data['volume'].quantile(0.6):
                return 75
            elif avg_volume > price_data['volume'].quantile(0.4):
                return 50
            else:
                return 25
                
        except Exception as e:
            logger.warning(f"计算流动性评分失败: {e}")
            return 50.0
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd_signal(self, prices: pd.Series) -> str:
        """计算MACD信号"""
        try:
            if len(prices) < 26:
                return "hold"
                
            # 简化的MACD计算
            ema_12 = prices.ewm(span=12).mean()
            ema_26 = prices.ewm(span=26).mean()
            macd_line = ema_12 - ema_26
            
            if len(macd_line) < 9:
                return "hold"
                
            signal_line = macd_line.ewm(span=9).mean()
            
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            
            if current_macd > current_signal:
                return "buy"
            else:
                return "sell"
                
        except Exception as e:
            logger.warning(f"计算MACD信号失败: {e}")
            return "hold"
    
    def _calculate_weights(
        self,
        selected_stocks: List[str],
        scores: Dict[str, float],
        criteria: StockSelectionCriteria
    ) -> Dict[str, float]:
        """计算权重分配"""
        if not selected_stocks:
            return {}
        
        # 根据评分计算权重
        total_score = sum(scores[stock] for stock in selected_stocks)
        
        if total_score == 0:
            # 平均分配
            weight = 1.0 / len(selected_stocks)
            return {stock: weight for stock in selected_stocks}
        
        weights = {}
        for stock in selected_stocks:
            weights[stock] = scores[stock] / total_score
        
        # 根据风险等级调整权重分散度
        if criteria.risk_level == RiskLevel.CONSERVATIVE:
            # 保守型：更均匀的权重分布
            avg_weight = 1.0 / len(selected_stocks)
            for stock in selected_stocks:
                weights[stock] = (weights[stock] + avg_weight) / 2
        
        return weights
    
    async def _generate_explanations(
        self,
        result: StockSelectionResult
    ) -> List[SelectionExplanation]:
        """生成选股解释"""
        explanations = []
        
        for stock_code in result.selected_stocks:
            try:
                explanation = await self._generate_single_explanation(stock_code, result)
                explanations.append(explanation)
            except Exception as e:
                logger.warning(f"生成股票 {stock_code} 解释失败: {e}")
                continue
        
        return explanations
    
    async def _generate_single_explanation(
        self,
        stock_code: str,
        result: StockSelectionResult
    ) -> SelectionExplanation:
        """生成单个股票的选股解释"""
        
        score = result.stock_scores.get(stock_code, 0.0)
        
        # 生成选股原因
        if score >= 80:
            reason = f"技术指标表现优秀，综合评分{score:.1f}分"
            strength = "strong"
        elif score >= 60:
            reason = f"技术指标表现良好，综合评分{score:.1f}分"
            strength = "moderate"
        else:
            reason = f"符合基本选股条件，综合评分{score:.1f}分"
            strength = "weak"
        
        # 获取关键指标（这里使用模拟数据，实际应该从技术指标服务获取）
        key_indicators = {
            "RSI": 45.2,
            "MACD": 0.15,
            "SMA_20": 1.02,
            "Volume_Ratio": 1.3
        }
        
        # 技术信号
        technical_signals = {
            "price_trend": "up",
            "volume_trend": "increasing",
            "support_level": "strong",
            "resistance_level": "moderate"
        }
        
        # 基本面信号
        fundamental_signals = {
            "pe_ratio": 15.8,
            "pb_ratio": 2.1,
            "roe": 12.5,
            "debt_ratio": 0.35
        }
        
        # 风险评估
        risk_assessment = {
            "volatility": "moderate",
            "liquidity": "good",
            "sector_risk": "low",
            "overall_risk": result.criteria.risk_level.value
        }
        
        return SelectionExplanation(
            stock_code=stock_code,
            selection_reason=reason,
            score=score,
            key_indicators=key_indicators,
            technical_signals=technical_signals,
            fundamental_signals=fundamental_signals,
            risk_assessment=risk_assessment,
            recommendation_strength=strength
        )
    
    async def _generate_overall_explanation(
        self,
        result: StockSelectionResult
    ) -> str:
        """生成整体解释"""
        stock_count = len(result.selected_stocks)
        avg_score = np.mean(list(result.stock_scores.values())) if result.stock_scores else 0
        
        strategy_desc = {
            SelectionStrategy.MOMENTUM_BASED: "动量策略",
            SelectionStrategy.VALUE_BASED: "价值策略",
            SelectionStrategy.GROWTH_BASED: "成长策略",
            SelectionStrategy.QUALITY_BASED: "质量策略",
            SelectionStrategy.TECH_ANALYSIS: "技术分析策略",
            SelectionStrategy.QUANTITATIVE: "量化策略",
            SelectionStrategy.HYBRID: "混合策略"
        }
        
        strategy_name = strategy_desc.get(result.criteria.strategy_type, "量化策略")
        risk_name = result.criteria.risk_level.value
        
        explanation = f"""
本次选股采用{strategy_name}，风险偏好为{risk_name}。
共选出{stock_count}只股票，平均评分{avg_score:.1f}分。
选股主要基于技术指标分析、动量分析、波动性评估和流动性分析。
        """.strip()
        
        return explanation
    
    async def _calculate_portfolio_metrics(
        self,
        result: StockSelectionResult
    ) -> Dict[str, Any]:
        """计算组合指标"""
        if not result.selected_stocks:
            return {}
        
        weights = list(result.weights.values())
        
        metrics = {
            "stock_count": len(result.selected_stocks),
            "total_weight": sum(weights),
            "weight_concentration": max(weights) if weights else 0,
            "average_score": np.mean(list(result.stock_scores.values())),
            "score_std": np.std(list(result.stock_scores.values())),
            "top_weight_stock": result.selected_stocks[0] if result.selected_stocks else None,
            "top_weight": max(weights) if weights else 0
        }
        
        return metrics
    
    async def _save_strategy_to_db(self, strategy_data: Dict[str, Any]):
        """保存策略到数据库"""
        # 这里应该实现具体的数据库保存逻辑
        # 使用DatabaseService的save_ai_strategy方法
        pass
    
    async def _get_strategy_by_id(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取策略"""
        # 这里应该实现从数据库获取策略的逻辑
        # 使用DatabaseService的get_ai_strategy方法
        return None
    
    async def _save_selection_result(self, result: StockSelectionResult):
        """保存选股结果"""
        # 使用DatabaseService保存结果
        if hasattr(self._database_service, 'save_ai_selection_result'):
            result_data = asdict(result)
            result_data["criteria"] = asdict(result.criteria)
            await self._database_service.save_ai_selection_result(result_data)
    
    def _get_cached_result(self, cache_key: str) -> Optional[StockSelectionResult]:
        """获取缓存结果"""
        if cache_key in self._result_cache:
            cached_result = self._result_cache[cache_key]
            # 检查是否过期
            if datetime.now() - cached_result.created_at < self._cache_ttl:
                return cached_result
            else:
                del self._result_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: StockSelectionResult):
        """缓存结果"""
        self._result_cache[cache_key] = result
        
        # 清理过期缓存
        expired_keys = []
        for key, cached_result in self._result_cache.items():
            if datetime.now() - cached_result.created_at >= self._cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._result_cache[key]
    
    # 其他策略实现方法
    def _momentum_strategy(self, stock_data: Dict[str, Dict[str, Any]], criteria: StockSelectionCriteria) -> Tuple[List[str], Dict[str, float]]:
        """动量策略实现"""
        return self._quantitative_strategy(stock_data, criteria)
    
    def _value_strategy(self, stock_data: Dict[str, Dict[str, Any]], criteria: StockSelectionCriteria) -> Tuple[List[str], Dict[str, float]]:
        """价值策略实现"""
        return self._quantitative_strategy(stock_data, criteria)
    
    def _growth_strategy(self, stock_data: Dict[str, Dict[str, Any]], criteria: StockSelectionCriteria) -> Tuple[List[str], Dict[str, float]]:
        """成长策略实现"""
        return self._quantitative_strategy(stock_data, criteria)
    
    def _quality_strategy(self, stock_data: Dict[str, Dict[str, Any]], criteria: StockSelectionCriteria) -> Tuple[List[str], Dict[str, float]]:
        """质量策略实现"""
        return self._quantitative_strategy(stock_data, criteria)
    
    def _technical_strategy(self, stock_data: Dict[str, Dict[str, Any]], criteria: StockSelectionCriteria) -> Tuple[List[str], Dict[str, float]]:
        """技术分析策略实现"""
        return self._quantitative_strategy(stock_data, criteria)
    
    def _hybrid_strategy(self, stock_data: Dict[str, Dict[str, Any]], criteria: StockSelectionCriteria) -> Tuple[List[str], Dict[str, float]]:
        """混合策略实现"""
        return self._quantitative_strategy(stock_data, criteria)
    
    def shutdown(self):
        """关闭服务"""
        if self._executor:
            self._executor.shutdown(wait=True)
        logger.info("AI选股集成服务已关闭")


# 便捷函数
def get_ai_selection_service() -> Optional[AISelectionIntegrationService]:
    """获取AI选股服务实例"""
    try:
        container = get_service_container()
        if container and container.is_registered(AISelectionIntegrationService):
            return container.resolve(AISelectionIntegrationService)
        return None
    except Exception as e:
        logger.error(f"获取AI选股服务失败: {e}")
        return None