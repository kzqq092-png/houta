"""
情绪数据源插件包

这个包包含各种情绪数据源的插件实现，为应用程序提供实时市场情绪数据。

插件包括：
- AkShareSentimentPlugin: 基于AkShare库的情绪数据源
- BaseSentimentPlugin: 情绪数据源插件的基础类

使用方法：
    from plugins.sentiment_data_sources.akshare_sentiment_plugin import AkShareSentimentPlugin
    
    plugin = AkShareSentimentPlugin()
    plugin.initialize()
    sentiment_data = plugin.fetch_sentiment_data()
"""

from .base_sentiment_plugin import BaseSentimentPlugin
from .akshare_sentiment_plugin import AkShareSentimentPlugin

__version__ = "1.0.0"
__author__ = "HIkyuu-UI Team"

# 导出的类
__all__ = [
    'BaseSentimentPlugin',
    'AkShareSentimentPlugin',
]

# 注册可用的情绪数据源插件
AVAILABLE_SENTIMENT_PLUGINS = {
    'akshare': AkShareSentimentPlugin,
    # 在这里添加更多插件
}


def get_available_plugins():
    """获取所有可用的情绪数据源插件"""
    return AVAILABLE_SENTIMENT_PLUGINS.copy()


def create_plugin(plugin_name: str):
    """根据名称创建插件实例"""
    if plugin_name in AVAILABLE_SENTIMENT_PLUGINS:
        return AVAILABLE_SENTIMENT_PLUGINS[plugin_name]()
    else:
        raise ValueError(f"未知的情绪数据源插件: {plugin_name}")
