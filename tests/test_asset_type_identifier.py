"""
AssetTypeIdentifier 测试文件

测试资产类型识别器的各种功能和边界情况。

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
"""

from core.plugin_types import AssetType
from core.asset_type_identifier import AssetTypeIdentifier, get_asset_type_identifier, identify_asset_type
import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAssetTypeIdentifier(unittest.TestCase):
    """AssetTypeIdentifier 测试类"""

    def setUp(self):
        """测试前设置"""
        self.identifier = AssetTypeIdentifier()

    def test_a_stock_identification(self):
        """测试A股识别"""
        test_cases = [
            # 深交所A股
            ("000001.SZ", AssetType.STOCK_A),
            ("000002.sz", AssetType.STOCK_A),
            ("002001.SZ", AssetType.STOCK_A),
            ("300001.SZ", AssetType.STOCK_A),
            # 上交所A股
            ("600000.SH", AssetType.STOCK_A),
            ("601001.sh", AssetType.STOCK_A),
            ("603001.SH", AssetType.STOCK_A),
            ("605001.SH", AssetType.STOCK_A),
            ("688001.SH", AssetType.STOCK_A),  # 科创板
        ]

        for symbol, expected_type in test_cases:
            with self.subTest(symbol=symbol):
                result = self.identifier.identify_asset_type_by_symbol(symbol)
                self.assertEqual(result, expected_type, f"识别失败: {symbol} -> {result}, 期望: {expected_type}")

    def test_b_stock_identification(self):
        """测试B股识别"""
        test_cases = [
            ("200001.SZ", AssetType.STOCK_B),   # 深交所B股
            ("900001.SH", AssetType.STOCK_B),   # 上交所B股
        ]

        for symbol, expected_type in test_cases:
            with self.subTest(symbol=symbol):
                result = self.identifier.identify_asset_type_by_symbol(symbol)
                self.assertEqual(result, expected_type)

    def test_hk_stock_identification(self):
        """测试港股识别"""
        test_cases = [
            ("0700.HK", AssetType.STOCK_HK),    # 腾讯
            ("9988.hk", AssetType.STOCK_HK),    # 阿里巴巴
            ("00001.HK", AssetType.STOCK_HK),   # 长和
        ]

        for symbol, expected_type in test_cases:
            with self.subTest(symbol=symbol):
                result = self.identifier.identify_asset_type_by_symbol(symbol)
                self.assertEqual(result, expected_type)

    def test_us_stock_identification(self):
        """测试美股识别"""
        test_cases = [
            ("AAPL", AssetType.STOCK_US),       # 苹果
            ("MSFT", AssetType.STOCK_US),       # 微软
            ("GOOGL", AssetType.STOCK_US),      # 谷歌
            ("TSLA", AssetType.STOCK_US),       # 特斯拉
            ("AAPL.US", AssetType.STOCK_US),    # 带后缀
            ("MSFT.NASDAQ", AssetType.STOCK_US),
        ]

        for symbol, expected_type in test_cases:
            with self.subTest(symbol=symbol):
                result = self.identifier.identify_asset_type_by_symbol(symbol)
                self.assertEqual(result, expected_type)

    def test_crypto_identification(self):
        """测试数字货币识别"""
        test_cases = [
            ("BTCUSDT", AssetType.CRYPTO),      # 比特币
            ("ETHUSDT", AssetType.CRYPTO),      # 以太坊
            ("BTC", AssetType.CRYPTO),          # 比特币简称
            ("ETH", AssetType.CRYPTO),          # 以太坊简称
            ("USDT", AssetType.CRYPTO),         # 稳定币
            ("DOGEUSDT", AssetType.CRYPTO),     # 狗狗币
        ]

        for symbol, expected_type in test_cases:
            with self.subTest(symbol=symbol):
                result = self.identifier.identify_asset_type_by_symbol(symbol)
                self.assertEqual(result, expected_type)

    def test_futures_identification(self):
        """测试期货识别"""
        test_cases = [
            # 中金所
            ("IF2312", AssetType.FUTURES),      # 沪深300期货
            ("IC2312", AssetType.FUTURES),      # 中证500期货
            ("IH2312", AssetType.FUTURES),      # 上证50期货
            ("T2312", AssetType.FUTURES),       # 10年期国债期货
            # 上期所
            ("CU2312", AssetType.FUTURES),      # 铜
            ("AU2312", AssetType.FUTURES),      # 黄金
            ("AG2312", AssetType.FUTURES),      # 白银
            # 大商所
            ("A2401", AssetType.FUTURES),       # 豆一
            ("M2401", AssetType.FUTURES),       # 豆粕
            # 郑商所
            ("CF2401", AssetType.FUTURES),      # 棉花
            ("SR2401", AssetType.FUTURES),      # 白糖
        ]

        for symbol, expected_type in test_cases:
            with self.subTest(symbol=symbol):
                result = self.identifier.identify_asset_type_by_symbol(symbol)
                self.assertEqual(result, expected_type)

    def test_fund_identification(self):
        """测试基金识别"""
        test_cases = [
            ("110001.OF", AssetType.FUND),      # 开放式基金
            ("510050.SH", AssetType.FUND),      # ETF
            ("159919.SZ", AssetType.FUND),      # ETF
        ]

        for symbol, expected_type in test_cases:
            with self.subTest(symbol=symbol):
                result = self.identifier.identify_asset_type_by_symbol(symbol)
                self.assertEqual(result, expected_type)

    def test_index_identification(self):
        """测试指数识别"""
        test_cases = [
            ("000001.SH", AssetType.INDEX),     # 上证指数
            ("399001.SZ", AssetType.INDEX),     # 深证成指
        ]

        for symbol, expected_type in test_cases:
            with self.subTest(symbol=symbol):
                result = self.identifier.identify_asset_type_by_symbol(symbol)
                self.assertEqual(result, expected_type)

    def test_exchange_based_identification(self):
        """测试基于交易所的识别"""
        test_cases = [
            ("000001", "SSE", AssetType.STOCK_A),
            ("AAPL", "NASDAQ", AssetType.STOCK_US),
            ("0700", "HKEX", AssetType.STOCK_HK),
            ("BTCUSDT", "BINANCE", AssetType.CRYPTO),
        ]

        for symbol, exchange, expected_type in test_cases:
            with self.subTest(symbol=symbol, exchange=exchange):
                result = self.identifier.identify_asset_type_by_exchange(symbol, exchange)
                self.assertEqual(result, expected_type)

    def test_batch_identification(self):
        """测试批量识别"""
        symbols = ["000001.SZ", "AAPL", "BTCUSDT", "IF2312"]
        expected_types = [AssetType.STOCK_A, AssetType.STOCK_US, AssetType.CRYPTO, AssetType.FUTURES]

        results = self.identifier.batch_identify_asset_types(symbols)

        for symbol, expected_type in zip(symbols, expected_types):
            self.assertEqual(results[symbol], expected_type)

    def test_invalid_symbols(self):
        """测试无效股票代码"""
        invalid_symbols = ["", None, "   ", "INVALID123456789"]

        for symbol in invalid_symbols:
            with self.subTest(symbol=symbol):
                if symbol is None:
                    result = self.identifier.identify_asset_type_by_symbol(symbol)
                    self.assertEqual(result, AssetType.STOCK)  # 默认返回股票类型
                else:
                    result = self.identifier.identify_asset_type_by_symbol(symbol)
                    # 无效代码应该返回默认股票类型或者能处理
                    self.assertIsInstance(result, AssetType)

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        test_cases = [
            ("000001.sz", "000001.SZ"),
            ("aapl", "AAPL"),
            ("btcusdt", "BTCUSDT"),
        ]

        for lower_case, upper_case in test_cases:
            with self.subTest(lower=lower_case, upper=upper_case):
                result_lower = self.identifier.identify_asset_type_by_symbol(lower_case)
                result_upper = self.identifier.identify_asset_type_by_symbol(upper_case)
                self.assertEqual(result_lower, result_upper)

    def test_cache_functionality(self):
        """测试缓存功能"""
        symbol = "000001.SZ"

        # 第一次识别
        result1 = self.identifier.identify_asset_type_by_symbol(symbol)

        # 检查缓存统计
        cache_stats = self.identifier.get_cache_stats()
        self.assertEqual(cache_stats["cache_size"], 1)

        # 第二次识别（应该使用缓存）
        result2 = self.identifier.identify_asset_type_by_symbol(symbol)
        self.assertEqual(result1, result2)

        # 清除缓存
        self.identifier.clear_cache()
        cache_stats_after = self.identifier.get_cache_stats()
        self.assertEqual(cache_stats_after["cache_size"], 0)

    def test_database_mapping(self):
        """测试数据库映射"""
        test_cases = [
            (AssetType.STOCK_A, "stock_data.duckdb"),
            (AssetType.FUTURES, "futures_data.duckdb"),
            (AssetType.CRYPTO, "crypto_data.duckdb"),
            (AssetType.FUND, "fund_data.duckdb"),
        ]

        for asset_type, expected_db in test_cases:
            with self.subTest(asset_type=asset_type):
                result = self.identifier.get_database_for_asset_type(asset_type)
                self.assertEqual(result, expected_db)

    def test_statistics(self):
        """测试统计功能"""
        symbols = ["000001.SZ", "000002.SZ", "AAPL", "MSFT", "BTCUSDT"]
        statistics = self.identifier.get_asset_type_statistics(symbols)

        # 验证统计结果
        self.assertIn(AssetType.STOCK_A, statistics)
        self.assertIn(AssetType.STOCK_US, statistics)
        self.assertIn(AssetType.CRYPTO, statistics)

        # 验证数量
        self.assertEqual(len(statistics[AssetType.STOCK_A]), 2)
        self.assertEqual(len(statistics[AssetType.STOCK_US]), 2)
        self.assertEqual(len(statistics[AssetType.CRYPTO]), 1)

    def test_symbol_validation(self):
        """测试股票代码验证"""
        valid_symbols = ["000001.SZ", "AAPL", "BTCUSDT"]
        invalid_symbols = ["", None, "   "]

        for symbol in valid_symbols:
            with self.subTest(symbol=symbol):
                self.assertTrue(self.identifier.is_valid_symbol(symbol))

        for symbol in invalid_symbols:
            with self.subTest(symbol=symbol):
                self.assertFalse(self.identifier.is_valid_symbol(symbol))

    def test_global_instance(self):
        """测试全局实例"""
        instance1 = get_asset_type_identifier()
        instance2 = get_asset_type_identifier()

        # 应该是同一个实例（单例模式）
        self.assertIs(instance1, instance2)

        # 测试便捷函数
        result = identify_asset_type("000001.SZ")
        self.assertEqual(result, AssetType.STOCK_A)


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
