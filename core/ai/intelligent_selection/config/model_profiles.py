"""
模型档案管理

定义不同AI模型的特性、性能指标和使用场景
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ModelType(Enum):
    """模型类型枚举"""
    LSTM = "lstm"
    GRU = "gru"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    SVM = "svm"
    LINEAR_REGRESSION = "linear_regression"
    PROPHET = "prophet"
    ARIMA = "arima"
    ENSEMBLE = "ensemble"


class MarketCondition(Enum):
    """市场条件枚举"""
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    STRONG_TREND = "strong_trend"
    WEAK_TREND = "weak_trend"
    NORMAL = "normal"


@dataclass
class ModelProfile:
    """模型档案"""
    model_type: str
    name: str
    description: str
    
    # 性能特征
    accuracy_range: tuple  # (min, max)
    speed_class: str  # fast, medium, slow
    memory_usage: int  # MB
    
    # 适用场景
    suitable_conditions: List[MarketCondition]
    data_requirements: Dict[str, Any]
    
    # 技术特征
    features: List[str]
    hyperparameters: Dict[str, Any]
    
    # 预测特征
    prediction_horizon: int  # 天数
    confidence_threshold: float
    
    def is_suitable_for(self, market_condition: MarketCondition, 
                       data_quality: str) -> bool:
        """判断模型是否适合当前市场条件"""
        if market_condition not in self.suitable_conditions:
            return False
        
        # 检查数据质量要求
        required_quality = self.data_requirements.get('quality', 'medium')
        if data_quality == 'low' and required_quality != 'low':
            return False
        
        return True


class ModelProfiles:
    """模型档案管理"""
    
    def __init__(self):
        self.profiles = self._initialize_profiles()
    
    def _initialize_profiles(self) -> Dict[str, ModelProfile]:
        """初始化模型档案"""
        return {
            'lstm': ModelProfile(
                model_type='lstm',
                name='长短期记忆网络',
                description='适合复杂时间序列模式识别，对长期依赖关系建模效果好',
                accuracy_range=(0.75, 0.95),
                speed_class='slow',
                memory_usage=256,
                suitable_conditions=[
                    MarketCondition.NORMAL,
                    MarketCondition.STRONG_TREND
                ],
                data_requirements={
                    'quality': 'high',
                    'min_samples': 1000,
                    'features': ['open', 'high', 'low', 'close', 'volume']
                },
                features=[
                    '长期依赖建模',
                    '非线性模式识别',
                    '多特征融合',
                    '自适应学习'
                ],
                hyperparameters={
                    'hidden_units': [64, 128],
                    'layers': [2, 3],
                    'dropout': 0.2,
                    'learning_rate': 0.001
                },
                prediction_horizon=30,
                confidence_threshold=0.8
            ),
            
            'gru': ModelProfile(
                model_type='gru',
                name='门控循环单元',
                description='LSTM的简化版本，训练更快，适合实时应用',
                accuracy_range=(0.70, 0.90),
                speed_class='medium',
                memory_usage=128,
                suitable_conditions=[
                    MarketCondition.NORMAL,
                    MarketCondition.WEAK_TREND
                ],
                data_requirements={
                    'quality': 'medium',
                    'min_samples': 500,
                    'features': ['open', 'high', 'low', 'close', 'volume']
                },
                features=[
                    '快速训练',
                    '参数较少',
                    '实时预测',
                    '稳定性好'
                ],
                hyperparameters={
                    'hidden_units': [64, 96],
                    'layers': [2, 3],
                    'dropout': 0.15,
                    'learning_rate': 0.001
                },
                prediction_horizon=15,
                confidence_threshold=0.75
            ),
            
            'xgboost': ModelProfile(
                model_type='xgboost',
                name='梯度提升决策树',
                description='对非线性关系建模能力强，适合中高频交易策略',
                accuracy_range=(0.65, 0.88),
                speed_class='fast',
                memory_usage=64,
                suitable_conditions=[
                    MarketCondition.NORMAL,
                    MarketCondition.HIGH_VOLATILITY,
                    MarketCondition.LOW_VOLATILITY
                ],
                data_requirements={
                    'quality': 'medium',
                    'min_samples': 200,
                    'features': ['open', 'high', 'low', 'close', 'volume', 'rsi', 'macd']
                },
                features=[
                    '快速训练',
                    '特征重要性',
                    '过拟合控制',
                    '可解释性强'
                ],
                hyperparameters={
                    'n_estimators': [100, 200],
                    'max_depth': [3, 6],
                    'learning_rate': [0.05, 0.1],
                    'subsample': 0.8
                },
                prediction_horizon=10,
                confidence_threshold=0.70
            ),
            
            'random_forest': ModelProfile(
                model_type='random_forest',
                name='随机森林',
                description='集成学习方法，稳定性好，适合基准策略',
                accuracy_range=(0.60, 0.85),
                speed_class='fast',
                memory_usage=32,
                suitable_conditions=[
                    MarketCondition.NORMAL,
                    MarketCondition.LOW_VOLATILITY
                ],
                data_requirements={
                    'quality': 'medium',
                    'min_samples': 100,
                    'features': ['open', 'high', 'low', 'close', 'volume']
                },
                features=[
                    '高稳定性',
                    '抗噪声能力强',
                    '快速预测',
                    '特征选择'
                ],
                hyperparameters={
                    'n_estimators': [50, 100],
                    'max_depth': [5, 10],
                    'min_samples_split': 5,
                    'max_features': 'sqrt'
                },
                prediction_horizon=7,
                confidence_threshold=0.65
            ),
            
            'linear_regression': ModelProfile(
                model_type='linear_regression',
                name='线性回归',
                description='简单快速，适合平稳市场的基础预测',
                accuracy_range=(0.50, 0.75),
                speed_class='fast',
                memory_usage=8,
                suitable_conditions=[
                    MarketCondition.NORMAL,
                    MarketCondition.LOW_VOLATILITY
                ],
                data_requirements={
                    'quality': 'low',
                    'min_samples': 50,
                    'features': ['open', 'high', 'low', 'close']
                },
                features=[
                    '简单快速',
                    '低内存占用',
                    '可解释性强',
                    '基础模型'
                ],
                hyperparameters={
                    'fit_intercept': True,
                    'normalize': False
                },
                prediction_horizon=3,
                confidence_threshold=0.60
            ),
            
            'ensemble': ModelProfile(
                model_type='ensemble',
                name='集成模型',
                description='多个模型的组合，通过加权或投票方式提高预测准确性',
                accuracy_range=(0.70, 0.95),
                speed_class='medium',
                memory_usage=512,
                suitable_conditions=[
                    MarketCondition.NORMAL,
                    MarketCondition.HIGH_VOLATILITY,
                    MarketCondition.STRONG_TREND
                ],
                data_requirements={
                    'quality': 'high',
                    'min_samples': 500,
                    'features': ['open', 'high', 'low', 'close', 'volume']
                },
                features=[
                    '多模型融合',
                    '提高准确性',
                    '降低方差',
                    '稳健性强'
                ],
                hyperparameters={
                    'base_models': ['lstm', 'xgboost', 'gru'],
                    'fusion_method': 'weighted_average',
                    'weight_update': True
                },
                prediction_horizon=20,
                confidence_threshold=0.80
            )
        }
    
    def get_profile(self, model_type: str) -> ModelProfile:
        """获取模型档案"""
        return self.profiles.get(model_type)
    
    def get_all_profiles(self) -> Dict[str, ModelProfile]:
        """获取所有模型档案"""
        return self.profiles.copy()
    
    def get_suitable_models(self, market_condition: MarketCondition, 
                          data_quality: str) -> List[str]:
        """获取适合当前条件的模型列表"""
        suitable_models = []
        for model_type, profile in self.profiles.items():
            if profile.is_suitable_for(market_condition, data_quality):
                suitable_models.append(model_type)
        return suitable_models
    
    def get_model_info(self, model_type: str) -> Dict[str, Any]:
        """获取模型详细信息"""
        profile = self.get_profile(model_type)
        if not profile:
            return {}
        
        return {
            'name': profile.name,
            'description': profile.description,
            'accuracy_range': profile.accuracy_range,
            'speed_class': profile.speed_class,
            'memory_usage': profile.memory_usage,
            'suitable_conditions': [c.value for c in profile.suitable_conditions],
            'features': profile.features,
            'prediction_horizon': profile.prediction_horizon,
            'confidence_threshold': profile.confidence_threshold
        }


def get_predefined_model_profiles() -> Dict[str, ModelProfile]:
    """获取预定义的模型档案"""
    profiles_manager = ModelProfiles()
    return profiles_manager.get_all_profiles()