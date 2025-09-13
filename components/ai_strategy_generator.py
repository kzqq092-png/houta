from loguru import logger
"""
AI策略生成器 - 重构版本

使用服务容器获取交易服务，符合插件架构原则
"""

from core.containers import get_service_container
from core.services.trading_service import TradingService

logger = logger


def run_backtest(params):
    """
    运行回测 - 使用服务架构

    Args:
        params: 回测参数

    Returns:
        回测结果
    """
    try:
        # 获取交易服务
        service_container = get_service_container()
        trading_service = service_container.resolve(TradingService)

        if not trading_service:
            logger.error("无法获取交易服务")
            return {}

        # 使用交易服务运行回测
        if hasattr(trading_service, 'run_backtest'):
            return trading_service.run_backtest(params)
        else:
            logger.error("交易服务不支持回测功能")
            return {}

    except Exception as e:
        logger.error(f"回测失败: {e}")
        return {}
