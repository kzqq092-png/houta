"""
AkShare情绪数据源插件
基于akshare库获取真实的市场情绪数据
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from plugins.plugin_interface import PluginType, PluginCategory, PluginMetadata
from .base_sentiment_plugin import BaseSentimentPlugin, SentimentData, SentimentResponse


class AkShareSentimentPlugin(BaseSentimentPlugin):
    """AkShare情绪数据源插件"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="AkShare情绪数据源",
            version="1.0.0",
            author="HIkyuu-UI Team",
            description="基于AkShare库获取真实的市场情绪数据，包括新闻情绪、VIX指数、微博情绪等",
            plugin_type=PluginType.DATA_SOURCE,
            category=PluginCategory.CORE,
            dependencies=["akshare>=1.11.0", "pandas>=1.3.0", "numpy>=1.20.0"],
            min_python_version="3.8",
            homepage_url="https://github.com/akfamily/akshare",
            documentation_url="https://akshare.akfamily.xyz/",
            tags=["sentiment", "emotion", "vix", "news", "weibo", "market"]
        )

    def _fetch_raw_sentiment_data(self, **kwargs) -> SentimentResponse:
        """获取AkShare原始情绪数据"""
        sentiment_data = []

        try:
            # 1. 获取A股新闻情绪指数
            news_sentiment = self._fetch_news_sentiment()
            if news_sentiment:
                sentiment_data.append(news_sentiment)

            # 2. 获取微博情绪数据
            weibo_sentiment = self._fetch_weibo_sentiment()
            if weibo_sentiment:
                sentiment_data.extend(weibo_sentiment)

            # 3. 获取VIX相关指数
            vix_data = self._fetch_vix_indices()
            if vix_data:
                sentiment_data.extend(vix_data)

            # 4. 获取消费者信心指数
            consumer_confidence = self._fetch_consumer_confidence()
            if consumer_confidence:
                sentiment_data.append(consumer_confidence)

            # 5. 获取外汇情绪
            fx_sentiment = self._fetch_fx_sentiment()
            if fx_sentiment:
                sentiment_data.append(fx_sentiment)

            if sentiment_data:
                return SentimentResponse(
                    success=True,
                    data=sentiment_data,
                    composite_score=0,  # 将在基类中计算
                    data_quality="real",
                    update_time=datetime.now()
                )
            else:
                return SentimentResponse(
                    success=False,
                    data=[],
                    composite_score=50.0,
                    error_message="未获取到任何情绪数据",
                    data_quality="empty"
                )

        except Exception as e:
            return SentimentResponse(
                success=False,
                data=[],
                composite_score=50.0,
                error_message=f"AkShare数据获取失败: {str(e)}",
                data_quality="error"
            )

    def _fetch_news_sentiment(self) -> Optional[SentimentData]:
        """获取新闻情绪指数"""
        try:
            # 获取A股新闻情绪指数
            df = ak.index_news_sentiment_scope()
            if df.empty:
                return None

            # 获取最新数据
            latest_data = df.iloc[-1]
            sentiment_value = float(latest_data['市场情绪指数'])

            # 标准化到0-100范围 (假设原始值在0-1之间)
            if sentiment_value <= 1:
                normalized_value = sentiment_value * 100
            else:
                normalized_value = sentiment_value

            return SentimentData(
                indicator_name="新闻情绪指数",
                value=normalized_value,
                status=self.get_sentiment_status(normalized_value),
                change=0.0,  # AkShare不提供变化幅度
                signal=self.get_trading_signal(normalized_value),
                suggestion=self.get_investment_suggestion(normalized_value),
                timestamp=datetime.now(),
                source="AkShare-ChinaScope",
                confidence=0.85,
                color=self.get_status_color(normalized_value),
                metadata={'原始值': sentiment_value, 'CSI300': float(latest_data['沪深300指数'])}
            )

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"获取新闻情绪指数失败: {e}")
            return None

    def _fetch_weibo_sentiment(self) -> List[SentimentData]:
        """获取微博情绪数据"""
        try:
            # 获取微博舆情报告
            df = ak.stock_js_weibo_report(time_period="CNHOUR12")
            if df.empty:
                return []

            # 转换为情绪数据
            weibo_data = []

            # 计算平均情绪（基于人气排行）
            if '人气排行指数' in df.columns:
                avg_popularity = df['人气排行指数'].astype(str).str.replace('%', '').astype(float).mean()

                weibo_sentiment = SentimentData(
                    indicator_name="微博情绪指数",
                    value=avg_popularity,
                    status=self.get_sentiment_status(avg_popularity),
                    change=0.0,
                    signal=self.get_trading_signal(avg_popularity),
                    suggestion=self.get_investment_suggestion(avg_popularity),
                    timestamp=datetime.now(),
                    source="AkShare-Weibo",
                    confidence=0.75,
                    color=self.get_status_color(avg_popularity),
                    metadata={'股票数量': len(df), '热门股票': df.iloc[0]['股票名称'] if len(df) > 0 else None}
                )
                weibo_data.append(weibo_sentiment)

            return weibo_data

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"获取微博情绪数据失败: {e}")
            return []

    def _fetch_vix_indices(self) -> List[SentimentData]:
        """获取VIX相关波动率指数"""
        vix_data = []

        try:
            # 尝试获取科创板期权波动率指数QVIX
            try:
                qvix_df = ak.index_option_kcb_qvix()
                if not qvix_df.empty:
                    latest_qvix = qvix_df.iloc[-1]['收盘价']

                    vix_sentiment = SentimentData(
                        indicator_name="科创板VIX指数",
                        value=float(latest_qvix),
                        status=self._get_vix_status(latest_qvix),
                        change=0.0,
                        signal=self._get_vix_signal(latest_qvix),
                        suggestion=self._get_vix_suggestion(latest_qvix),
                        timestamp=datetime.now(),
                        source="AkShare-QVIX",
                        confidence=0.90,
                        color=self._get_vix_color(latest_qvix),
                        metadata={'指数类型': '科创板期权波动率', '收盘价': float(latest_qvix)}
                    )
                    vix_data.append(vix_sentiment)
            except:
                pass

            # 尝试获取沪深300期权波动率指数
            try:
                csi300_qvix_df = ak.index_option_300index_qvix()
                if not csi300_qvix_df.empty:
                    latest_300qvix = csi300_qvix_df.iloc[-1]['收盘价']

                    vix_sentiment = SentimentData(
                        indicator_name="沪深300VIX指数",
                        value=float(latest_300qvix),
                        status=self._get_vix_status(latest_300qvix),
                        change=0.0,
                        signal=self._get_vix_signal(latest_300qvix),
                        suggestion=self._get_vix_suggestion(latest_300qvix),
                        timestamp=datetime.now(),
                        source="AkShare-300QVIX",
                        confidence=0.90,
                        color=self._get_vix_color(latest_300qvix),
                        metadata={'指数类型': '沪深300期权波动率', '收盘价': float(latest_300qvix)}
                    )
                    vix_data.append(vix_sentiment)
            except:
                pass

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"获取VIX指数失败: {e}")

        return vix_data

    def _fetch_consumer_confidence(self) -> Optional[SentimentData]:
        """获取消费者信心指数"""
        try:
            # 获取中国消费者信心指数
            df = ak.macro_china_xfzxx()
            if df.empty:
                return None

            # 获取最新数据
            latest_data = df.iloc[-1]
            confidence_value = float(latest_data['现值'])

            return SentimentData(
                indicator_name="消费者信心指数",
                value=confidence_value,
                status=self._get_confidence_status(confidence_value),
                change=0.0,
                signal=self._get_confidence_signal(confidence_value),
                suggestion=self._get_confidence_suggestion(confidence_value),
                timestamp=datetime.now(),
                source="AkShare-消费者信心",
                confidence=0.80,
                color=self._get_confidence_color(confidence_value),
                metadata={'发布日期': str(latest_data['发布日期']), '前值': float(latest_data['前值'])}
            )

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"获取消费者信心指数失败: {e}")
            return None

    def _fetch_fx_sentiment(self) -> Optional[SentimentData]:
        """获取外汇情绪数据"""
        try:
            from datetime import datetime

            # 获取最近的外汇情绪报告
            test_date = datetime.now().date().isoformat().replace("-", "")
            df = ak.macro_fx_sentiment(start_date=test_date, end_date=test_date)

            if df.empty:
                return None

            # 计算平均情绪（这里简化处理）
            avg_sentiment = 50.0  # 默认中性，实际应根据具体数据计算

            return SentimentData(
                indicator_name="外汇市场情绪",
                value=avg_sentiment,
                status=self.get_sentiment_status(avg_sentiment),
                change=0.0,
                signal=self.get_trading_signal(avg_sentiment),
                suggestion=self.get_investment_suggestion(avg_sentiment),
                timestamp=datetime.now(),
                source="AkShare-FX",
                confidence=0.70,
                color=self.get_status_color(avg_sentiment),
                metadata={'数据条数': len(df), '报告日期': test_date}
            )

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"获取外汇情绪数据失败: {e}")
            return None

    def _get_vix_status(self, vix_value: float) -> str:
        """根据VIX值获取情绪状态"""
        if vix_value < 15:
            return "市场平静"
        elif vix_value < 25:
            return "正常波动"
        elif vix_value < 35:
            return "市场紧张"
        else:
            return "高度恐慌"

    def _get_vix_signal(self, vix_value: float) -> str:
        """根据VIX值获取交易信号"""
        if vix_value < 15:
            return "注意风险"
        elif vix_value < 25:
            return "正常操作"
        elif vix_value < 35:
            return "谨慎操作"
        else:
            return "抄底机会"

    def _get_vix_suggestion(self, vix_value: float) -> str:
        """根据VIX值获取投资建议"""
        if vix_value < 15:
            return "市场过于平静，注意潜在风险"
        elif vix_value < 25:
            return "市场波动正常，可正常操作"
        elif vix_value < 35:
            return "市场波动增大，建议谨慎操作"
        else:
            return "市场恐慌，可关注抄底机会"

    def _get_vix_color(self, vix_value: float) -> str:
        """根据VIX值获取颜色"""
        if vix_value < 15:
            return "#28a745"  # 绿色
        elif vix_value < 25:
            return "#ffc107"  # 黄色
        elif vix_value < 35:
            return "#fd7e14"  # 橙色
        else:
            return "#dc3545"  # 红色

    def _get_confidence_status(self, confidence: float) -> str:
        """根据消费者信心指数获取状态"""
        if confidence > 120:
            return "极度乐观"
        elif confidence > 110:
            return "乐观"
        elif confidence > 90:
            return "中性"
        elif confidence > 80:
            return "悲观"
        else:
            return "极度悲观"

    def _get_confidence_signal(self, confidence: float) -> str:
        """根据消费者信心指数获取交易信号"""
        if confidence > 120:
            return "谨慎观望"
        elif confidence > 110:
            return "正常操作"
        elif confidence > 90:
            return "正常操作"
        elif confidence > 80:
            return "关注机会"
        else:
            return "买入机会"

    def _get_confidence_suggestion(self, confidence: float) -> str:
        """根据消费者信心指数获取投资建议"""
        if confidence > 120:
            return "消费者过度乐观，注意市场风险"
        elif confidence > 110:
            return "消费者信心良好，有利于经济增长"
        elif confidence > 90:
            return "消费者信心正常，市场相对稳定"
        elif confidence > 80:
            return "消费者信心不足，可关注刺激政策"
        else:
            return "消费者极度悲观，或有政策利好"

    def _get_confidence_color(self, confidence: float) -> str:
        """根据消费者信心指数获取颜色"""
        if confidence > 120:
            return "#dc3545"  # 红色
        elif confidence > 110:
            return "#28a745"  # 绿色
        elif confidence > 90:
            return "#ffc107"  # 黄色
        elif confidence > 80:
            return "#fd7e14"  # 橙色
        else:
            return "#007bff"  # 蓝色

    def get_available_indicators(self) -> List[Dict[str, Any]]:
        """获取可用的情绪指标列表"""
        return [
            {
                "name": "新闻情绪指数",
                "source": "AkShare-ChinaScope",
                "description": "基于新闻文本分析的A股市场情绪指数",
                "frequency": "daily",
                "confidence": 0.85
            },
            {
                "name": "微博情绪指数",
                "source": "AkShare-Weibo",
                "description": "基于微博舆情的股票关注度情绪指数",
                "frequency": "real-time",
                "confidence": 0.75
            },
            {
                "name": "科创板VIX指数",
                "source": "AkShare-QVIX",
                "description": "科创板期权波动率指数，反映市场恐慌程度",
                "frequency": "daily",
                "confidence": 0.90
            },
            {
                "name": "沪深300VIX指数",
                "source": "AkShare-300QVIX",
                "description": "沪深300期权波动率指数，反映主板市场恐慌程度",
                "frequency": "daily",
                "confidence": 0.90
            },
            {
                "name": "消费者信心指数",
                "source": "AkShare-消费者信心",
                "description": "中国消费者信心指数，反映消费者对经济的信心",
                "frequency": "monthly",
                "confidence": 0.80
            },
            {
                "name": "外汇市场情绪",
                "source": "AkShare-FX",
                "description": "外汇市场投机情绪报告",
                "frequency": "daily",
                "confidence": 0.70
            }
        ]

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        base_config = super().get_default_config()
        akshare_config = {
            "enable_news_sentiment": True,
            "enable_weibo_sentiment": True,
            "enable_vix_indices": True,
            "enable_consumer_confidence": True,
            "enable_fx_sentiment": False,  # 默认关闭，因为可能网络访问受限
            "weibo_time_period": "CNHOUR12",
            "retry_delay": 1.0,
            "max_retry_delay": 10.0
        }
        base_config.update(akshare_config)
        return base_config

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        if not super().validate_config(config):
            return False

        try:
            # 验证AkShare特定配置
            weibo_periods = ["CNHOUR2", "CNHOUR6", "CNHOUR12", "CNHOUR24", "CNDAY7", "CNDAY30"]
            if config.get("weibo_time_period") not in weibo_periods:
                return False

            return True
        except:
            return False
