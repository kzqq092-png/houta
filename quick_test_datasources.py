#!/usr/bin/env python3
"""
快速测试所有数据源插件状态
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def quick_test_plugin(plugin_module, plugin_class):
    """快速测试单个插件"""
    try:
        # 导入插件
        module = __import__(f'plugins.examples.{plugin_module}', fromlist=[plugin_class])
        plugin_cls = getattr(module, plugin_class)

        # 创建实例
        plugin = plugin_cls()

        # 初始化
        init_result = plugin.initialize({})

        # 检查连接状态
        is_connected = False
        if hasattr(plugin, 'is_connected'):
            is_connected = plugin.is_connected()

        # 检查健康状态
        health_ok = False
        health_msg = "无健康检查"
        if hasattr(plugin, 'health_check'):
            try:
                health_result = plugin.health_check()
                health_ok = getattr(health_result, 'is_healthy', False)
                health_msg = getattr(health_result, 'message', 'ok') if health_ok else getattr(health_result, 'message', 'failed')
            except Exception as e:
                health_msg = f"异常: {str(e)[:50]}"

        # 最终状态判断
        status = "🟢" if (init_result and is_connected and health_ok) else "🔴"

        return {
            'plugin': plugin_module,
            'status': status,
            'init': init_result,
            'connected': is_connected,
            'health': health_ok,
            'health_msg': health_msg[:50]
        }

    except Exception as e:
        return {
            'plugin': plugin_module,
            'status': "🔴",
            'init': False,
            'connected': False,
            'health': False,
            'health_msg': f"测试异常: {str(e)[:50]}"
        }


def main():
    """主函数"""
    print("🔍 快速测试所有数据源插件...")

    # 数据源插件列表
    plugins = [
        ('crypto_data_plugin', 'CryptoDataPlugin'),
        ('forex_data_plugin', 'ForexDataPlugin'),
        ('futures_data_plugin', 'FuturesDataPlugin'),
        ('wind_data_plugin', 'WindDataPlugin'),
        ('akshare_stock_plugin', 'AKShareStockPlugin'),
        ('eastmoney_stock_plugin', 'EastMoneyStockPlugin'),
        ('yahoo_finance_datasource', 'YahooFinanceDataSourcePlugin'),
        ('binance_crypto_plugin', 'BinanceCryptoPlugin'),
        ('huobi_crypto_plugin', 'HuobiCryptoPlugin'),
        ('okx_crypto_plugin', 'OKXCryptoPlugin'),
        ('coinbase_crypto_plugin', 'CoinbaseProPlugin'),
        ('ctp_futures_plugin', 'CTPFuturesPlugin'),
        ('mysteel_data_plugin', 'MySteelDataPlugin'),
        ('wenhua_data_plugin', 'WenhuaDataPlugin'),
        ('bond_data_plugin', 'BondDataPlugin'),
        ('custom_data_plugin', 'CustomDataPlugin'),
    ]

    results = []
    for plugin_module, plugin_class in plugins:
        result = quick_test_plugin(plugin_module, plugin_class)
        results.append(result)

    # 显示结果
    print("\n" + "="*80)
    print("📊 数据源插件状态汇总:")
    print("="*80)

    active_count = 0
    problem_plugins = []

    for result in results:
        status_icon = result['status']
        plugin_name = result['plugin']

        # 状态详情
        details = []
        if not result['init']:
            details.append("初始化失败")
        if not result['connected']:
            details.append("未连接")
        if not result['health']:
            details.append(f"健康检查: {result['health_msg']}")

        detail_str = " | ".join(details) if details else "正常"

        print(f"{status_icon} {plugin_name:<25} - {detail_str}")

        if result['status'] == "🟢":
            active_count += 1
        else:
            problem_plugins.append(plugin_name)

    print(f"\n📈 统计: {active_count}/{len(results)} 个插件状态正常")

    if problem_plugins:
        print(f"\n❌ 需要修复的插件:")
        for plugin in problem_plugins:
            print(f"   - {plugin}")

    return len(problem_plugins)


if __name__ == "__main__":
    problem_count = main()
    sys.exit(0 if problem_count == 0 else 1)
