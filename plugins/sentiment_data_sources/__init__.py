"""
情绪数据源插件包
提供多种情绪分析数据源的统一接口
"""

from .base_sentiment_plugin import BaseSentimentPlugin
from .config_base import ConfigurablePlugin, PluginConfigField

# 导入新的独立插件
from .fmp_sentiment_plugin import FMPSentimentPlugin
from .exorde_sentiment_plugin import ExordeSentimentPlugin
from .news_sentiment_plugin import NewsSentimentPlugin
from .vix_sentiment_plugin import VIXSentimentPlugin
from .crypto_sentiment_plugin import CryptoSentimentPlugin

# 保留多源插件作为备用
from .multi_source_sentiment_plugin import MultiSourceSentimentPlugin

# 可选导入AkShare插件（如果依赖不可用则跳过）
try:
    from .akshare_sentiment_plugin import AkShareSentimentPlugin
    AKSHARE_AVAILABLE = True
except ImportError:
    AkShareSentimentPlugin = None
    AKSHARE_AVAILABLE = False

# 可用的情绪数据源插件
__all__ = [
    'BaseSentimentPlugin',
    'ConfigurablePlugin',
    'PluginConfigField',
    'FMPSentimentPlugin',
    'ExordeSentimentPlugin',
    'NewsSentimentPlugin',
    'VIXSentimentPlugin',
    'CryptoSentimentPlugin',
    'MultiSourceSentimentPlugin'
]

if AKSHARE_AVAILABLE:
    __all__.append('AkShareSentimentPlugin')

# 插件注册表 - 现在以独立插件为主
AVAILABLE_PLUGINS = {
    'fmp_sentiment': FMPSentimentPlugin,
    'exorde_sentiment': ExordeSentimentPlugin,
    'news_sentiment': NewsSentimentPlugin,
    'vix_sentiment': VIXSentimentPlugin,
    'crypto_sentiment': CryptoSentimentPlugin,
    'multi_source': MultiSourceSentimentPlugin,  # 保留作为备用
}

if AKSHARE_AVAILABLE:
    AVAILABLE_PLUGINS['akshare'] = AkShareSentimentPlugin

# 获取默认插件


def get_default_plugin():
    """获取默认的情绪数据源插件"""
    # 现在优先使用FMP插件，然后是其他独立插件
    try:
        return FMPSentimentPlugin()
    except Exception:
        try:
            return MultiSourceSentimentPlugin()
        except Exception:
            if AKSHARE_AVAILABLE:
                return AkShareSentimentPlugin()
            else:
                raise RuntimeError("没有可用的情绪数据源插件")


def get_plugin_by_name(name: str):
    """根据名称获取插件"""
    if name in AVAILABLE_PLUGINS:
        return AVAILABLE_PLUGINS[name]()
    else:
        available_names = list(AVAILABLE_PLUGINS.keys())
        raise ValueError(f"未找到名为 {name} 的插件。可用插件: {available_names}")


def list_available_plugins():
    """列出所有可用的插件"""
    return list(AVAILABLE_PLUGINS.keys())


def check_plugin_availability():
    """检查插件可用性"""
    return {
        'fmp_sentiment': True,
        'exorde_sentiment': True,
        'news_sentiment': True,
        'vix_sentiment': True,
        'crypto_sentiment': True,
        'multi_source': True,
        'akshare': AKSHARE_AVAILABLE,
        'total_available': len(AVAILABLE_PLUGINS)
    }
