#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密货币情绪分析插件
基于加密货币Fear & Greed指数和市场数据分析情绪
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from plugins.plugin_interface import PluginType, PluginCategory, PluginMetadata
from .base_sentiment_plugin import BaseSentimentPlugin
from .config_base import ConfigurablePlugin, PluginConfigField, create_config_file_path, validate_number_range
from plugins.sentiment_data_source_interface import SentimentData, SentimentResponse


class CryptoSentimentPlugin(BaseSentimentPlugin, ConfigurablePlugin):
    """加密货币情绪分析插件"""

    def __init__(self):
        BaseSentimentPlugin.__init__(self)
        ConfigurablePlugin.__init__(self)
        self._config_file = create_config_file_path("crypto_sentiment")

        # 支持的加密货币
        self.supported_cryptos = [
            "BTC", "ETH", "BNB", "ADA", "XRP", "DOT", "LINK", "LTC",
            "BCH", "XLM", "DOGE", "UNI", "AAVE", "MATIC", "SOL"
        ]

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="加密货币情绪插件",
            version="1.0.0",
            author="HIkyuu-UI Team",
            email="support@hikyuu.com",
            website="https://github.com/hikyuu/hikyuu-ui",
            license="MIT",
            description="基于加密货币Fear & Greed指数和市场数据分析整体市场情绪",
            plugin_type=PluginType.DATA_SOURCE,
            category=PluginCategory.CORE,
            dependencies=[],
            min_hikyuu_version="1.0.0",
            max_hikyuu_version="2.0.0",
            documentation_url="",
            tags=["sentiment", "crypto", "bitcoin", "fear_greed", "market"]
        )

    def get_config_schema(self) -> List[PluginConfigField]:
        """获取配置模式定义"""
        return [
            # 基本设置
            PluginConfigField(
                name="enabled",
                display_name="启用插件",
                field_type="boolean",
                default_value=True,
                description="是否启用加密货币情绪分析插件",
                group="基本设置"
            ),

            # 加密货币设置
            PluginConfigField(
                name="monitored_cryptos",
                display_name="监控币种",
                field_type="multiselect",
                default_value=["BTC", "ETH", "BNB"],
                description="需要监控的加密货币种类",
                options=self.supported_cryptos,
                group="加密货币设置"
            ),
            PluginConfigField(
                name="crypto_weights",
                display_name="币种权重",
                field_type="string",
                default_value="BTC:0.5,ETH:0.3,BNB:0.2",
                description="各币种在情绪分析中的权重（格式：币种:权重,币种:权重）",
                placeholder="BTC:0.5,ETH:0.3,BNB:0.2",
                group="加密货币设置"
            ),
            PluginConfigField(
                name="include_altcoins",
                display_name="包含山寨币",
                field_type="boolean",
                default_value=True,
                description="是否包含山寨币情绪分析",
                group="加密货币设置"
            ),

            # Fear & Greed 设置
            PluginConfigField(
                name="fear_greed_source",
                display_name="恐贪指数源",
                field_type="select",
                default_value="alternative_me",
                description="Fear & Greed指数数据源",
                options=["alternative_me", "simulated", "custom"],
                group="Fear & Greed设置"
            ),
            PluginConfigField(
                name="extreme_fear_threshold",
                display_name="极度恐惧阈值",
                field_type="number",
                default_value=25,
                description="极度恐惧状态的阈值",
                min_value=0,
                max_value=40,
                group="Fear & Greed设置"
            ),
            PluginConfigField(
                name="fear_threshold",
                display_name="恐惧阈值",
                field_type="number",
                default_value=45,
                description="恐惧状态的阈值",
                min_value=20,
                max_value=60,
                group="Fear & Greed设置"
            ),
            PluginConfigField(
                name="greed_threshold",
                display_name="贪婪阈值",
                field_type="number",
                default_value=75,
                description="贪婪状态的阈值",
                min_value=60,
                max_value=90,
                group="Fear & Greed设置"
            ),
            PluginConfigField(
                name="extreme_greed_threshold",
                display_name="极度贪婪阈值",
                field_type="number",
                default_value=90,
                description="极度贪婪状态的阈值",
                min_value=80,
                max_value=100,
                group="Fear & Greed设置"
            ),

            # 市场影响设置
            PluginConfigField(
                name="traditional_market_impact",
                display_name="传统市场影响度",
                field_type="number",
                default_value=0.3,
                description="加密货币对传统市场情绪的影响权重",
                min_value=0.0,
                max_value=1.0,
                group="市场影响设置"
            ),
            PluginConfigField(
                name="correlation_adjustment",
                display_name="相关性调整",
                field_type="boolean",
                default_value=True,
                description="是否根据与传统市场的相关性调整权重",
                group="市场影响设置"
            ),
            PluginConfigField(
                name="data_weight",
                display_name="数据权重",
                field_type="number",
                default_value=0.15,
                description="加密货币数据在综合情绪指数中的权重",
                min_value=0.0,
                max_value=1.0,
                group="市场影响设置"
            ),

            # 分析设置
            PluginConfigField(
                name="enable_dominance_analysis",
                display_name="启用主导地位分析",
                field_type="boolean",
                default_value=True,
                description="是否启用比特币主导地位分析",
                group="分析设置"
            ),
            PluginConfigField(
                name="enable_volatility_analysis",
                display_name="启用波动率分析",
                field_type="boolean",
                default_value=True,
                description="是否启用加密货币波动率分析",
                group="分析设置"
            ),
            PluginConfigField(
                name="sentiment_smoothing",
                display_name="情绪平滑",
                field_type="number",
                default_value=0.2,
                description="情绪数据平滑处理系数",
                min_value=0.0,
                max_value=1.0,
                group="分析设置"
            ),

            # 更新设置
            PluginConfigField(
                name="update_interval",
                display_name="更新间隔",
                field_type="number",
                default_value=60,
                description="数据更新间隔（分钟）",
                min_value=5,
                max_value=1440,
                group="更新设置"
            ),
            PluginConfigField(
                name="cache_duration",
                display_name="缓存时长",
                field_type="number",
                default_value=30,
                description="数据缓存时长（分钟）",
                min_value=5,
                max_value=240,
                group="更新设置"
            ),

            # 高级设置
            PluginConfigField(
                name="defi_sentiment_weight",
                display_name="DeFi情绪权重",
                field_type="number",
                default_value=0.1,
                description="DeFi市场情绪在分析中的权重",
                min_value=0.0,
                max_value=0.5,
                group="高级设置"
            ),
            PluginConfigField(
                name="nft_sentiment_weight",
                display_name="NFT情绪权重",
                field_type="number",
                default_value=0.05,
                description="NFT市场情绪在分析中的权重",
                min_value=0.0,
                max_value=0.3,
                group="高级设置"
            )
        ]

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "enabled": True,
            "monitored_cryptos": ["BTC", "ETH", "BNB"],
            "crypto_weights": "BTC:0.5,ETH:0.3,BNB:0.2",
            "include_altcoins": True,
            "fear_greed_source": "alternative_me",
            "extreme_fear_threshold": 25,
            "fear_threshold": 45,
            "greed_threshold": 75,
            "extreme_greed_threshold": 90,
            "traditional_market_impact": 0.3,
            "correlation_adjustment": True,
            "data_weight": 0.15,
            "enable_dominance_analysis": True,
            "enable_volatility_analysis": True,
            "sentiment_smoothing": 0.2,
            "update_interval": 60,
            "cache_duration": 30,
            "defi_sentiment_weight": 0.1,
            "nft_sentiment_weight": 0.05
        }

    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """验证配置"""
        try:
            # 验证阈值递增关系
            extreme_fear = config.get("extreme_fear_threshold", 25)
            fear = config.get("fear_threshold", 45)
            greed = config.get("greed_threshold", 75)
            extreme_greed = config.get("extreme_greed_threshold", 90)

            if not (extreme_fear < fear < greed < extreme_greed):
                return False, "Fear & Greed阈值必须递增：极度恐惧 < 恐惧 < 贪婪 < 极度贪婪"

            # 验证权重配置
            weights_str = config.get("crypto_weights", "")
            try:
                self._parse_crypto_weights(weights_str)
            except Exception as e:
                return False, f"币种权重格式错误: {str(e)}"

            # 验证各项权重范围
            weight_fields = [
                ("traditional_market_impact", "传统市场影响度"),
                ("data_weight", "数据权重"),
                ("sentiment_smoothing", "情绪平滑"),
                ("defi_sentiment_weight", "DeFi情绪权重"),
                ("nft_sentiment_weight", "NFT情绪权重")
            ]

            for field, display_name in weight_fields:
                value = config.get(field, 0)
                is_valid, msg = validate_number_range(value, 0.0, 1.0)
                if not is_valid:
                    return False, f"{display_name}: {msg}"

            # 验证监控币种
            monitored_cryptos = config.get("monitored_cryptos", [])
            if not monitored_cryptos:
                return False, "至少需要监控一种加密货币"

            for crypto in monitored_cryptos:
                if crypto not in self.supported_cryptos:
                    return False, f"不支持的加密货币: {crypto}"

            return True, "配置验证通过"

        except Exception as e:
            return False, f"配置验证异常: {str(e)}"

    def get_available_indicators(self) -> List[str]:
        """获取可用的情绪指标列表"""
        indicators = ["加密货币Fear&Greed指数"]

        if self.get_config("enable_dominance_analysis", True):
            indicators.append("比特币主导地位")

        if self.get_config("enable_volatility_analysis", True):
            indicators.append("加密市场波动率")

        if self.get_config("defi_sentiment_weight", 0.1) > 0:
            indicators.append("DeFi市场情绪")

        if self.get_config("nft_sentiment_weight", 0.05) > 0:
            indicators.append("NFT市场情绪")

        return indicators

    def _fetch_raw_sentiment_data(self, **kwargs) -> SentimentResponse:
        """获取加密货币原始情绪数据"""
        if not self.is_enabled():
            return SentimentResponse(
                success=False,
                data=[],
                composite_score=50.0,
                error_message="加密货币情绪插件已禁用",
                data_quality="disabled",
                update_time=datetime.now()
            )

        try:
            self._safe_log("info", "开始获取加密货币情绪数据...")

            sentiment_data = []

            # 1. 获取Fear & Greed指数
            fear_greed_data = self._fetch_fear_greed_data()
            if fear_greed_data:
                sentiment_data.append(fear_greed_data)

            # 2. 获取比特币主导地位（如果启用）
            if self.get_config("enable_dominance_analysis", True):
                dominance_data = self._fetch_btc_dominance_data()
                if dominance_data:
                    sentiment_data.append(dominance_data)

            # 3. 获取市场波动率（如果启用）
            if self.get_config("enable_volatility_analysis", True):
                volatility_data = self._fetch_crypto_volatility_data()
                if volatility_data:
                    sentiment_data.append(volatility_data)

            # 4. 获取DeFi情绪（如果启用）
            if self.get_config("defi_sentiment_weight", 0.1) > 0:
                defi_data = self._fetch_defi_sentiment_data()
                if defi_data:
                    sentiment_data.append(defi_data)

            # 5. 获取NFT情绪（如果启用）
            if self.get_config("nft_sentiment_weight", 0.05) > 0:
                nft_data = self._fetch_nft_sentiment_data()
                if nft_data:
                    sentiment_data.append(nft_data)

            if sentiment_data:
                composite_score = self._calculate_crypto_composite_score(sentiment_data)
                self._safe_log("info", f"成功获取 {len(sentiment_data)} 项加密货币情绪数据")

                return SentimentResponse(
                    success=True,
                    data=sentiment_data,
                    composite_score=composite_score,
                    data_quality="simulated",  # 基于模拟数据
                    update_time=datetime.now()
                )
            else:
                return SentimentResponse(
                    success=False,
                    data=[],
                    composite_score=50.0,
                    error_message="未获取到加密货币情绪数据",
                    data_quality="unavailable",
                    update_time=datetime.now()
                )

        except Exception as e:
            self._safe_log("error", f"加密货币情绪数据获取失败: {str(e)}")
            return SentimentResponse(
                success=False,
                data=[],
                composite_score=50.0,
                error_message=f"加密货币情绪数据获取失败: {str(e)}",
                data_quality="error",
                update_time=datetime.now()
            )

    def _fetch_fear_greed_data(self) -> Optional[SentimentData]:
        """获取Fear & Greed指数数据"""
        try:
            # 生成模拟Fear & Greed指数 (0-100)
            fear_greed_index = np.random.normal(50, 20)
            fear_greed_index = max(0, min(100, fear_greed_index))

            # 应用平滑处理
            smoothing = self.get_config("sentiment_smoothing", 0.2)
            if smoothing > 0:
                # 模拟历史平滑
                historical_avg = np.random.normal(50, 15)
                fear_greed_index = fear_greed_index * (1 - smoothing) + historical_avg * smoothing
                fear_greed_index = max(0, min(100, fear_greed_index))

            # 获取状态和信号
            status = self._get_fear_greed_status(fear_greed_index)
            signal = self._get_fear_greed_signal(fear_greed_index)

            return SentimentData(
                indicator_name="加密货币Fear&Greed指数",
                value=round(fear_greed_index, 2),
                status=status,
                change=round(np.random.normal(0, 3), 2),
                signal=signal,
                suggestion=f"加密市场{status}(F&G={fear_greed_index:.0f})，{signal}",
                timestamp=datetime.now(),
                source="Crypto-Fear&Greed",
                confidence=0.85
            )

        except Exception as e:
            self._safe_log("warning", f"获取Fear & Greed数据失败: {e}")
            return None

    def _fetch_btc_dominance_data(self) -> Optional[SentimentData]:
        """获取比特币主导地位数据"""
        try:
            # 生成模拟比特币主导地位 (通常在40%-70%)
            btc_dominance = np.random.normal(55, 8)
            btc_dominance = max(30, min(80, btc_dominance))

            # 主导地位分析
            if btc_dominance >= 65:
                status = "BTC主导强势"
                signal = "山寨币承压"
                sentiment_score = 45  # BTC强势时整体情绪趋于保守
            elif btc_dominance >= 50:
                status = "BTC主导正常"
                signal = "市场均衡"
                sentiment_score = 55
            else:
                status = "山寨币活跃"
                signal = "风险偏好上升"
                sentiment_score = 65  # 山寨币活跃时风险偏好较高

            return SentimentData(
                indicator_name="比特币主导地位",
                value=round(sentiment_score, 2),
                status=status,
                change=round(np.random.normal(0, 2), 2),
                signal=signal,
                suggestion=f"BTC主导地位{btc_dominance:.1f}%，{status}",
                timestamp=datetime.now(),
                source="Crypto-Dominance",
                confidence=0.75
            )

        except Exception as e:
            self._safe_log("warning", f"获取BTC主导地位数据失败: {e}")
            return None

    def _fetch_crypto_volatility_data(self) -> Optional[SentimentData]:
        """获取加密货币波动率数据"""
        try:
            # 生成模拟波动率数据
            monitored_cryptos = self.get_config("monitored_cryptos", ["BTC", "ETH", "BNB"])

            # 模拟各币种的波动率
            volatilities = {}
            for crypto in monitored_cryptos:
                if crypto == "BTC":
                    vol = np.random.normal(60, 20)  # BTC波动率相对较低
                elif crypto == "ETH":
                    vol = np.random.normal(70, 25)  # ETH波动率中等
                else:
                    vol = np.random.normal(80, 30)  # 其他币种波动率较高

                volatilities[crypto] = max(20, min(200, vol))

            # 计算加权平均波动率
            weights = self._parse_crypto_weights(self.get_config("crypto_weights", ""))
            weighted_volatility = 0
            total_weight = 0

            for crypto, vol in volatilities.items():
                weight = weights.get(crypto, 0.1)
                weighted_volatility += vol * weight
                total_weight += weight

            if total_weight > 0:
                avg_volatility = weighted_volatility / total_weight
            else:
                avg_volatility = np.mean(list(volatilities.values()))

            # 波动率转换为情绪分数
            if avg_volatility <= 40:
                status = "波动极低"
                signal = "市场冷淡"
                sentiment_score = 35
            elif avg_volatility <= 60:
                status = "波动较低"
                signal = "市场平稳"
                sentiment_score = 50
            elif avg_volatility <= 100:
                status = "波动正常"
                signal = "市场活跃"
                sentiment_score = 65
            else:
                status = "波动剧烈"
                signal = "高风险高回报"
                sentiment_score = 80

            return SentimentData(
                indicator_name="加密市场波动率",
                value=round(sentiment_score, 2),
                status=status,
                change=round(np.random.normal(0, 5), 2),
                signal=signal,
                suggestion=f"加密市场平均波动率{avg_volatility:.0f}%，{status}",
                timestamp=datetime.now(),
                source="Crypto-Volatility",
                confidence=0.70
            )

        except Exception as e:
            self._safe_log("warning", f"获取加密货币波动率数据失败: {e}")
            return None

    def _fetch_defi_sentiment_data(self) -> Optional[SentimentData]:
        """获取DeFi市场情绪数据"""
        try:
            # 模拟DeFi指标
            tvl_change = np.random.normal(0, 10)  # TVL变化百分比
            yield_avg = np.random.normal(8, 4)    # 平均收益率
            new_protocols = np.random.poisson(2)  # 新协议数量

            # 综合评分
            defi_score = 50
            defi_score += tvl_change * 2  # TVL变化影响
            defi_score += (yield_avg - 5) * 3  # 收益率影响
            defi_score += new_protocols * 2  # 新协议影响

            defi_score = max(0, min(100, defi_score))

            if defi_score >= 70:
                status = "DeFi繁荣"
                signal = "创新活跃"
            elif defi_score >= 50:
                status = "DeFi稳定"
                signal = "发展正常"
            else:
                status = "DeFi低迷"
                signal = "需要关注"

            return SentimentData(
                indicator_name="DeFi市场情绪",
                value=round(defi_score, 2),
                status=status,
                change=round(tvl_change, 2),
                signal=signal,
                suggestion=f"DeFi生态{status}，TVL变化{tvl_change:+.1f}%",
                timestamp=datetime.now(),
                source="Crypto-DeFi",
                confidence=0.65
            )

        except Exception as e:
            self._safe_log("warning", f"获取DeFi情绪数据失败: {e}")
            return None

    def _fetch_nft_sentiment_data(self) -> Optional[SentimentData]:
        """获取NFT市场情绪数据"""
        try:
            # 模拟NFT指标
            trading_volume_change = np.random.normal(0, 25)  # 交易量变化
            floor_price_change = np.random.normal(0, 15)     # 地板价变化
            new_collections = np.random.poisson(5)           # 新集合数量

            # 综合评分
            nft_score = 50
            nft_score += trading_volume_change * 1.5
            nft_score += floor_price_change * 2
            nft_score += (new_collections - 5) * 2

            nft_score = max(0, min(100, nft_score))

            if nft_score >= 70:
                status = "NFT热潮"
                signal = "投机活跃"
            elif nft_score >= 50:
                status = "NFT正常"
                signal = "稳定发展"
            else:
                status = "NFT冷淡"
                signal = "关注度下降"

            return SentimentData(
                indicator_name="NFT市场情绪",
                value=round(nft_score, 2),
                status=status,
                change=round(trading_volume_change, 2),
                signal=signal,
                suggestion=f"NFT市场{status}，交易量变化{trading_volume_change:+.1f}%",
                timestamp=datetime.now(),
                source="Crypto-NFT",
                confidence=0.60
            )

        except Exception as e:
            self._safe_log("warning", f"获取NFT情绪数据失败: {e}")
            return None

    def _get_fear_greed_status(self, index: float) -> str:
        """根据Fear & Greed指数获取状态"""
        extreme_fear = self.get_config("extreme_fear_threshold", 25)
        fear = self.get_config("fear_threshold", 45)
        greed = self.get_config("greed_threshold", 75)
        extreme_greed = self.get_config("extreme_greed_threshold", 90)

        if index <= extreme_fear:
            return "极度恐惧"
        elif index <= fear:
            return "恐惧"
        elif index < greed:
            return "中性"
        elif index < extreme_greed:
            return "贪婪"
        else:
            return "极度贪婪"

    def _get_fear_greed_signal(self, index: float) -> str:
        """根据Fear & Greed指数获取信号"""
        extreme_fear = self.get_config("extreme_fear_threshold", 25)
        fear = self.get_config("fear_threshold", 45)
        greed = self.get_config("greed_threshold", 75)
        extreme_greed = self.get_config("extreme_greed_threshold", 90)

        if index <= extreme_fear:
            return "抄底机会"
        elif index <= fear:
            return "谨慎买入"
        elif index < greed:
            return "持有观望"
        elif index < extreme_greed:
            return "获利了结"
        else:
            return "高位减仓"

    def _parse_crypto_weights(self, weights_str: str) -> Dict[str, float]:
        """解析加密货币权重配置"""
        weights = {}

        if not weights_str:
            return weights

        for item in weights_str.split(","):
            if ":" in item:
                crypto, weight_str = item.split(":", 1)
                crypto = crypto.strip().upper()
                try:
                    weight = float(weight_str.strip())
                    if 0 <= weight <= 1:
                        weights[crypto] = weight
                    else:
                        raise ValueError(f"权重值必须在0-1之间: {weight}")
                except ValueError as e:
                    raise ValueError(f"无效的权重值 '{weight_str}': {e}")
            else:
                raise ValueError(f"权重格式错误: {item}")

        return weights

    def _calculate_crypto_composite_score(self, sentiment_data: List[SentimentData]) -> float:
        """计算加密货币综合情绪指数"""
        if not sentiment_data:
            return 50.0

        try:
            correlation_adjustment = self.get_config("correlation_adjustment", True)
            traditional_impact = self.get_config("traditional_market_impact", 0.3)

            total_score = 0.0
            total_weight = 0.0

            for data in sentiment_data:
                weight = 1.0
                confidence = data.confidence or 0.7

                # 根据指标类型调整权重
                if "Fear&Greed" in data.indicator_name:
                    weight = 2.0  # 主要指标
                elif "主导地位" in data.indicator_name:
                    weight = 1.5
                elif "波动率" in data.indicator_name:
                    weight = 1.2
                elif "DeFi" in data.indicator_name:
                    weight = self.get_config("defi_sentiment_weight", 0.1) * 10
                elif "NFT" in data.indicator_name:
                    weight = self.get_config("nft_sentiment_weight", 0.05) * 20

                # 相关性调整
                if correlation_adjustment:
                    # 模拟与传统市场的相关性调整
                    correlation_factor = np.random.uniform(0.8, 1.2)
                    weight *= correlation_factor

                # 传统市场影响调整
                if traditional_impact > 0:
                    impact_adjustment = 1 + traditional_impact * np.random.normal(0, 0.1)
                    weight *= impact_adjustment

                adjusted_weight = weight * confidence
                total_score += data.value * adjusted_weight
                total_weight += adjusted_weight

            if total_weight > 0:
                composite_score = total_score / total_weight
            else:
                composite_score = 50.0

            return max(0.0, min(100.0, round(composite_score, 2)))

        except Exception as e:
            self._safe_log("warning", f"计算加密货币综合指数失败: {e}")
            # 使用简单平均作为备选
            avg_score = np.mean([data.value for data in sentiment_data])
            return max(0.0, min(100.0, round(avg_score, 2)))


# 插件工厂函数
def create_crypto_sentiment_plugin() -> CryptoSentimentPlugin:
    """创建加密货币情绪分析插件实例"""
    return CryptoSentimentPlugin()


if __name__ == "__main__":
    # 测试插件
    plugin = create_crypto_sentiment_plugin()

    # 初始化
    plugin.initialize(None)

    # 加载配置
    plugin.load_config()

    # 获取数据
    response = plugin._fetch_raw_sentiment_data()

    print(f"成功: {response.success}")
    print(f"数据项: {len(response.data)}")
    print(f"综合指数: {response.composite_score}")

    if response.data:
        for item in response.data:
            print(f"- {item.indicator_name}: {item.value} ({item.status})")
