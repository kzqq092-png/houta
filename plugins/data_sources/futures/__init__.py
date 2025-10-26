"""
期货数据源插件目录

包含所有期货交易相关的数据源插件
"""

# 插件列表
FUTURES_PLUGINS = [
    'ctp_plugin',             # CTP（中国期货标准）
    'wenhua_plugin',          # 文华财经
    'futures_universal_plugin'  # 通用接口
]

__all__ = FUTURES_PLUGINS
