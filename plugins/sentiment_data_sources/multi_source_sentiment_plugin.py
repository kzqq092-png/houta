#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源情绪数据插件
支持多种免费/低成本API：
1. Financial Modeling Prep (FMP) - 免费额度
2. Exorde API - 1000免费credits
3. AI Market Mood - 免费使用
4. Alpha Vantage - 新闻情绪
"""

import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from plugins.plugin_interface import PluginType, PluginCategory, PluginMetadata
from .base_sentiment_plugin import BaseSentimentPlugin
from plugins.sentiment_data_source_interface import SentimentData, SentimentResponse


class MultiSourceSentimentPlugin(BaseSentimentPlugin):
    """多源情绪数据插件"""

    def __init__(self):
        super().__init__()
        # API配置
        self.api_keys = {
            'fmp': '',  # Financial Modeling Prep
            'exorde': '',  # Exorde API
            'alpha_vantage': '',  # Alpha Vantage
        }
        self.api_configs = {
            'fmp': {
                'base_url': 'https://financialmodelingprep.com/api',
                'free_limit': 250,  # 每日免费请求数
                'endpoints': {
                    'social_sentiment': '/v4/historical/social-sentiment',
                    'news_sentiment': '/v4/stock-news-sentiments-rss-feed',
                    'trending': '/v4/social-sentiments/trending'
                }
            },
            'exorde': {
                'base_url': 'https://api.exorde.io',
                'free_credits': 1000,
                'endpoints': {
                    'sentiment': '/sentiment',
                    'emotions': '/emotions',
                    'volume': '/volume'
                }
            }
        }

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="多源情绪数据插件",
            version="1.0.0",
            author="HIkyuu-UI Team",
            email="support@hikyuu.com",
            website="https://github.com/hikyuu/hikyuu-ui",
            license="MIT",
            description="集成多种免费情绪分析API：FMP、Exorde、AI Market Mood等，提供全面的市场情绪数据",
            plugin_type=PluginType.DATA_SOURCE,
            category=PluginCategory.CORE,
            dependencies=["requests>=2.25.0", "pandas>=1.3.0", "numpy>=1.20.0"],
            min_hikyuu_version="1.0.0",
            max_hikyuu_version="2.0.0",
            documentation_url="https://site.financialmodelingprep.com/developer/docs",
            tags=["sentiment", "emotion", "multi-source", "fmp", "exorde", "free"]
        )

    def _fetch_raw_sentiment_data(self, **kwargs) -> SentimentResponse:
        """获取原始情绪数据"""
        try:
            # 此插件使用模拟数据，已被禁用
            return SentimentResponse(
                success=False,
                data=[],
                composite_score=50.0,
                error_message="多源情绪插件已禁用，请使用专门的数据源插件（如FMP、VIX等）",
                data_quality="unavailable",
                update_time=datetime.now()
            )
        except Exception as e:
            self._safe_log("error", f"多源情绪数据获取失败: {e}")
            return SentimentResponse(
                success=False,
                data=[],
                composite_score=50.0,
                error_message=f"数据获取异常: {str(e)}",
                data_quality="error",
                update_time=datetime.now()
            )

    def _fetch_fmp_sentiment(self) -> List[SentimentData]:
        """获取FMP社交情绪数据"""
        try:
            # 使用免费API（无需API key）
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
            sentiment_data = []

            for symbol in symbols[:2]:  # 限制请求数量
                try:
                    # 模拟FMP社交情绪数据（实际使用时需要API key）
                    sentiment_score = np.random.normal(60, 15)
                    sentiment_score = max(0, min(100, sentiment_score))

                    bullish_percent = np.random.uniform(40, 80)
                    bearish_percent = 100 - bullish_percent

                    if sentiment_score >= 70:
                        status = "强烈看多"
                        signal = "买入"
                    elif sentiment_score >= 55:
                        status = "轻微看多"
                        signal = "持有"
                    elif sentiment_score >= 45:
                        status = "中性"
                        signal = "观望"
                    else:
                        status = "看空"
                        signal = "减仓"

                    sentiment_data.append(SentimentData(
                        indicator_name=f"{symbol}社交情绪",
                        value=round(sentiment_score, 2),
                        status=status,
                        change=round(np.random.normal(0, 3), 2),
                        signal=signal,
                        suggestion=f"{symbol}社交媒体情绪{status}，看多{bullish_percent:.1f}%",
                        timestamp=datetime.now(),
                        source="FMP-社交",
                        confidence=0.80
                    ))

                except Exception as e:
                    self._safe_log("warning", f"获取{symbol}FMP数据失败: {e}")
                    continue

            return sentiment_data

        except Exception as e:
            self._safe_log("warning", f"获取FMP情绪数据失败: {e}")
            return []

    def _fetch_exorde_sentiment(self) -> List[SentimentData]:
        """获取Exorde情绪数据"""
        try:
            # 模拟Exorde 27种情绪分析
            emotions = ['love', 'joy', 'optimism', 'fear', 'anger', 'sadness', 'trust']
            sentiment_data = []

            # 生成综合情绪指数
            composite_emotions = {}
            for emotion in emotions:
                composite_emotions[emotion] = np.random.uniform(0, 1)

            # 计算主导情绪
            dominant_emotion = max(composite_emotions, key=composite_emotions.get)
            emotion_score = composite_emotions[dominant_emotion] * 100

            # 情绪到投资信号的映射
            emotion_map = {
                'love': ('极度乐观', '强烈买入'),
                'joy': ('乐观', '买入'),
                'optimism': ('看好', '逢低买入'),
                'trust': ('信任', '持有'),
                'fear': ('恐慌', '谨慎'),
                'anger': ('愤怒', '观望'),
                'sadness': ('悲观', '减仓')
            }

            status, signal = emotion_map.get(dominant_emotion, ('中性', '观望'))

            sentiment_data.append(SentimentData(
                indicator_name="市场情绪光谱",
                value=round(emotion_score, 2),
                status=f"{status}({dominant_emotion})",
                change=round(np.random.normal(0, 2), 2),
                signal=signal,
                suggestion=f"市场主导情绪为{dominant_emotion}({emotion_score:.1f}%)，建议{signal}",
                timestamp=datetime.now(),
                source="Exorde-27情绪",
                confidence=0.75
            ))

            return sentiment_data

        except Exception as e:
            self._safe_log("warning", f"获取Exorde情绪数据失败: {e}")
            return []

    def _fetch_news_sentiment(self) -> List[SentimentData]:
        """获取新闻情绪分析"""
        try:
            # 模拟新闻情绪分析
            news_sources = ["财经新闻", "分析师报告", "公司公告"]
            sentiment_data = []

            for source in news_sources:
                sentiment_score = np.random.normal(52, 12)
                sentiment_score = max(0, min(100, sentiment_score))

                if sentiment_score >= 70:
                    status = "积极正面"
                    signal = "利好"
                elif sentiment_score >= 55:
                    status = "温和正面"
                    signal = "轻微利好"
                elif sentiment_score >= 45:
                    status = "中性"
                    signal = "无明显影响"
                else:
                    status = "负面"
                    signal = "利空"

                sentiment_data.append(SentimentData(
                    indicator_name=f"{source}情绪",
                    value=round(sentiment_score, 2),
                    status=status,
                    change=round(np.random.normal(0, 2.5), 2),
                    signal=signal,
                    suggestion=f"{source}情绪{status}，{signal}信号",
                    timestamp=datetime.now(),
                    source=f"新闻-{source}",
                    confidence=0.70
                ))

            return sentiment_data

        except Exception as e:
            self._safe_log("warning", f"获取新闻情绪数据失败: {e}")
            return []

    def _fetch_vix_simulation(self) -> Optional[SentimentData]:
        """获取VIX恐慌指数模拟"""
        try:
            # 模拟VIX指数
            vix_value = np.random.normal(18, 6)
            vix_value = max(5, min(80, vix_value))

            if vix_value <= 12:
                status = "极度平静"
                signal = "高风险偏好"
                fear_level = "极低"
            elif vix_value <= 20:
                status = "相对平静"
                signal = "正常交易"
                fear_level = "低"
            elif vix_value <= 30:
                status = "适度紧张"
                signal = "谨慎交易"
                fear_level = "中等"
            elif vix_value <= 40:
                status = "高度恐慌"
                signal = "防御为主"
                fear_level = "高"
            else:
                status = "极度恐慌"
                signal = "现金为王"
                fear_level = "极高"

            return SentimentData(
                indicator_name="市场恐慌指数",
                value=round(vix_value, 2),
                status=status,
                change=round(np.random.normal(0, 1.5), 2),
                signal=signal,
                suggestion=f"恐慌程度{fear_level}(VIX={vix_value:.1f})，{signal}",
                timestamp=datetime.now(),
                source="VIX-模拟",
                confidence=0.85
            )

        except Exception as e:
            self._safe_log("warning", f"获取VIX模拟数据失败: {e}")
            return None

    def _fetch_crypto_sentiment(self) -> Optional[SentimentData]:
        """获取加密货币情绪"""
        try:
            # 模拟加密货币市场情绪（影响股市）
            crypto_fear_greed = np.random.randint(0, 100)

            if crypto_fear_greed >= 75:
                status = "极度贪婪"
                signal = "泡沫风险"
                impact = "可能拖累科技股"
            elif crypto_fear_greed >= 55:
                status = "贪婪"
                signal = "风险偏好高"
                impact = "利好科技股"
            elif crypto_fear_greed >= 45:
                status = "中性"
                signal = "正常状态"
                impact = "对股市影响有限"
            elif crypto_fear_greed >= 25:
                status = "恐惧"
                signal = "避险情绪"
                impact = "资金流入传统资产"
            else:
                status = "极度恐惧"
                signal = "恐慌抛售"
                impact = "可能拖累整体市场"

            return SentimentData(
                indicator_name="加密市场情绪",
                value=round(crypto_fear_greed, 2),
                status=status,
                change=round(np.random.normal(0, 8), 2),
                signal=signal,
                suggestion=f"加密市场{status}({crypto_fear_greed})，{impact}",
                timestamp=datetime.now(),
                source="Crypto-Fear&Greed",
                confidence=0.65
            )

        except Exception as e:
            self._safe_log("warning", f"获取加密货币情绪失败: {e}")
            return None

    def _calculate_composite_score(self, sentiment_data: List[SentimentData]) -> float:
        """计算多源综合情绪指数"""
        if not sentiment_data:
            return 50.0

        total_weighted_score = 0.0
        total_weight = 0.0

        # 多源权重设定
        source_weights = {
            "FMP-社交": 0.25,
            "Exorde-27情绪": 0.20,
            "新闻-财经新闻": 0.15,
            "新闻-分析师报告": 0.15,
            "新闻-公司公告": 0.10,
            "VIX-模拟": 0.20,  # VIX需要反向处理
            "Crypto-Fear&Greed": 0.10
        }

        for data in sentiment_data:
            # 从source中提取权重key
            weight_key = next((key for key in source_weights.keys()
                               if key in data.source), "default")
            weight = source_weights.get(weight_key, 0.05)

            confidence = data.confidence if data.confidence else 0.5
            adjusted_weight = weight * confidence

            # VIX反向处理
            if "VIX" in data.source:
                # VIX越低，情绪越乐观
                if data.value <= 15:
                    sentiment_score = 80
                elif data.value <= 25:
                    sentiment_score = 60
                elif data.value <= 35:
                    sentiment_score = 40
                else:
                    sentiment_score = 20
            else:
                sentiment_score = data.value

            total_weighted_score += sentiment_score * adjusted_weight
            total_weight += adjusted_weight

        if total_weight > 0:
            composite_score = total_weighted_score / total_weight
        else:
            composite_score = 50.0

        return max(0.0, min(100.0, round(composite_score, 2)))

    def get_api_usage_info(self) -> Dict[str, Any]:
        """获取API使用情况信息"""
        return {
            "apis_available": [
                {
                    "name": "Financial Modeling Prep",
                    "free_tier": "250 requests/day",
                    "features": ["社交情绪", "新闻情绪", "趋势分析"],
                    "cost": "免费使用"
                },
                {
                    "name": "Exorde API",
                    "free_tier": "1000 credits",
                    "features": ["27种情绪分析", "社交监听", "趋势检测"],
                    "cost": "$20/月起"
                },
                {
                    "name": "AI Market Mood",
                    "free_tier": "基础使用免费",
                    "features": ["新闻聚合", "情绪分析", "市场预测"],
                    "cost": "免费 + 付费升级"
                }
            ],
            "recommendation": "建议组合使用多个免费额度，获得更全面的情绪数据"
        }

    def get_available_indicators(self) -> List[str]:
        """获取可用的情绪指标列表"""
        return [
            "FMP社交情绪",
            "市场情绪光谱",
            "财经新闻情绪",
            "分析师报告情绪",
            "公司公告情绪",
            "市场恐慌指数",
            "加密市场情绪"
        ]


# 插件工厂函数
def create_multi_source_sentiment_plugin() -> MultiSourceSentimentPlugin:
    """创建多源情绪数据插件实例"""
    return MultiSourceSentimentPlugin()


if __name__ == "__main__":
    # 测试插件
    plugin = create_multi_source_sentiment_plugin()

    # 初始化
    plugin.initialize(None)

    # 获取数据
    response = plugin._fetch_raw_sentiment_data()

    print(f"成功: {response.success}")
    print(f"数据项: {len(response.data)}")
    print(f"综合指数: {response.composite_score}")

    if response.data:
        for item in response.data:
            print(f"- {item.indicator_name}: {item.value} ({item.status})")

    # API使用信息
    usage_info = plugin.get_api_usage_info()
    print(f"\nAPI信息: {json.dumps(usage_info, indent=2, ensure_ascii=False)}")
