"""
智能模型选择器主模块

提供完整的智能模型选择功能，整合市场状态检测、模型性能评估、
动态选择策略和预测结果融合。
"""

import logging
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from .market_detector import MarketStateDetector, MarketState
from .performance_evaluator import ModelPerformanceEvaluator, ModelPerformance
from .selection_strategy import ModelSelectionStrategy, ModelSelection, SelectionCriteria
from .fusion_engine import (
    PredictionFusionEngine, ModelPrediction, EnsemblePredictionResult,
    FusionMethod
)
from .config.selector_config import IntelligentSelectorConfig
from .config.model_profiles import ModelProfile, MarketCondition

logger = logging.getLogger(__name__)


@dataclass
class SelectionRequest:
    """模型选择请求"""
    prediction_type: str
    available_models: List[str]
    market_data: Dict[str, Any]
    kline_data: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SelectionResult:
    """模型选择结果"""
    selected_models: List[ModelSelection]
    market_state: MarketState
    performance_evaluation: Dict[str, ModelPerformance]
    fusion_result: Optional[EnsemblePredictionResult] = None
    selection_criteria: Optional[SelectionCriteria] = None
    selection_metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class IntelligentModelSelector:
    """智能模型选择器主类"""
    
    def __init__(self, config: IntelligentSelectorConfig = None):
        """初始化智能模型选择器"""
        self.config = config or IntelligentSelectorConfig()
        
        # 初始化各个组件
        self.market_detector = MarketStateDetector(self.config.market_detection)
        self.performance_evaluator = ModelPerformanceEvaluator(self.config.performance_evaluation)
        self.selection_strategy = ModelSelectionStrategy(self.config.selection_strategy)
        self.fusion_engine = PredictionFusionEngine(self.config.fusion)
        
        # 模型档案管理
        self.model_profiles = self._load_model_profiles()
        
        # 缓存和统计
        self.selection_cache = {}
        self.statistics = {
            'total_selections': 0,
            'successful_selections': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'total_predictions': 0,
            'average_processing_time': 0.0
        }
        
        logger.info("智能模型选择器初始化完成")
    
    def select_models(self, request: SelectionRequest) -> SelectionResult:
        """执行智能模型选择"""
        start_time = datetime.now()
        
        try:
            logger.info(f"开始智能模型选择: {len(request.available_models)}个可用模型")
            
            # 1. 检查缓存
            cache_data = {
                'models': request.available_models,
                'market_data': request.market_data,
                'kline_data': request.kline_data
            }
            cache_key = self._generate_cache_key(cache_data, 'selection')
            if cache_key in self.selection_cache:
                logger.info("命中缓存，直接返回结果")
                self.statistics['cache_hits'] += 1
                cached_result = self.selection_cache[cache_key]
                cached_result.timestamp = datetime.now()  # 更新时间戳
                return cached_result
            
            self.statistics['cache_misses'] += 1
            
            # 2. 市场状态检测
            logger.info("进行市场状态检测")
            market_state = self.market_detector.detect_market_state(
                request.kline_data, request.market_data
            )
            
            # 3. 模型性能评估
            logger.info("评估模型性能")
            performance_evaluation = {}
            for model_type in request.available_models:
                # 模拟性能评估（实际应用中应该基于历史数据）
                performance = self._simulate_performance_evaluation(
                    model_type, market_state
                )
                performance_evaluation[model_type] = performance
            
            # 4. 构建选择标准
            selection_criteria = self._build_selection_criteria(
                request, market_state, performance_evaluation
            )
            
            # 5. 模型选择
            logger.info("执行模型选择策略")
            selected_models = self.selection_strategy.select_optimal_models(
                selection_criteria
            )
            
            # 6. 预测结果融合（如果需要）
            fusion_result = None
            if self.config.enable_fusion and len(selected_models) > 1:
                logger.info("执行预测结果融合")
                fusion_result = self._perform_fusion(selected_models, request)
            
            # 7. 构建选择结果
            result = SelectionResult(
                selected_models=selected_models,
                market_state=market_state,
                performance_evaluation=performance_evaluation,
                fusion_result=fusion_result,
                selection_criteria=selection_criteria,
                selection_metadata={
                    'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'cache_key': cache_key,
                    'config_version': self.config.version
                }
            )
            
            # 8. 缓存结果
            self._cache_result(cache_key, result)
            
            # 9. 更新统计信息
            self._update_statistics(start_time, success=True)
            
            logger.info(f"智能模型选择完成: 选择了{len(selected_models)}个模型, "
                       f"处理时间={(datetime.now() - start_time).total_seconds():.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"智能模型选择失败: {e}")
            self._update_statistics(start_time, success=False)
            
            # 返回默认选择结果
            return self._get_fallback_result(request)
    
    def _simulate_performance_evaluation(self, model_type: str, 
                                       market_state: MarketState) -> ModelPerformance:
        """模拟模型性能评估"""
        try:
            # 基于市场状态和模型类型模拟性能评估
            # 实际应用中这里应该基于真实的历史数据
            
            base_accuracy = self._get_base_accuracy(model_type)
            volatility_factor = self._get_volatility_factor(market_state.volatility.level.value)
            trend_factor = self._get_trend_factor(market_state.trend_strength.level.value)
            
            adjusted_accuracy = base_accuracy * volatility_factor * trend_factor
            
            return ModelPerformance(
                model_type=model_type,
                metrics=self._create_mock_metrics(adjusted_accuracy),
                composite_score=adjusted_accuracy,
                reliability_score=min(adjusted_accuracy * 1.1, 1.0),
                sample_size=100,  # 模拟样本数
                evaluation_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.warning(f"模拟{model_type}性能评估失败: {e}")
            return ModelPerformance(
                model_type=model_type,
                metrics=self._create_mock_metrics(0.5),
                composite_score=0.5,
                reliability_score=0.5,
                sample_size=0,
                evaluation_timestamp=datetime.now()
            )
    
    def _get_base_accuracy(self, model_type: str) -> float:
        """获取模型基础准确率"""
        base_accuracies = {
            'linear_regression': 0.65,
            'random_forest': 0.75,
            'svm': 0.70,
            'neural_network': 0.80,
            'lstm': 0.85,
            'xgboost': 0.82,
            'prophet': 0.78,
            'arima': 0.72
        }
        return base_accuracies.get(model_type, 0.6)
    
    def _get_volatility_factor(self, volatility_level: str) -> float:
        """获取波动率调整因子"""
        factors = {
            'low': 1.0,
            'medium': 0.9,
            'high': 0.8,
            'extreme': 0.7
        }
        return factors.get(volatility_level, 0.9)
    
    def _get_trend_factor(self, trend_level: str) -> float:
        """获取趋势强度调整因子"""
        factors = {
            'weak': 0.9,
            'moderate': 1.0,
            'strong': 1.1,
            'very_strong': 1.05
        }
        return factors.get(trend_level, 1.0)
    
    def _create_mock_metrics(self, accuracy: float) -> 'ModelMetrics':
        """创建模拟的模型指标"""
        from .performance_evaluator import ModelMetrics
        
        return ModelMetrics(
            accuracy=accuracy,
            precision=max(accuracy - 0.05, 0.0),
            recall=max(accuracy - 0.03, 0.0),
            f1_score=max(accuracy - 0.04, 0.0),
            mape=max(100.0 - accuracy * 80.0, 5.0),  # 模拟MAPE
            sharpe_ratio=max((accuracy - 0.5) * 2, -1.0),
            timestamp=datetime.now()
        )
    
    def _build_selection_criteria(self, request: SelectionRequest,
                                market_state: MarketState,
                                performance_evaluation: Dict[str, ModelPerformance]) -> SelectionCriteria:
        """构建模型选择标准"""
        try:
            # 基于市场状态确定权重
            weights = self._calculate_criteria_weights(market_state)
            
            # 应用用户偏好和约束
            user_weights = self._apply_user_preferences(
                request.user_preferences or {}, weights
            )
            
            # 确定选择数量
            max_models = self._determine_max_models(
                request, market_state, performance_evaluation
            )
            
            return SelectionCriteria(
                prediction_type=request.prediction_type,
                market_state={
                    'volatility': market_state.volatility.level.value,
                    'trend_strength': market_state.trend_strength.level.value,
                    'market_regime': market_state.market_regime.regime.value,
                    'liquidity': market_state.liquidity.level.value
                },
                data_quality=self._assess_data_quality(request),
                latency_requirement=request.constraints.get('max_latency', 1000) if request.constraints else 1000,
                accuracy_requirement=request.constraints.get('min_accuracy', 0.7) if request.constraints else 0.7,
                available_models=request.available_models,
                ensemble_size=max_models
            )
            
        except Exception as e:
            logger.error(f"构建选择标准失败: {e}")
            # 返回默认标准
            return SelectionCriteria(
                prediction_type=request.prediction_type,
                market_state={},
                data_quality="medium",
                latency_requirement=1000,
                accuracy_requirement=0.7,
                available_models=request.available_models,
                ensemble_size=min(3, len(request.available_models))
            )
    
    def _calculate_criteria_weights(self, market_state: MarketState) -> Dict[str, float]:
        """基于市场状态计算权重"""
        # 基础权重
        base_weights = {
            'accuracy': 0.3,
            'speed': 0.2,
            'robustness': 0.25,
            'interpretability': 0.15,
            'resource_usage': 0.1
        }
        
        # 根据市场状态调整权重
        if market_state.volatility.level.value in ['high', 'extreme']:
            # 高波动环境，更重视鲁棒性
            base_weights['robustness'] = 0.4
            base_weights['accuracy'] = 0.25
        
        if market_state.trend_strength.level.value in ['strong', 'very_strong']:
            # 强趋势环境，更重视准确性和速度
            base_weights['accuracy'] = 0.35
            base_weights['speed'] = 0.25
        
        return base_weights
    
    def _apply_user_preferences(self, user_preferences: Dict[str, Any], 
                              default_weights: Dict[str, float]) -> Dict[str, float]:
        """应用用户偏好"""
        weights = default_weights.copy()
        
        # 处理用户指定的权重
        if 'weights' in user_preferences:
            user_weights = user_preferences['weights']
            for criterion, weight in user_weights.items():
                if criterion in weights and isinstance(weight, (int, float)):
                    weights[criterion] = max(0.0, min(1.0, weight))
        
        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def _determine_max_models(self, request: SelectionRequest,
                            market_state: MarketState,
                            performance_evaluation: Dict[str, ModelPerformance]) -> int:
        """确定最大模型数量"""
        # 基础最大数量
        base_max = 3
        
        # 根据可用模型数量调整
        available_count = len(request.available_models)
        if available_count <= 2:
            return available_count
        
        # 根据市场状态调整
        if market_state.volatility.level.value in ['high', 'extreme']:
            # 高波动环境使用更多模型以提高稳定性
            return min(base_max + 1, available_count)
        
        # 根据用户约束调整
        if request.constraints and 'max_models' in request.constraints:
            max_allowed = request.constraints['max_models']
            return min(base_max, max_allowed, available_count)
        
        return min(base_max, available_count)
    
    def _perform_fusion(self, selected_models: List[ModelSelection], 
                       request: SelectionRequest) -> Optional[EnsemblePredictionResult]:
        """执行预测结果融合"""
        try:
            # 模拟模型预测结果
            mock_predictions = self._generate_mock_predictions(selected_models)
            
            # 执行融合
            fusion_result = self.fusion_engine.fuse_predictions(
                mock_predictions, FusionMethod.WEIGHTED_AVERAGE
            )
            
            return fusion_result
            
        except Exception as e:
            logger.warning(f"预测融合失败: {e}")
            return None
    
    def _generate_mock_predictions(self, selected_models: List[ModelSelection]) -> List[ModelPrediction]:
        """生成模拟预测结果"""
        predictions = []
        
        for model_selection in selected_models:
            # 模拟预测值（实际应用中应该调用真实的模型预测）
            import random
            random.seed(hash(model_selection.model_type) % 1000)
            
            prediction_value = random.uniform(-0.1, 0.1)  # 模拟小幅变动
            confidence = model_selection.confidence * 0.8 + 0.1  # 基于置信度的预测置信度
            
            # 创建模型预测对象
            prediction = ModelPrediction(
                model_type=model_selection.model_type,
                prediction_value=prediction_value,
                confidence=confidence,
                timestamp=datetime.now(),
                metadata={'selection_weight': model_selection.weight, 'selection_confidence': model_selection.confidence}
            )
            predictions.append(prediction)
        
        return predictions
    
    def _assess_data_quality(self, request: SelectionRequest) -> float:
        """评估数据质量"""
        try:
            quality_score = 0.8  # 基础质量分数
            
            # 检查K线数据完整性
            if request.kline_data:
                required_fields = ['open', 'high', 'low', 'close', 'volume']
                available_fields = [field for field in required_fields if field in request.kline_data]
                completeness = len(available_fields) / len(required_fields)
                quality_score *= (0.5 + 0.5 * completeness)
            
            # 检查市场数据
            if request.market_data:
                data_count = len(request.market_data)
                if data_count >= 5:
                    quality_score *= 1.0
                elif data_count >= 3:
                    quality_score *= 0.8
                else:
                    quality_score *= 0.6
            
            return min(1.0, quality_score)
            
        except Exception as e:
            logger.warning(f"数据质量评估失败: {e}")
            return 0.5
    
    def _generate_cache_key(self, data: Dict[str, Any], prediction_type: str) -> str:
        """生成缓存键"""
        import hashlib
        
        key_data = {
            'prediction_type': prediction_type,
            'data_hash': hash(str(sorted(data.items()))),
            'timestamp_hour': datetime.now().replace(minute=0, second=0, microsecond=0).timestamp()
        }
        
        key_str = str(key_data)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _cache_result(self, cache_key: str, result: SelectionResult):
        """缓存选择结果"""
        try:
            self.selection_cache[cache_key] = result
            
            # 限制缓存大小
            if len(self.selection_cache) > self.config.max_cache_size:
                # 删除最旧的缓存项
                oldest_key = min(self.selection_cache.keys())
                del self.selection_cache[oldest_key]
                
        except Exception as e:
            logger.warning(f"缓存结果失败: {e}")
    
    def _update_statistics(self, start_time: datetime, success: bool):
        """更新统计信息"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        self.statistics['total_selections'] += 1
        if success:
            self.statistics['successful_selections'] += 1
        
        # 更新平均处理时间
        current_avg = self.statistics['average_processing_time']
        total = self.statistics['total_selections']
        self.statistics['average_processing_time'] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def _get_fallback_result(self, request: SelectionRequest) -> SelectionResult:
        """获取选择失败时的默认结果"""
        logger.info("使用默认选择策略")
        
        # 选择前两个模型作为默认选择
        fallback_models = request.available_models[:2] if len(request.available_models) >= 2 else request.available_models
        
        # 创建默认模型选择
        from .selection_strategy import ModelSelection
        selected_models = []
        for i, model_type in enumerate(fallback_models):
            selection = ModelSelection(
                model_type=model_type,
                confidence=0.5,
                weight=0.5,
                selection_reason="默认选择策略",
                timestamp=datetime.now()
            )
            selected_models.append(selection)
        
        # 创建默认市场状态
        from .market_detector import MarketState
        default_market_state = self.market_detector._get_default_market_state()
        
        return SelectionResult(
            selected_models=selected_models,
            market_state=default_market_state,
            performance_evaluation={},
            selection_metadata={'fallback': True, 'error': 'Default selection due to failure'}
        )
    
    def _load_model_profiles(self) -> Dict[str, ModelProfile]:
        """加载模型档案"""
        from .config.model_profiles import get_predefined_model_profiles
        return get_predefined_model_profiles()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.statistics.copy()
    
    def clear_cache(self):
        """清除缓存"""
        self.selection_cache.clear()
        logger.info("模型选择缓存已清除")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            'cache_size': len(self.selection_cache),
            'max_cache_size': self.config.max_cache_size,
            'cache_keys': list(self.selection_cache.keys())
        }
    
    def intelligent_predict(self, 
                          prediction_type: str, 
                          data: Dict[str, Any],
                          **kwargs) -> Optional[Dict[str, Any]]:
        """
        智能预测接口
        
        Args:
            prediction_type: 预测类型
            data: 输入数据
            **kwargs: 其他参数
            
        Returns:
            智能选择后的预测结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 数据预处理和验证
            processed_data = self._preprocess_data(data, prediction_type)
            if not processed_data:
                return self._fallback_prediction(prediction_type, data)
            
            # 2. 生成缓存键
            cache_key = self._generate_cache_key(processed_data, prediction_type)
            
            # 3. 检查缓存
            if self.config.enable_cache and self._is_cache_valid(cache_key):
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self.statistics['cache_hits'] += 1
                    return cached_result
            
            self.statistics['cache_misses'] += 1
            
            # 4. 构建选择请求
            available_models = self._get_available_models(prediction_type, processed_data)
            if not available_models:
                logger.warning(f"没有可用的{prediction_type}模型")
                return self._fallback_prediction(prediction_type, data)
            
            request = SelectionRequest(
                prediction_type=prediction_type,
                available_models=available_models,
                market_data=processed_data.get('market_data', {}),
                kline_data=processed_data.get('kline_data'),
                constraints=kwargs
            )
            
            # 5. 执行模型选择
            selection_result = self.select_models(request)
            
            if not selection_result.selected_models:
                logger.warning("模型选择失败，使用后备策略")
                return self._fallback_prediction(prediction_type, data)
            
            # 6. 执行多模型预测
            predictions = self._execute_model_predictions(
                selection_result.selected_models, processed_data
            )
            
            if not predictions:
                logger.warning("所有模型预测失败，使用后备策略")
                return self._fallback_prediction(prediction_type, data)
            
            # 7. 融合预测结果
            if self.config.enable_fusion and len(predictions) > 1:
                from .fusion_engine import FusionMethod
                final_prediction = self.fusion_engine.fuse_predictions(
                    predictions,
                    FusionMethod.WEIGHTED_AVERAGE
                )
            else:
                final_prediction = predictions[0]
            
            # 8. 转换为字典格式并添加元数据
            if hasattr(final_prediction, 'final_prediction'):
                # 融合引擎返回的对象
                prediction_dict = {
                    'prediction': final_prediction.final_prediction,
                    'confidence': final_prediction.confidence,
                    'model_type': final_prediction.contributing_models[0] if final_prediction.contributing_models else 'ensemble',
                    'strategy': final_prediction.fusion_method,
                    'timestamp': final_prediction.timestamp,
                    'individual_predictions': [
                        {
                            'model_type': p.model_type,
                            'prediction': p.prediction_value,
                            'confidence': p.confidence
                        }
                        for p in final_prediction.individual_predictions
                    ],
                    'selection_metadata': {
                        'selected_models': [s.model_type for s in selection_result.selected_models],
                        'market_state': selection_result.market_state.__dict__,
                        'selection_confidence': np.mean([s.confidence for s in selection_result.selected_models]),
                        'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                    }
                }
            else:
                # 直接预测结果字典
                prediction_dict = final_prediction.copy()
                prediction_dict.update({
                    'selection_metadata': {
                        'selected_models': [s.model_type for s in selection_result.selected_models],
                        'market_state': selection_result.market_state.__dict__,
                        'selection_confidence': np.mean([s.confidence for s in selection_result.selected_models]),
                        'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                    }
                })
            
            final_prediction = prediction_dict
            
            # 9. 缓存结果
            if self.config.enable_cache:
                self._cache_result(cache_key, final_prediction)
            
            # 10. 更新统计
            self.statistics['successful_predictions'] += 1
            self.statistics['total_predictions'] += 1
            
            return final_prediction
            
        except Exception as e:
            logger.error(f"智能预测失败: {e}")
            self.statistics['failed_predictions'] += 1
            self.statistics['total_predictions'] += 1
            return self._fallback_prediction(prediction_type, data)
    
    def _preprocess_data(self, data: Dict[str, Any], prediction_type: str) -> Optional[Dict[str, Any]]:
        """预处理输入数据"""
        try:
            processed = data.copy()
            
            # 验证必要字段
            if prediction_type in ['price_prediction', 'trend_prediction']:
                if 'kline_data' not in processed and 'kline_data' not in data:
                    if 'market_data' in processed:
                        # 模拟K线数据
                        processed['kline_data'] = {
                            'open': processed['market_data'].get('price', 100),
                            'close': processed['market_data'].get('price', 100),
                            'high': processed['market_data'].get('price', 100) * 1.01,
                            'low': processed['market_data'].get('price', 100) * 0.99,
                            'volume': processed['market_data'].get('volume', 1000000)
                        }
            
            return processed
            
        except Exception as e:
            logger.error(f"数据预处理失败: {e}")
            return None
    

    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.selection_cache:
            return False
        
        cache_entry = self.selection_cache[cache_key]
        cache_time = cache_entry.get('timestamp', datetime.min)
        
        # 检查是否过期
        return (datetime.now() - cache_time).total_seconds() < self.config.cache_ttl
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        if cache_key in self.selection_cache:
            return self.selection_cache[cache_key].get('result')
        return None
    
    def _get_available_models(self, prediction_type: str, data: Dict[str, Any]) -> List[str]:
        """获取可用模型"""
        # 根据预测类型返回对应的可用模型
        model_mapping = {
            'price_prediction': ['linear_regression', 'random_forest', 'svm', 'neural_network'],
            'trend_prediction': ['linear_regression', 'random_forest', 'lstm', 'arima'],
            'pattern_recognition': ['cnn', 'svm', 'random_forest'],
            'sentiment_analysis': ['bert', 'svm', 'naive_bayes']
        }
        
        return model_mapping.get(prediction_type, ['linear_regression', 'random_forest'])
    
    def _execute_model_predictions(self, 
                                 selected_models: List[ModelSelection], 
                                 data: Dict[str, Any]) -> List[ModelPrediction]:
        """执行模型预测"""
        predictions = []
        
        for selection in selected_models:
            try:
                # 模拟模型预测
                prediction = self._simulate_model_prediction(selection.model_type, data)
                predictions.append(prediction)
            except Exception as e:
                logger.warning(f"模型 {selection.model_type} 预测失败: {e}")
                continue
        
        return predictions
    
    def _simulate_model_prediction(self, model_type: str, data: Dict[str, Any]) -> ModelPrediction:
        """模拟模型预测"""
        # 简化的预测逻辑
        base_value = 100.0
        
        # 根据模型类型生成不同的预测结果
        if model_type == 'linear_regression':
            prediction_value = base_value * 1.02
            confidence = 0.75
        elif model_type == 'random_forest':
            prediction_value = base_value * 1.015
            confidence = 0.80
        elif model_type == 'svm':
            prediction_value = base_value * 1.018
            confidence = 0.70
        else:
            prediction_value = base_value * 1.01
            confidence = 0.65
        
        return ModelPrediction(
            model_type=model_type,
            prediction_value=prediction_value,
            confidence=confidence,
            timestamp=datetime.now(),
            metadata={'selection_weight': None, 'data_keys': list(data.keys())}
        )
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """缓存结果"""
        if len(self.selection_cache) >= self.config.max_cache_size:
            # 清除最旧的缓存
            oldest_key = min(self.selection_cache.keys(), 
                           key=lambda k: self.selection_cache[k]['timestamp'])
            del self.selection_cache[oldest_key]
        
        self.selection_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
    
    def _fallback_prediction(self, prediction_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """后备预测策略"""
        return {
            'prediction': 100.0,
            'confidence': 0.5,
            'model_type': 'fallback',
            'strategy': 'simple_average',
            'timestamp': datetime.now(),
            'note': '使用后备预测策略'
        }