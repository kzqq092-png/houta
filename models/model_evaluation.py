import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from loguru import logger
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report,
                             roc_curve, auc, precision_recall_curve)

def evaluate_ml_model(model, X_test, y_test, predictions=None):
    """
    评估机器学习模型的性能

    参数:
        model: 训练好的模型
        X_test: 测试特征数据
        y_test: 测试标签数据
        predictions: 预测结果（如果为None则调用model.predict）

    返回:
        metrics_dict: 包含各种评估指标的字典
    """
    # 如果未提供预测结果，则使用模型进行预测
    if predictions is None:
        predictions = model.predict(X_test)

    # 计算基本指标
    accuracy = accuracy_score(y_test, predictions)

    # 多分类使用average参数
    precision = precision_score(y_test, predictions, average='weighted')
    recall = recall_score(y_test, predictions, average='weighted')
    f1 = f1_score(y_test, predictions, average='weighted')

    # 计算混淆矩阵
    cm = confusion_matrix(y_test, predictions)

    # 归一化混淆矩阵
    cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    # 保存基本指标到字典
    metrics_dict = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'confusion_matrix': cm,
        'confusion_matrix_normalized': cm_normalized
    }

    # 尝试计算类别概率（如果模型支持）
    try:
        # 对于三分类问题（-1, 0, 1）
        class_labels = np.unique(y_test)
        class_probs = model.predict_proba(X_test)

        # 保存ROC数据
        roc_data = {}
        for i, label in enumerate(model.classes_):
            if label == -1:  # 卖出信号
                fpr, tpr, _ = roc_curve(y_test == label, class_probs[:, i])
                roc_auc = auc(fpr, tpr)
                roc_data['sell'] = {'fpr': fpr, 'tpr': tpr, 'auc': roc_auc}
            elif label == 1:  # 买入信号
                fpr, tpr, _ = roc_curve(y_test == label, class_probs[:, i])
                roc_auc = auc(fpr, tpr)
                roc_data['buy'] = {'fpr': fpr, 'tpr': tpr, 'auc': roc_auc}

        metrics_dict['roc_data'] = roc_data
        metrics_dict['class_probs'] = class_probs
    except (AttributeError, ValueError) as e:
        logger.info(f"无法计算概率指标: {e}")

    # 打印分类报告
    logger.info("\n分类报告:")
    logger.info(f"{classification_report(y_test, predictions)}")

    # 打印主要指标
    logger.info(f"\n准确率: {accuracy:.4f}")
    logger.info(f"精确率: {precision:.4f}")
    logger.info(f"召回率: {recall:.4f}")
    logger.info(f"F1分数: {f1:.4f}")

    # 打印混淆矩阵
    logger.info("\n混淆矩阵:")
    logger.info(cm)

    # 返回指标字典
    return metrics_dict

def analyze_feature_importance(model, feature_names, top_n=20):
    """
    分析特征重要性

    参数:
        model: 训练好的模型
        feature_names: 特征名称列表
        top_n: 显示前N个重要特征

    返回:
        feature_importance_df: 包含特征重要性的DataFrame
    """
    # 检查模型是否具有特征重要性属性
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importances = np.abs(model.coef_[0])  # 对于线性模型，使用系数的绝对值
    else:
        logger.info("该模型不支持直接提取特征重要性")
        return None

    # 创建特征重要性DataFrame
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    })

    # 按重要性排序
    feature_importance = feature_importance.sort_values(
        'importance', ascending=False)

    # 显示前N个特征
    top_features = feature_importance.head(top_n)

    logger.info(f"\n前{top_n}个重要特征:")
    for i, (index, row) in enumerate(top_features.iterrows()):
        logger.info(f"{i+1}. {row['feature']}: {row['importance']:.4f}")

    # 绘制特征重要性图
    plt.figure(figsize=(10, 8))
    plt.barh(top_features['feature'], top_features['importance'])
    plt.xlabel('重要性')
    plt.ylabel('特征名称')
    plt.title('特征重要性排名')
    plt.tight_layout()

    # 保存图像（可选）
    plt.savefig('feature_importance.png', dpi=300, bbox_inches='tight')

    return feature_importance
