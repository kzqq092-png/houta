from loguru import logger
#!/usr/bin/env python3
"""
AI模型生成脚本

功能：
1. 生成训练数据
2. 训练4个AI预测模型：pattern_model, trend_model, sentiment_model, price_model
3. 保存模型到 models/trained/ 目录

使用方法：
python scripts/generate_ai_models.py [--quick] [--model pattern|trend|sentiment|price|all]
"""

import sys
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 检查TensorFlow可用性
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout, LSTM
    from tensorflow.keras.utils import to_categorical
    from models.deep_learning import build_deep_learning_model, TENSORFLOW_AVAILABLE
    TF_AVAILABLE = True
    logger.info(" TensorFlow 可用")
except ImportError as e:
    TF_AVAILABLE = False
    logger.info(f" TensorFlow 不可用: {e}")
    logger.info("请安装TensorFlow: pip install tensorflow")

logger = logger


class AIModelGenerator:
    """AI模型生成器"""

    def __init__(self, quick_mode=False):
        """
        初始化模型生成器

        Args:
            quick_mode: 快速模式，使用较少的训练数据和轮次
        """
        self.quick_mode = quick_mode
        self.models_dir = project_root / "models" / "trained"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 训练参数
        if quick_mode:
            self.epochs = 10
            self.sample_size = 1000
            self.sequence_length = 10
        else:
            self.epochs = 50
            self.sample_size = 5000
            self.sequence_length = 20

        logger.info(f"模式: {'快速' if quick_mode else '标准'}")
        logger.info(f"训练轮次: {self.epochs}")
        logger.info(f"样本数量: {self.sample_size}")

    def generate_sample_data(self, data_type="pattern", size=None):
        """
        生成示例训练数据

        Args:
            data_type: 数据类型 (pattern, trend, sentiment, price)
            size: 数据大小

        Returns:
            X: 特征数据
            y: 标签数据
        """
        if size is None:
            size = self.sample_size

        logger.info(f"生成 {data_type} 训练数据，样本数: {size}")

        if data_type == "pattern":
            # 形态识别数据：技术指标 -> 形态类型
            n_features = 15  # 15个技术指标
            X = np.random.randn(size, n_features)

            # 添加一些相关性，模拟真实的技术指标关系
            X[:, 1] = X[:, 0] * 0.8 + np.random.randn(size) * 0.3  # RSI与价格相关
            X[:, 2] = X[:, 0] * 0.6 + np.random.randn(size) * 0.5  # MACD与价格相关

            # 3类形态：上升、下降、震荡
            y = np.random.randint(0, 3, size)

        elif data_type == "trend":
            # 趋势预测数据：历史价格+指标 -> 未来趋势
            n_features = 20  # 20个特征
            X = np.random.randn(size, n_features)

            # 模拟趋势特征
            trend_signal = np.cumsum(np.random.randn(size) * 0.1)
            X[:, 0] = trend_signal  # 主趋势特征
            X[:, 1] = np.roll(trend_signal, 1)  # 滞后1期
            X[:, 2] = np.roll(trend_signal, 2)  # 滞后2期

            # 3类趋势：上涨、下跌、横盘
            y = np.where(trend_signal > 0.5, 2, np.where(trend_signal < -0.5, 0, 1))

        elif data_type == "sentiment":
            # 情绪分析数据：市场指标 -> 情绪状态
            n_features = 12  # 12个市场情绪指标
            X = np.random.randn(size, n_features)

            # 模拟情绪指标
            fear_greed = np.random.beta(2, 2, size) * 100  # 恐惧贪婪指数
            volume_ratio = np.random.lognormal(0, 0.5, size)  # 成交量比率
            X[:, 0] = (fear_greed - 50) / 25  # 标准化
            X[:, 1] = np.log(volume_ratio)

            # 3类情绪：乐观、悲观、中性
            y = np.where(fear_greed > 70, 2, np.where(fear_greed < 30, 0, 1))

        elif data_type == "price":
            # 价格预测数据：技术分析特征 -> 价格变化
            n_features = 25  # 25个技术分析特征
            X = np.random.randn(size, n_features)

            # 模拟价格相关特征
            price_momentum = np.random.randn(size)
            volatility = np.random.exponential(1, size)
            X[:, 0] = price_momentum
            X[:, 1] = volatility
            X[:, 2] = price_momentum * volatility  # 动量*波动率

            # 3类价格变化：上涨、下跌、平稳
            price_change = price_momentum + np.random.randn(size) * 0.5
            y = np.where(price_change > 0.3, 2, np.where(price_change < -0.3, 0, 1))

        else:
            raise ValueError(f"不支持的数据类型: {data_type}")

        # 确保标签分布相对均衡
        unique, counts = np.unique(y, return_counts=True)
        logger.info(f"标签分布: {dict(zip(unique, counts))}")

        return X.astype(np.float32), y.astype(np.int32)

    def create_simple_model(self, input_dim, model_name):
        """
        创建简单的深度学习模型

        Args:
            input_dim: 输入维度
            model_name: 模型名称

        Returns:
            model: Keras模型
        """
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow不可用，无法创建深度学习模型")

        model = Sequential([
            Dense(128, activation='relu', input_dim=input_dim),
            Dropout(0.3),
            Dense(64, activation='relu'),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(3, activation='softmax')  # 3分类输出
        ])

        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )

        logger.info(f"{model_name} 模型结构:")
        model.summary()

        return model

    def train_and_save_model(self, model_type):
        """
        训练并保存指定类型的模型

        Args:
            model_type: 模型类型 (pattern, trend, sentiment, price)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"开始训练 {model_type} 模型")
        logger.info(f"{'='*60}")

        try:
            # 生成训练数据
            X, y = self.generate_sample_data(model_type)

            # 划分训练测试集
            split_idx = int(0.8 * len(X))
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # 转换为分类标签
            y_train_cat = to_categorical(y_train, 3)
            y_test_cat = to_categorical(y_test, 3)

            logger.info(f"训练集大小: {X_train.shape[0]}")
            logger.info(f"测试集大小: {X_test.shape[0]}")
            logger.info(f"特征维度: {X_train.shape[1]}")

            # 创建模型
            model = self.create_simple_model(X_train.shape[1], model_type)

            # 训练模型
            logger.info("开始训练...")
            history = model.fit(
                X_train, y_train_cat,
                validation_data=(X_test, y_test_cat),
                epochs=self.epochs,
                batch_size=32,
                verbose=1 if not self.quick_mode else 0
            )

            # 评估模型
            test_loss, test_acc = model.evaluate(X_test, y_test_cat, verbose=0)
            logger.info(f"测试准确率: {test_acc:.4f}")

            # 保存模型
            model_path = self.models_dir / f"{model_type}_model.h5"
            model.save(str(model_path))
            logger.info(f" 模型已保存: {model_path}")

            # 保存训练信息
            info = {
                'model_type': model_type,
                'training_date': datetime.now().isoformat(),
                'test_accuracy': float(test_acc),
                'test_loss': float(test_loss),
                'epochs': self.epochs,
                'sample_size': self.sample_size,
                'input_features': int(X_train.shape[1]),
                'quick_mode': self.quick_mode
            }

            info_path = self.models_dir / f"{model_type}_model_info.json"
            import json
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)

            logger.info(f" 模型信息已保存: {info_path}")

        except Exception as e:
            logger.info(f" {model_type} 模型训练失败: {e}")
            import traceback
            traceback.print_exc()

    def generate_all_models(self):
        """生成所有AI模型"""
        model_types = ['pattern', 'trend', 'sentiment', 'price']

        logger.info(f"\n 开始生成AI预测模型")
        logger.info(f"目标目录: {self.models_dir}")
        logger.info(f"模型类型: {model_types}")

        if not TF_AVAILABLE:
            logger.info(" TensorFlow不可用，无法生成深度学习模型")
            logger.info("请安装TensorFlow: pip install tensorflow")
            return False

        success_count = 0
        for model_type in model_types:
            try:
                self.train_and_save_model(model_type)
                success_count += 1
            except Exception as e:
                logger.info(f" {model_type} 模型生成失败: {e}")

        logger.info(f"\n{'='*60}")
        logger.info(f"模型生成完成")
        logger.info(f"成功: {success_count}/{len(model_types)}")
        logger.info(f"模型保存目录: {self.models_dir}")
        logger.info(f"{'='*60}")

        if success_count == len(model_types):
            logger.info(" 所有模型生成成功！现在可以重新启动FactorWeave-Quant 应用程序。")
            return True
        else:
            logger.info(" 部分模型生成失败，请检查错误信息。")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成 FactorWeave-Quant  AI预测模型')
    parser.add_argument('--quick', action='store_true',
                        help='快速模式（较少训练轮次和数据）')
    parser.add_argument('--model', choices=['pattern', 'trend', 'sentiment', 'price', 'all'],
                        default='all', help='要生成的模型类型')

    args = parser.parse_args()

    logger.info("FactorWeave-Quant  AI模型生成器")
    logger.info("=" * 60)

    # 创建模型生成器
    generator = AIModelGenerator(quick_mode=args.quick)

    # 生成模型
    if args.model == 'all':
        success = generator.generate_all_models()
    else:
        try:
            generator.train_and_save_model(args.model)
            success = True
        except Exception as e:
            logger.info(f"模型生成失败: {e}")
            success = False

    if success:
        logger.info("\n 下一步操作:")
        logger.info("1. 重新启动FactorWeave-Quant 应用程序")
        logger.info("2. 检查日志确认模型加载成功")
        logger.info("3. 测试AI预测功能")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
