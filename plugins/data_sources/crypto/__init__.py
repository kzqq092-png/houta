"""
加密货币数据源插件目录

包含所有加密货币交易所的数据源插件
"""

# 插件列表
CRYPTO_PLUGINS = [
    'binance_plugin',        # 币安（全球最大）
    'okx_plugin',            # OKX（衍生品丰富）
    'huobi_plugin',          # 火币（中文友好）
    'coinbase_plugin',       # Coinbase（合规）
    'crypto_universal_plugin'  # 通用接口
]

__all__ = CRYPTO_PLUGINS
