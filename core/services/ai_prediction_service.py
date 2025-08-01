#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI预测服务 - 统一的机器学习预测服务

提供：
1. 形态预测
2. 趋势预测  
3. 情绪预测
4. 价格预测
5. 风险预测
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import pickle
import os
import hashlib
from pathlib import Path

# 尝试导入深度学习模块
try:
    from models.deep_learning import build_deep_learning_model, TENSORFLOW_AVAILABLE
    from models.model_evaluation import evaluate_ml_model
    DL_AVAILABLE = True
except ImportError:
    DL_AVAILABLE = False
    TENSORFLOW_AVAILABLE = False

from core.services.base_service import BaseService

logger = logging.getLogger(__name__)


class AIModelType:
    """AI模型类型"""
    DEEP_LEARNING = "deep_learning"
    ENSEMBLE = "ensemble"
    STATISTICAL = "statistical"
    RULE_BASED = "rule_based"


class PredictionType:
    """预测类型"""
    PATTERN = "pattern"      # 形态预测
    TREND = "trend"         # 趋势预测
    SENTIMENT = "sentiment"  # 情绪预测
    PRICE = "price"         # 价格预测
    RISK = "risk"           # 风险预测


class AIPredictionService(BaseService):
    """AI预测服务"""

    def __init__(self):
        """初始化AI预测服务"""
        super().__init__()

        # 从数据库加载配置
        self._load_config_from_database()

        # 模型缓存
        self._models = {}
        self._predictions_cache = {}
        self._last_update = {}

        # 初始化模型
        self._initialize_models()

    def _load_config_from_database(self):
        """从数据库加载配置"""
        try:
            from db.models.ai_config_models import get_ai_config_manager
            config_manager = get_ai_config_manager()

            # 加载各种配置
            self.model_config = config_manager.get_config('model_config') or {
                'enabled': True,
                'model_type': AIModelType.ENSEMBLE,
                'confidence_threshold': 0.7,
                'prediction_horizon': 5,
                'feature_window': 20,
                'cache_size': 1000,
                'model_update_interval': 24
            }

            self.validation_config = config_manager.get_config('validation') or {
                'min_data_points': 10,
                'max_prediction_horizon': 30,
                'max_data_rows': 10000,
                'required_columns': ['open', 'high', 'low', 'close']
            }

            self.feature_config = config_manager.get_config('feature_config') or {
                'technical_indicators': True,
                'pattern_features': True,
                'volume_features': True,
                'price_features': True,
                'volatility_features': True
            }

            self.cache_config = config_manager.get_config('cache_config') or {
                'enable_cache': True,
                'cache_ttl': 300,
                'max_cache_size': 1000
            }

            self.logging_config = config_manager.get_config('logging') or {
                'log_predictions': True,
                'log_level': 'INFO',
                'detailed_errors': True
            }

            logger.info("✅ AI预测配置已从数据库加载")

        except Exception as e:
            logger.warning(f"从数据库加载配置失败，使用默认配置: {e}")
            # 使用默认配置
            self.model_config = {
                'enabled': True,
                'model_type': AIModelType.ENSEMBLE,
                'confidence_threshold': 0.7,
                'prediction_horizon': 5,
                'feature_window': 20,
                'cache_size': 1000,
                'model_update_interval': 24
            }

            self.validation_config = {
                'min_data_points': 10,
                'max_prediction_horizon': 30,
                'max_data_rows': 10000,
                'required_columns': ['open', 'high', 'low', 'close']
            }

            self.feature_config = {
                'technical_indicators': True,
                'pattern_features': True,
                'volume_features': True,
                'price_features': True,
                'volatility_features': True
            }

            self.cache_config = {
                'enable_cache': True,
                'cache_ttl': 300,
                'max_cache_size': 1000
            }

            self.logging_config = {
                'log_predictions': True,
                'log_level': 'INFO',
                'detailed_errors': True
            }

    def _validate_kdata(self, kdata: pd.DataFrame) -> bool:
        """
        验证K线数据格式和内容

        Args:
            kdata: K线数据DataFrame

        Returns:
            验证是否通过

        Raises:
            ValueError: 数据格式错误
            TypeError: 数据类型错误
        """
        required_columns = ['open', 'high', 'low', 'close']

        # 检查基础格式
        if kdata is None or kdata.empty:
            logger.warning("K线数据为空")
            return False

        # 检查必需列
        missing_columns = [col for col in required_columns if col not in kdata.columns]
        if missing_columns:
            raise ValueError(f"K线数据缺少必需列: {missing_columns}")

        # 检查数据类型
        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(kdata[col]):
                raise TypeError(f"列 {col} 必须是数值类型，当前类型: {kdata[col].dtype}")

        # 检查空值
        null_counts = kdata[required_columns].isnull().sum()
        if null_counts.any():
            logger.warning(f"K线数据包含空值: {null_counts[null_counts > 0].to_dict()}")

        # 检查数据合理性
        invalid_high_low = (kdata['high'] < kdata['low']).sum()
        if invalid_high_low > 0:
            raise ValueError(f"发现 {invalid_high_low} 条记录的高价低于低价")

        # 检查数据范围合理性
        for col in required_columns:
            if (kdata[col] <= 0).any():
                raise ValueError(f"列 {col} 包含非正数值")

        # 检查数据大小限制
        max_rows = 10000  # 限制最大行数
        if len(kdata) > max_rows:
            logger.warning(f"数据行数({len(kdata)})超过建议最大值({max_rows})")

        return True

    def _generate_cache_key(self, kdata: pd.DataFrame, method: str, **kwargs) -> str:
        """
        生成安全的缓存键

        Args:
            kdata: K线数据
            method: 方法名称
            **kwargs: 额外参数

        Returns:
            缓存键字符串
        """
        try:
            # 基础信息
            basic_info = f"{method}_{kdata.shape[0]}_{kdata.shape[1]}"

            # 时间范围信息
            if hasattr(kdata.index, 'min') and hasattr(kdata.index, 'max'):
                try:
                    time_info = f"_{kdata.index.min()}_{kdata.index.max()}"
                except Exception:
                    time_info = f"_{len(kdata)}"
            else:
                time_info = f"_{len(kdata)}"

            # 数据内容摘要
            if len(kdata) > 0:
                try:
                    first_row_sum = float(kdata.iloc[0][['open', 'high', 'low', 'close']].sum())
                    last_row_sum = float(kdata.iloc[-1][['open', 'high', 'low', 'close']].sum())
                    content_info = f"_{first_row_sum:.2f}_{last_row_sum:.2f}"
                except Exception:
                    content_info = "_default"
            else:
                content_info = "_empty"

            # 额外参数
            kwargs_str = "_".join(f"{k}_{v}" for k, v in sorted(kwargs.items()))
            if kwargs_str:
                kwargs_str = f"_{kwargs_str}"

            # 生成最终的缓存键
            cache_content = f"{basic_info}{time_info}{content_info}{kwargs_str}"
            cache_key = hashlib.md5(cache_content.encode('utf-8')).hexdigest()[:16]

            return f"{method}_{cache_key}"

        except Exception as e:
            logger.warning(f"生成缓存键失败: {e}，使用默认键")
            return f"{method}_default_{datetime.now().timestamp()}"

    def _initialize_models(self):
        """初始化预测模型"""
        try:
            # 加载预训练模型或创建新模型
            model_dir = Path("models/trained")
            model_dir.mkdir(exist_ok=True)

            if DL_AVAILABLE:
                logger.info("✅ 深度学习模块可用，初始化AI预测模型")
                self._load_or_create_models()
            else:
                logger.warning("⚠️ 深度学习模块不可用，使用统计模型")
                self._initialize_statistical_models()

        except Exception as e:
            logger.error(f"❌ 模型初始化失败: {e}")
            self._initialize_fallback_models()

    def _load_or_create_models(self):
        """加载或创建深度学习模型"""
        for pred_type in [PredictionType.PATTERN, PredictionType.TREND,
                          PredictionType.SENTIMENT, PredictionType.PRICE]:
            model_path = Path(f"models/trained/{pred_type}_model.h5")
            if model_path.exists():
                try:
                    # 尝试加载TensorFlow模型
                    if TENSORFLOW_AVAILABLE:
                        import tensorflow as tf

                        # 验证模型文件
                        if model_path.stat().st_size == 0:
                            logger.warning(f"{pred_type}模型文件为空")
                            self._models[pred_type] = None
                            continue

                        # 加载模型并验证
                        model = tf.keras.models.load_model(str(model_path))

                        # 基础模型验证
                        if not hasattr(model, 'predict'):
                            logger.warning(f"{pred_type}模型缺少predict方法")
                            self._models[pred_type] = None
                            continue

                        self._models[pred_type] = model
                        logger.info(f"✅ 加载{pred_type}深度学习模型成功")
                    else:
                        # 如果没有TensorFlow，检查是否是简化模型
                        try:
                            import json
                            with open(model_path, 'r', encoding='utf-8') as f:
                                model_data = json.load(f)
                                if model_data.get('model_type') == 'simplified':
                                    self._models[pred_type] = model_data
                                    logger.info(f"✅ 加载{pred_type}简化模型")
                                else:
                                    raise ValueError("Not a simplified model")
                        except Exception:
                            self._models[pred_type] = None
                            logger.warning(f"⚠️ 无法识别{pred_type}模型格式")

                except Exception as e:
                    # 回退：尝试加载为简化模型
                    try:
                        import json
                        with open(model_path, 'r', encoding='utf-8') as f:
                            model_data = json.load(f)
                            if model_data.get('model_type') == 'simplified':
                                self._models[pred_type] = model_data
                                logger.info(f"✅ 加载{pred_type}简化模型（回退模式）")
                            else:
                                raise ValueError("Not a simplified model")
                    except Exception:
                        logger.warning(f"⚠️ 加载{pred_type}模型失败: {e}")
                        self._models[pred_type] = None
            else:
                # 标记需要训练
                self._models[pred_type] = None
                logger.warning(f"⚠️ 加载{pred_type}模型不存在，路径: {model_path}")

    def _initialize_statistical_models(self):
        """初始化统计模型"""
        logger.info("初始化统计预测模型")
        # 使用简单的统计方法作为后备
        for pred_type in [PredictionType.PATTERN, PredictionType.TREND,
                          PredictionType.SENTIMENT, PredictionType.PRICE]:
            self._models[pred_type] = "statistical"

    def _initialize_fallback_models(self):
        """初始化后备模型"""
        logger.info("初始化规则基础模型")
        for pred_type in [PredictionType.PATTERN, PredictionType.TREND,
                          PredictionType.SENTIMENT, PredictionType.PRICE]:
            self._models[pred_type] = "rule_based"

    def predict_patterns(self, kdata: pd.DataFrame, patterns: List[Dict]) -> Dict[str, Any]:
        """
        形态预测

        Args:
            kdata: K线数据
            patterns: 识别到的形态列表

        Returns:
            预测结果字典
        """
        try:
            # 验证输入数据
            if not self._validate_kdata(kdata):
                raise ValueError("无效的K线数据")

            if not patterns or not isinstance(patterns, list):
                logger.warning("形态列表为空，使用默认预测")
                patterns = []

            # 验证每个形态的结构
            for i, pattern in enumerate(patterns):
                if not isinstance(pattern, dict) or 'name' not in pattern:
                    logger.warning(f"形态数据格式无效(索引{i})，跳过")
                    continue

            cache_key = self._generate_cache_key(kdata, "predict_patterns", patterns=len(patterns))
            if cache_key in self._predictions_cache:
                logger.debug(f"使用缓存的形态预测结果: {cache_key}")
                return self._predictions_cache[cache_key]

            prediction = self._generate_pattern_prediction(kdata, patterns)
            self._predictions_cache[cache_key] = prediction
            return prediction

        except Exception as e:
            logger.error(f"形态预测失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_fallback_pattern_prediction()

    def predict_trend(self, kdata: pd.DataFrame, timeframe: int = 5) -> Dict[str, Any]:
        """
        趋势预测

        Args:
            kdata: K线数据
            timeframe: 预测时间框架（天数）

        Returns:
            趋势预测结果
        """
        try:
            # 验证输入数据
            if not self._validate_kdata(kdata):
                raise ValueError("无效的K线数据")

            # 参数验证
            if not isinstance(timeframe, int) or timeframe < 1 or timeframe > 30:
                raise ValueError("预测时间框架必须在1-30天之间")

            if len(kdata) < timeframe * 2:
                raise ValueError(f"数据长度({len(kdata)})不足，至少需要{timeframe * 2}个数据点")

            features = self._extract_trend_features(kdata)
            model = self._models.get(PredictionType.TREND)

            if model and model != "rule_based" and model != "statistical":
                # 使用深度学习模型
                prediction = self._predict_with_dl_model(model, features, PredictionType.TREND)
                if prediction:  # 确保预测结果不为None
                    return prediction

            if model == "statistical":
                # 使用统计模型
                prediction = self._predict_with_statistical_model(features, PredictionType.TREND)
                if prediction:
                    return prediction

            # 使用规则模型作为后备
            prediction = self._predict_with_rules(kdata, PredictionType.TREND)
            return prediction

        except Exception as e:
            logger.error(f"趋势预测失败: {e}")
            return self._get_fallback_trend_prediction()

    def predict_sentiment(self, kdata: pd.DataFrame, market_data: Dict = None) -> Dict[str, Any]:
        """
        情绪预测

        Args:
            kdata: K线数据
            market_data: 市场数据

        Returns:
            情绪预测结果
        """
        try:
            features = self._extract_sentiment_features(kdata, market_data)
            model = self._models.get(PredictionType.SENTIMENT)

            if model and model != "rule_based" and model != "statistical":
                prediction = self._predict_with_dl_model(model, features, PredictionType.SENTIMENT)
            elif model == "statistical":
                prediction = self._predict_with_statistical_model(features, PredictionType.SENTIMENT)
            else:
                prediction = self._predict_sentiment_with_rules(kdata, market_data)

            return prediction

        except Exception as e:
            logger.error(f"情绪预测失败: {e}")
            return self._get_fallback_sentiment_prediction()

    def predict_price(self, kdata: pd.DataFrame, horizon: int = 5) -> Dict[str, Any]:
        """
        价格预测

        Args:
            kdata: K线数据
            horizon: 预测时间范围（天数）

        Returns:
            价格预测结果
        """
        try:
            features = self._extract_price_features(kdata)
            model = self._models.get(PredictionType.PRICE)

            if model and model != "rule_based" and model != "statistical":
                # 使用深度学习模型
                prediction = self._predict_with_dl_model(model, features, PredictionType.PRICE)
                if prediction:  # 确保预测结果不为None
                    return prediction

            if model == "statistical":
                # 使用统计模型
                prediction = self._predict_with_statistical_model(features, PredictionType.PRICE)
                if prediction:
                    return prediction

            # 使用规则模型作为后备
            prediction = self._predict_price_with_rules(kdata, horizon)
            return prediction

        except Exception as e:
            logger.error(f"价格预测失败: {e}")
            return self._get_fallback_price_prediction()

    def assess_risk(self, kdata: pd.DataFrame, predictions: Dict = None) -> Dict[str, Any]:
        """
        风险评估

        Args:
            kdata: K线数据
            predictions: 其他预测结果

        Returns:
            风险评估结果
        """
        try:
            # 计算各种风险指标
            volatility_risk = self._calculate_volatility_risk(kdata)
            technical_risk = self._calculate_technical_risk(kdata)
            market_risk = self._calculate_market_risk(kdata)

            # 综合风险评估
            overall_risk = self._calculate_overall_risk(
                volatility_risk, technical_risk, market_risk, predictions
            )

            return {
                'overall_risk': overall_risk,
                'volatility_risk': volatility_risk,
                'technical_risk': technical_risk,
                'market_risk': market_risk,
                'risk_level': self._categorize_risk(overall_risk),
                'risk_factors': self._identify_risk_factors(kdata),
                'recommendations': self._get_risk_recommendations(overall_risk)
            }

        except Exception as e:
            logger.error(f"风险评估失败: {e}")
            return self._get_fallback_risk_assessment()

    def _generate_pattern_prediction(self, kdata: pd.DataFrame, patterns: List[Dict]) -> Dict[str, Any]:
        """生成形态预测"""
        if not patterns:
            return self._get_fallback_pattern_prediction()

        # 分析形态信号强度
        buy_signals = [p for p in patterns if p.get('signal_type') == 'bullish']
        sell_signals = [p for p in patterns if p.get('signal_type') == 'bearish']

        # 计算平均置信度
        avg_confidence = np.mean([p.get('confidence', 0.5) for p in patterns])

        # 基于形态预测趋势
        if len(buy_signals) > len(sell_signals):
            direction = "上涨"
            confidence = min(avg_confidence + 0.1, 0.95)
        elif len(sell_signals) > len(buy_signals):
            direction = "下跌"
            confidence = min(avg_confidence + 0.1, 0.95)
        else:
            direction = "震荡"
            confidence = avg_confidence

        # 计算目标价位
        current_price = float(kdata['close'].iloc[-1])
        if direction == "上涨":
            target_price = current_price * np.random.uniform(1.02, 1.08)
        elif direction == "下跌":
            target_price = current_price * np.random.uniform(0.92, 0.98)
        else:
            target_price = current_price * np.random.uniform(0.98, 1.02)

        return {
            'direction': direction,
            'confidence': confidence,
            'target_price': target_price,
            'time_horizon': '3-7个交易日',
            'pattern_count': len(patterns),
            'signal_strength': avg_confidence,
            'model_type': 'pattern_analysis',
            'timestamp': datetime.now().isoformat()
        }

    def _extract_trend_features(self, kdata: pd.DataFrame) -> np.ndarray:
        """提取趋势预测特征"""
        features = []

        # 价格特征
        close_prices = kdata['close'].values
        features.extend([
            np.mean(close_prices[-5:]) / np.mean(close_prices[-20:]),  # 短期均线比率
            np.std(close_prices[-20:]) / np.mean(close_prices[-20:]),  # 波动率
            (close_prices[-1] - close_prices[-5]) / close_prices[-5],  # 5日涨幅
            (close_prices[-1] - close_prices[-20]) / close_prices[-20]  # 20日涨幅
        ])

        # 成交量特征
        if 'volume' in kdata.columns:
            volumes = kdata['volume'].values
            features.extend([
                np.mean(volumes[-5:]) / np.mean(volumes[-20:]),  # 成交量比率
                np.std(volumes[-20:]) / np.mean(volumes[-20:])   # 成交量波动
            ])

        return np.array(features)

    def _extract_sentiment_features(self, kdata: pd.DataFrame, market_data: Dict = None) -> np.ndarray:
        """提取情绪预测特征"""
        features = []

        # 技术情绪特征
        close_prices = kdata['close'].values
        high_prices = kdata['high'].values
        low_prices = kdata['low'].values

        # RSI近似计算
        price_changes = np.diff(close_prices[-21:])
        gains = np.where(price_changes > 0, price_changes, 0)
        losses = np.where(price_changes < 0, -price_changes, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        rsi = 100 - (100 / (1 + avg_gain / (avg_loss + 1e-8)))

        features.extend([
            rsi / 100,  # 标准化RSI
            len([1 for i in range(-10, 0) if close_prices[i] > close_prices[i-1]]) / 10,  # 上涨天数比例
            np.mean(high_prices[-10:] - close_prices[-10:]) / np.mean(close_prices[-10:]),  # 上影线比例
            np.mean(close_prices[-10:] - low_prices[-10:]) / np.mean(close_prices[-10:])   # 下影线比例
        ])

        return np.array(features)

    def _extract_price_features(self, kdata: pd.DataFrame) -> np.ndarray:
        """提取价格预测特征"""
        features = []

        # OHLCV特征
        for col in ['open', 'high', 'low', 'close']:
            if col in kdata.columns:
                values = kdata[col].values[-20:]
                features.extend([
                    np.mean(values),
                    np.std(values),
                    values[-1] / values[0] - 1  # 20日收益率
                ])

        # 技术指标特征
        close_prices = kdata['close'].values
        ma5 = np.mean(close_prices[-5:])
        ma10 = np.mean(close_prices[-10:])
        ma20 = np.mean(close_prices[-20:])

        features.extend([
            close_prices[-1] / ma5 - 1,
            close_prices[-1] / ma10 - 1,
            close_prices[-1] / ma20 - 1,
            ma5 / ma20 - 1
        ])

        return np.array(features)

    def _predict_with_dl_model(self, model, features, prediction_type):
        """使用深度学习模型进行预测"""
        try:
            # 检查是否是简化模型
            if isinstance(model, dict) and model.get('model_type') == 'simplified':
                return self._predict_with_simplified_model(model, features, prediction_type)

            # 否则使用TensorFlow模型
            if TENSORFLOW_AVAILABLE and hasattr(model, 'predict'):
                # 获取模型期望的输入形状
                expected_input_dim = model.input_shape[-1] if hasattr(model, 'input_shape') else len(features)

                # 调整特征维度以匹配模型
                if len(features) != expected_input_dim:
                    logger.info(f"调整特征维度: {len(features)} -> {expected_input_dim}")
                    if len(features) < expected_input_dim:
                        # 如果特征太少，用均值填充
                        features = np.pad(features, (0, expected_input_dim - len(features)),
                                          mode='constant', constant_values=np.mean(features))
                    else:
                        # 如果特征太多，截取前N个
                        features = features[:expected_input_dim]

                prediction = model.predict(features.reshape(1, -1), verbose=0)
                confidence = float(np.max(prediction))
                predicted_class = int(np.argmax(prediction))

                # 根据预测类型返回结果
                return self._format_prediction_result(predicted_class, confidence, prediction_type)
            else:
                raise ValueError("Invalid model type for deep learning prediction")

        except Exception as e:
            logger.warning(f"深度学习预测失败: {e}")
            # 返回后备预测结果
            return {
                'direction': '震荡',
                'confidence': 0.5,
                'model_type': 'dl_model_fallback',
                'timestamp': datetime.now().isoformat()
            }

    def _predict_with_simplified_model(self, model, features, prediction_type):
        """使用简化模型进行预测"""
        try:
            # 简化预测逻辑：基于特征和模型权重
            model_info = model.get('model_info', {})
            expected_input_dim = model_info.get('input_features', len(features))

            # 调整特征维度以匹配模型
            if len(features) != expected_input_dim:
                logger.info(f"简化模型调整特征维度: {len(features)} -> {expected_input_dim}")
                if len(features) < expected_input_dim:
                    # 如果特征太少，用均值填充
                    features = np.pad(features, (0, expected_input_dim - len(features)),
                                      mode='constant', constant_values=np.mean(features) if len(features) > 0 else 0.0)
                else:
                    # 如果特征太多，截取前N个
                    features = features[:expected_input_dim]

            # 使用模型权重进行简单的线性组合预测
            weights = model.get('weights', {})
            layer1_weights = np.array(weights.get('layer1', np.random.randn(expected_input_dim, 64)))

            # 确保权重维度匹配
            if layer1_weights.shape[0] != len(features):
                layer1_weights = np.resize(layer1_weights, (len(features), 64))

            # 简化的前向传播
            try:
                hidden = np.tanh(np.dot(features, layer1_weights))
                output = np.mean(hidden) + 0.5  # 简化输出
            except Exception:
                # 如果计算失败，使用简单的特征平均
                output = np.mean(features) + 0.5 if len(features) > 0 else 0.5

            # 生成预测结果
            confidence = min(max(abs(output - 0.5) * 2, 0.3), 0.9)  # 限制置信度范围
            predicted_class = 1 if abs(output - 0.5) < 0.1 else (2 if output > 0.5 else 0)

            return self._format_prediction_result(predicted_class, confidence, prediction_type)

        except Exception as e:
            logger.warning(f"简化模型预测失败: {e}")
            # 返回后备预测结果
            return {
                'direction': '震荡',
                'confidence': 0.5,
                'model_type': 'simplified_model_fallback',
                'timestamp': datetime.now().isoformat()
            }

    def _format_prediction_result(self, predicted_class, confidence, prediction_type):
        """格式化预测结果"""
        class_names = {
            PredictionType.PATTERN: ['下降形态', '震荡形态', '上升形态'],
            PredictionType.TREND: ['下跌趋势', '横盘趋势', '上涨趋势'],
            PredictionType.SENTIMENT: ['悲观情绪', '中性情绪', '乐观情绪'],
            PredictionType.PRICE: ['价格下跌', '价格平稳', '价格上涨']
        }

        direction_map = {
            0: '下跌',
            1: '震荡',
            2: '上涨'
        }

        class_list = class_names.get(prediction_type, ['下跌', '震荡', '上涨'])
        predicted_label = class_list[predicted_class] if predicted_class < len(class_list) else class_list[1]
        direction = direction_map.get(predicted_class, '震荡')

        return {
            'direction': direction,
            'confidence': confidence,
            'predicted_class': predicted_class,
            'predicted_label': predicted_label,
            'model_type': 'ai_model',
            'timestamp': datetime.now().isoformat()
        }

    def _predict_with_statistical_model(self, features: np.ndarray, pred_type: str) -> Dict[str, Any]:
        """使用统计模型预测"""
        # 简单的统计方法
        feature_mean = np.mean(features)
        feature_std = np.std(features)

        if feature_mean > feature_std:
            direction = "上涨" if pred_type == PredictionType.TREND else "乐观"
            confidence = 0.6
        elif feature_mean < -feature_std:
            direction = "下跌" if pred_type == PredictionType.TREND else "悲观"
            confidence = 0.6
        else:
            direction = "震荡" if pred_type == PredictionType.TREND else "中性"
            confidence = 0.5

        return {
            'direction': direction,
            'confidence': confidence,
            'model_type': 'statistical'
        }

    def _predict_with_rules(self, kdata: pd.DataFrame, pred_type: str) -> Dict[str, Any]:
        """使用规则模型预测"""
        # 如果没有提供kdata，返回默认预测
        if kdata is None or kdata.empty:
            return {
                'direction': '震荡',
                'confidence': 0.5,
                'model_type': 'rule_based_fallback'
            }

        try:
            close_prices = kdata['close'].values

            # 确保有足够的数据
            if len(close_prices) < 10:
                return {
                    'direction': '震荡',
                    'confidence': 0.5,
                    'model_type': 'rule_based_insufficient_data'
                }

            # 简单的技术分析规则
            ma5 = np.mean(close_prices[-5:])
            ma10 = np.mean(close_prices[-10:])
            current_price = close_prices[-1]

            if current_price > ma5 > ma10:
                direction = "上涨"
                confidence = 0.65
            elif current_price < ma5 < ma10:
                direction = "下跌"
                confidence = 0.65
            else:
                direction = "震荡"
                confidence = 0.5

            return {
                'direction': direction,
                'confidence': confidence,
                'model_type': 'rule_based'
            }
        except Exception as e:
            logger.warning(f"规则预测失败: {e}")
            return {
                'direction': '震荡',
                'confidence': 0.5,
                'model_type': 'rule_based_error'
            }

    def _predict_sentiment_with_rules(self, kdata: pd.DataFrame, market_data: Dict = None) -> Dict[str, Any]:
        """基于规则的情绪预测"""
        return self._predict_with_rules(kdata, PredictionType.SENTIMENT)

    def _predict_price_with_rules(self, kdata: pd.DataFrame, horizon: int) -> Dict[str, Any]:
        """基于规则的价格预测"""
        current_price = float(kdata['close'].iloc[-1])
        close_prices = kdata['close'].values

        # 计算趋势
        trend = np.polyfit(range(len(close_prices[-10:])), close_prices[-10:], 1)[0]

        # 预测价格范围
        if trend > 0:
            target_low = current_price * 1.01
            target_high = current_price * 1.05
            direction = "上涨"
        elif trend < 0:
            target_low = current_price * 0.95
            target_high = current_price * 0.99
            direction = "下跌"
        else:
            target_low = current_price * 0.98
            target_high = current_price * 1.02
            direction = "震荡"

        return {
            'direction': direction,
            'current_price': current_price,
            'target_low': target_low,
            'target_high': target_high,
            'target_range': f"{target_low:.2f} - {target_high:.2f}",
            'horizon_days': horizon,
            'confidence': 0.6,
            'model_type': 'rule_based'
        }

    def _calculate_volatility_risk(self, kdata: pd.DataFrame) -> float:
        """计算波动率风险"""
        returns = kdata['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # 年化波动率
        return min(volatility * 5, 1.0)  # 标准化到0-1

    def _calculate_technical_risk(self, kdata: pd.DataFrame) -> float:
        """计算技术面风险"""
        close_prices = kdata['close'].values

        # 计算最大回撤
        peak = np.maximum.accumulate(close_prices)
        drawdown = (close_prices - peak) / peak
        max_drawdown = abs(np.min(drawdown))

        return min(max_drawdown * 2, 1.0)

    def _calculate_market_risk(self, kdata: pd.DataFrame) -> float:
        """计算市场风险"""
        # 简化的市场风险评估
        volumes = kdata['volume'].values if 'volume' in kdata.columns else np.ones(len(kdata))
        vol_ratio = np.std(volumes[-10:]) / np.mean(volumes[-10:])
        return min(vol_ratio * 0.5, 1.0)

    def _calculate_overall_risk(self, vol_risk: float, tech_risk: float,
                                market_risk: float, predictions: Dict = None) -> float:
        """计算综合风险"""
        weights = [0.4, 0.4, 0.2]  # 波动率、技术面、市场风险权重
        risks = [vol_risk, tech_risk, market_risk]
        overall = np.average(risks, weights=weights)

        # 如果有预测结果，调整风险
        if predictions:
            confidence = predictions.get('confidence', 0.5)
            if confidence < 0.5:
                overall *= 1.2  # 低置信度增加风险

        return min(overall, 1.0)

    def _categorize_risk(self, risk_score: float) -> str:
        """风险等级分类"""
        if risk_score < 0.3:
            return "低风险"
        elif risk_score < 0.6:
            return "中风险"
        else:
            return "高风险"

    def _identify_risk_factors(self, kdata: pd.DataFrame) -> List[str]:
        """识别风险因素"""
        factors = []

        # 检查技术指标风险
        close_prices = kdata['close'].values
        if len(close_prices) > 20:
            ma20 = np.mean(close_prices[-20:])
            if close_prices[-1] < ma20 * 0.95:
                factors.append("价格大幅低于均线")

        # 检查波动率风险
        returns = pd.Series(close_prices).pct_change().dropna()
        if returns.std() > 0.05:
            factors.append("高波动率")

        # 检查成交量异常
        if 'volume' in kdata.columns:
            volumes = kdata['volume'].values
            if len(volumes) > 10:
                vol_ratio = volumes[-1] / np.mean(volumes[-10:])
                if vol_ratio > 3:
                    factors.append("成交量异常放大")
                elif vol_ratio < 0.3:
                    factors.append("成交量异常萎缩")

        return factors if factors else ["无明显风险因素"]

    def _get_risk_recommendations(self, risk_score: float) -> List[str]:
        """获取风险建议"""
        if risk_score < 0.3:
            return ["可以适度增加仓位", "注意止盈点设置"]
        elif risk_score < 0.6:
            return ["保持适中仓位", "设置止损点", "密切关注市场变化"]
        else:
            return ["建议减少仓位", "严格止损", "避免追涨杀跌", "等待更好时机"]

    # 后备预测方法
    def _get_fallback_pattern_prediction(self) -> Dict[str, Any]:
        """后备形态预测"""
        return {
            'direction': '震荡',
            'confidence': 0.5,
            'target_price': 0.0,
            'time_horizon': '3-5个交易日',
            'pattern_count': 0,
            'signal_strength': 0.5,
            'model_type': 'fallback',
            'timestamp': datetime.now().isoformat()
        }

    def _get_fallback_trend_prediction(self) -> Dict[str, Any]:
        """后备趋势预测"""
        return {
            'direction': '震荡',
            'confidence': 0.5,
            'model_type': 'fallback'
        }

    def _get_fallback_sentiment_prediction(self) -> Dict[str, Any]:
        """后备情绪预测"""
        return {
            'direction': '中性',
            'confidence': 0.5,
            'model_type': 'fallback'
        }

    def _get_fallback_price_prediction(self) -> Dict[str, Any]:
        """后备价格预测"""
        return {
            'direction': '震荡',
            'current_price': 0.0,
            'target_low': 0.0,
            'target_high': 0.0,
            'target_range': 'N/A',
            'horizon_days': 5,
            'confidence': 0.5,
            'model_type': 'fallback'
        }

    def _get_fallback_risk_assessment(self) -> Dict[str, Any]:
        """后备风险评估"""
        return {
            'overall_risk': 0.5,
            'volatility_risk': 0.5,
            'technical_risk': 0.5,
            'market_risk': 0.5,
            'risk_level': '中风险',
            'risk_factors': ['数据不足'],
            'recommendations': ['谨慎操作', '充分准备']
        }

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'available_models': list(self._models.keys()),
            'model_types': {k: type(v).__name__ for k, v in self._models.items()},
            'deep_learning_available': DL_AVAILABLE,
            'tensorflow_available': TENSORFLOW_AVAILABLE,
            'config': self.model_config,
            'cache_size': len(self._predictions_cache)
        }

    def get_model_type_display_name(self, model_type: str) -> str:
        """获取模型类型的显示名称"""
        display_names = {
            'ensemble': '集成模型',
            'deep_learning': '深度学习',
            'statistical': '统计模型',
            'rule_based': '规则模型'
        }
        return display_names.get(model_type, model_type)

    def validate_model_type(self, model_type: str) -> bool:
        """验证模型类型是否有效"""
        valid_types = [AIModelType.ENSEMBLE, AIModelType.DEEP_LEARNING,
                       AIModelType.STATISTICAL, AIModelType.RULE_BASED]
        return model_type in valid_types

    def reload_config(self):
        """重新加载配置"""
        try:
            self._load_config_from_database()
            logger.info("AI预测服务配置已重新加载")
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")

    def get_current_config(self) -> Dict[str, Any]:
        """获取当前有效配置"""
        return {
            'model_config': self.model_config,
            'validation_config': self.validation_config,
            'feature_config': self.feature_config,
            'cache_config': self.cache_config,
            'logging_config': self.logging_config
        }

    def clear_cache(self):
        """清理预测缓存"""
        self._predictions_cache.clear()
        logger.info("预测缓存已清理")

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.model_config.update(new_config)
        logger.info(f"配置已更新: {new_config}")

    def dispose(self):
        """清理资源"""
        self.clear_cache()
        self._models.clear()
        logger.info("AI预测服务已清理")
