#!/usr/bin/env python3
"""
修复插件接口实现的脚本
将所有插件改为实现 core/data_source_extensions.py 中的 IDataSourcePlugin 接口
"""

import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# 插件配置映射
PLUGIN_CONFIGS = {
    'akshare_stock_plugin.py': {
        'class_name': 'AKShareStockPlugin',
        'plugin_id': 'akshare_stock',
        'name': 'AKShare股票数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.STOCK'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'eastmoney_stock_plugin.py': {
        'class_name': 'EastMoneyStockPlugin',
        'plugin_id': 'eastmoney_stock',
        'name': '东方财富股票数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.STOCK'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'binance_crypto_plugin.py': {
        'class_name': 'BinanceCryptoPlugin',
        'plugin_id': 'binance_crypto',
        'name': 'Binance数字货币数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.CRYPTO'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'coinbase_crypto_plugin.py': {
        'class_name': 'CoinbaseProPlugin',
        'plugin_id': 'coinbase_pro',
        'name': 'Coinbase Pro数字货币数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.CRYPTO'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'huobi_crypto_plugin.py': {
        'class_name': 'HuobiCryptoPlugin',
        'plugin_id': 'huobi_crypto',
        'name': '火币数字货币数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.CRYPTO'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'okx_crypto_plugin.py': {
        'class_name': 'OKXCryptoPlugin',
        'plugin_id': 'okx_crypto',
        'name': 'OKX数字货币数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.CRYPTO'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'ctp_futures_plugin.py': {
        'class_name': 'CTPFuturesPlugin',
        'plugin_id': 'ctp_futures',
        'name': 'CTP期货数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.FUTURES'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'wenhua_data_plugin.py': {
        'class_name': 'WenhuaDataPlugin',
        'plugin_id': 'wenhua_data',
        'name': '文华财经数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.FUTURES', 'AssetType.STOCK'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'mysteel_data_plugin.py': {
        'class_name': 'MySteelDataPlugin',
        'plugin_id': 'mysteel_data',
        'name': '我的钢铁网数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.COMMODITY'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'forex_data_plugin.py': {
        'class_name': 'ForexDataPlugin',
        'plugin_id': 'forex_data',
        'name': '外汇数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.FOREX'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'bond_data_plugin.py': {
        'class_name': 'BondDataPlugin',
        'plugin_id': 'bond_data',
        'name': '债券数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.BOND'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'custom_data_plugin.py': {
        'class_name': 'CustomDataPlugin',
        'plugin_id': 'custom_data',
        'name': '自定义数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.STOCK', 'AssetType.FUTURES', 'AssetType.FOREX'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    },
    'wind_data_plugin.py': {
        'class_name': 'WindDataPlugin',
        'plugin_id': 'wind_data',
        'name': 'Wind万得数据源',
        'author': 'FactorWeave-Quant 团队',
        'supported_asset_types': ['AssetType.STOCK', 'AssetType.BOND', 'AssetType.FUTURES', 'AssetType.FUND', 'AssetType.INDEX'],
        'supported_data_types': ['DataType.HISTORICAL_KLINE', 'DataType.REAL_TIME_QUOTE']
    }
}


def generate_interface_methods(config: Dict) -> str:
    """生成接口方法的实现代码"""

    plugin_id = config['plugin_id']
    name = config['name']
    author = config['author']
    supported_asset_types = ', '.join(config['supported_asset_types'])
    supported_data_types = ', '.join(config['supported_data_types'])

    return f'''
    def get_plugin_info(self) -> PluginInfo:
        """获取插件基本信息"""
        return PluginInfo(
            id="{plugin_id}",
            name="{name}",
            version=self.version,
            description=self.description,
            author="{author}",
            supported_asset_types=[{supported_asset_types}],
            supported_data_types=[{supported_data_types}]
        )
    
    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型列表"""
        return [{supported_data_types}]
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            # 可以在这里处理配置参数
            if hasattr(self, 'configure_api') and 'api_key' in config:
                self.configure_api(config.get('api_key', ''))
            return True
        except Exception as e:
            self.logger.error(f"插件初始化失败: {{e}}")
            return False
    
    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        try:
            # 清理资源
            if hasattr(self, '_disconnect_wind'):
                self._disconnect_wind()
        except Exception as e:
            self.logger.error(f"插件关闭失败: {{e}}")
    
    def fetch_data(self, symbol: str, data_type: str,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   **kwargs) -> pd.DataFrame:
        """获取数据"""
        try:
            import pandas as pd
            
            if data_type == "historical_kline":
                if start_date is None:
                    start_date = datetime.now() - timedelta(days=30)
                if end_date is None:
                    end_date = datetime.now()
                    
                kline_data = self.get_kline_data(symbol, start_date, end_date, 
                                               kwargs.get('frequency', '1d'))
                
                # 转换为DataFrame格式
                if kline_data:
                    data = []
                    for kline in kline_data:
                        data.append({{
                            'datetime': kline.timestamp,
                            'open': kline.open,
                            'high': kline.high,
                            'low': kline.low,
                            'close': kline.close,
                            'volume': kline.volume
                        }})
                    return pd.DataFrame(data)
                else:
                    return pd.DataFrame()
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"数据获取失败: {{e}}")
            return pd.DataFrame()
    
    def get_real_time_data(self, symbols: List[str]) -> Dict[str, Any]:
        """获取实时数据"""
        try:
            result = {{}}
            for symbol in symbols:
                market_data = self.get_market_data(symbol)
                if market_data:
                    result[symbol] = {{
                        'symbol': symbol,
                        'price': market_data.current_price,
                        'open': market_data.open_price,
                        'high': market_data.high_price,
                        'low': market_data.low_price,
                        'volume': market_data.volume,
                        'change': market_data.change_amount,
                        'change_pct': market_data.change_percent,
                        'timestamp': market_data.timestamp.isoformat()
                    }}
            return result
        except Exception as e:
            self.logger.error(f"实时数据获取失败: {{e}}")
            return {{}}'''


def add_missing_imports(content: str) -> str:
    """添加缺失的导入"""
    imports_to_add = []

    # 检查是否需要添加导入
    if 'PluginInfo' not in content:
        imports_to_add.append('PluginInfo')
    if 'pd.DataFrame' in content and 'import pandas as pd' not in content:
        if 'import pandas as pd' not in content:
            imports_to_add.append('pd')

    if imports_to_add:
        # 找到现有导入的位置
        import_lines = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if line.startswith('from core.data_source_data_models import'):
                # 替换导入语句
                lines[i] = 'from core.data_source_extensions import IDataSourcePlugin, PluginInfo'
                lines.insert(i+1, 'from core.plugin_types import AssetType, DataType')
                if 'pd' in imports_to_add:
                    lines.insert(i+2, 'import pandas as pd')
                break

        content = '\n'.join(lines)

    return content


def fix_plugin_file(file_path: str, config: Dict) -> bool:
    """修复单个插件文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复导入语句
        content = content.replace(
            'from core.data_source_data_models import',
            'from core.data_source_extensions import IDataSourcePlugin, PluginInfo\n'
            'from core.plugin_types import AssetType, DataType\n'
            'from core.data_source_data_models import'
        )

        # 添加缺失的导入
        if 'import pandas as pd' not in content:
            content = content.replace(
                'import requests',
                'import requests\nimport pandas as pd'
            )

        # 生成接口方法实现
        interface_methods = generate_interface_methods(config)

        # 找到类定义的结束位置，添加新方法
        class_name = config['class_name']
        class_pattern = f'class {class_name}\\(IDataSourcePlugin\\):'

        if re.search(class_pattern, content):
            # 在类的最后添加接口方法
            # 找到类的最后一个方法结束位置
            lines = content.split('\n')
            last_method_end = -1
            in_class = False
            class_indent = 0

            for i, line in enumerate(lines):
                if re.match(class_pattern, line):
                    in_class = True
                    class_indent = len(line) - len(line.lstrip())
                    continue

                if in_class:
                    if line.strip() == '' or line.startswith(' ' * (class_indent + 4)):
                        last_method_end = i
                    elif line.strip() and not line.startswith(' ' * (class_indent + 1)):
                        # 遇到新的顶级定义，停止
                        break

            if last_method_end > 0:
                lines.insert(last_method_end + 1, interface_methods)
                content = '\n'.join(lines)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 修复了 {file_path}")
        return True

    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False


def main():
    """主函数"""
    plugins_dir = "plugins/examples"

    if not os.path.exists(plugins_dir):
        print(f"❌ 插件目录不存在: {plugins_dir}")
        return

    fixed_count = 0
    total_count = 0

    print("开始修复插件接口...")
    print("=" * 50)

    for plugin_file, config in PLUGIN_CONFIGS.items():
        file_path = os.path.join(plugins_dir, plugin_file)
        if os.path.exists(file_path):
            total_count += 1
            if fix_plugin_file(file_path, config):
                fixed_count += 1
        else:
            print(f"⚠️  插件文件不存在: {file_path}")

    print("=" * 50)
    print(f"修复完成: {fixed_count}/{total_count} 个文件")


if __name__ == "__main__":
    main()
