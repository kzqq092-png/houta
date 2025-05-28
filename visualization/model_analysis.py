import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc, precision_recall_curve
import logging

logger = logging.getLogger(__name__)


class ModelAnalysis:
    def __init__(self):
        pass

    def plot_feature_importance_comparison(self, feature_importances_list, model_names,
                                           feature_names, top_n=15, figsize=(12, 10)):
        """
        比较多个模型的特征重要性

        参数:
            feature_importances_list: list，多个模型的特征重要性数组列表
            model_names: list，模型名称列表
            feature_names: list，特征名称列表
            top_n: int，显示前N个重要特征
            figsize: tuple，图形大小
        """
        try:
            if len(feature_importances_list) != len(model_names):
                raise ValueError("特征重要性列表和模型名称列表长度不匹配")

            # 创建特征重要性DataFrame
            dfs = []
            for i, importances in enumerate(feature_importances_list):
                if len(importances) != len(feature_names):
                    raise ValueError(f"模型 {model_names[i]} 的特征重要性长度与特征名称不匹配")

                df = pd.DataFrame({
                    'Feature': feature_names,
                    'Importance': importances,
                    'Model': model_names[i]
                })
                dfs.append(df)

            combined_df = pd.concat(dfs)

            # 获取每个模型的前N个重要特征
            top_features = set()
            for model in model_names:
                model_df = combined_df[combined_df['Model'] == model]
                top_model_features = model_df.nlargest(
                    top_n, 'Importance')['Feature'].values
                top_features.update(top_model_features)

            # 过滤数据只包含前N个特征
            filtered_df = combined_df[combined_df['Feature'].isin(
                top_features)]

            # 创建图形
            plt.figure(figsize=figsize)

            # 使用seaborn绘制条形图
            ax = sns.barplot(x='Importance', y='Feature',
                             hue='Model', data=filtered_df)

            # 设置标题和标签
            plt.title('Feature Importance Comparison Across Models', fontsize=15)
            plt.xlabel('Importance')
            plt.ylabel('Feature')

            # 调整图例位置
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制特征重要性比较图失败: {str(e)}")
            raise

    def plot_signal_over_time(self, df, signal_col='signal', figsize=(15, 8)):
        """
        绘制信号随时间变化的热力图

        参数:
            df: DataFrame，包含信号数据
            signal_col: str，信号列名
            figsize: tuple，图形大小
        """
        try:
            if signal_col not in df.columns:
                raise ValueError(f"DataFrame中缺少信号列: {signal_col}")

            # 确保索引是日期类型
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError("DataFrame的索引必须是日期类型")

            # 创建包含年月信息的DataFrame
            signal_df = pd.DataFrame({
                'year': df.index.year,
                'month': df.index.month,
                'signal': df[signal_col]
            })

            # 按年月分组统计信号数量
            pivot_buy = signal_df[signal_df['signal'] == 1].groupby(
                ['year', 'month']).size().unstack(fill_value=0)
            pivot_sell = signal_df[signal_df['signal'] == -
                                   1].groupby(['year', 'month']).size().unstack(fill_value=0)

            # 计算信号比例（买-卖）/总量
            pivot_ratio = (pivot_buy - pivot_sell) / \
                (pivot_buy + pivot_sell + 1e-10)  # 添加小数避免除零

            # 创建图形
            fig, ax = plt.subplots(figsize=figsize)

            # 绘制热力图
            cmap = plt.cm.RdYlGn  # 红色表示多卖出，绿色表示多买入
            im = ax.imshow(pivot_ratio, cmap=cmap,
                           aspect='auto', vmin=-1, vmax=1)

            # 设置坐标轴标签
            ax.set_xticks(np.arange(len(pivot_ratio.columns)))
            ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
            ax.set_yticks(np.arange(len(pivot_ratio.index)))
            ax.set_yticklabels(pivot_ratio.index)

            # 添加标题
            plt.title('Signal Distribution Over Time', fontsize=15)

            # 添加颜色条
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Signal Ratio (Buy - Sell) / Total')

            # 在每个单元格添加文本
            for i in range(len(pivot_ratio.index)):
                for j in range(len(pivot_ratio.columns)):
                    buy_count = pivot_buy.iloc[i, j]
                    sell_count = pivot_sell.iloc[i, j]
                    text = f"{buy_count}-{sell_count}"
                    ax.text(j, i, text, ha="center",
                            va="center", color="black")

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制信号时间分布图失败: {str(e)}")
            raise

    def plot_model_performance(self, performance_metrics, model_names, figsize=(12, 8)):
        """
        绘制模型性能比较图

        参数:
            performance_metrics: dict，包含各个模型的性能指标
            model_names: list，模型名称列表
            figsize: tuple，图形大小
        """
        try:
            # 创建图形
            fig, axes = plt.subplots(2, 2, figsize=figsize)
            axes = axes.flatten()

            # 绘制准确率
            accuracy = [performance_metrics[model]['accuracy']
                        for model in model_names]
            axes[0].bar(model_names, accuracy, color='blue')
            axes[0].set_title('Accuracy')
            axes[0].set_ylim(0, 1)

            # 绘制精确率
            precision = [performance_metrics[model]['precision']
                         for model in model_names]
            axes[1].bar(model_names, precision, color='green')
            axes[1].set_title('Precision')
            axes[1].set_ylim(0, 1)

            # 绘制召回率
            recall = [performance_metrics[model]['recall']
                      for model in model_names]
            axes[2].bar(model_names, recall, color='red')
            axes[2].set_title('Recall')
            axes[2].set_ylim(0, 1)

            # 绘制F1分数
            f1 = [performance_metrics[model]['f1'] for model in model_names]
            axes[3].bar(model_names, f1, color='purple')
            axes[3].set_title('F1 Score')
            axes[3].set_ylim(0, 1)

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制模型性能比较图失败: {str(e)}")
            raise

    def plot_learning_curve(self, train_sizes, train_scores, test_scores,
                            title='Learning Curve', figsize=(10, 6)):
        """
        绘制学习曲线

        参数:
            train_sizes: array-like，训练集大小
            train_scores: array-like，训练集得分
            test_scores: array-like，测试集得分
            title: str，图表标题
            figsize: tuple，图形大小
        """
        try:
            plt.figure(figsize=figsize)

            # 计算均值和标准差
            train_mean = np.mean(train_scores, axis=1)
            train_std = np.std(train_scores, axis=1)
            test_mean = np.mean(test_scores, axis=1)
            test_std = np.std(test_scores, axis=1)

            # 绘制训练集得分
            plt.plot(train_sizes, train_mean, 'o-',
                     color='r', label='Training score')
            plt.fill_between(train_sizes, train_mean - train_std,
                             train_mean + train_std, alpha=0.1, color='r')

            # 绘制测试集得分
            plt.plot(train_sizes, test_mean, 'o-', color='g',
                     label='Cross-validation score')
            plt.fill_between(train_sizes, test_mean - test_std,
                             test_mean + test_std, alpha=0.1, color='g')

            # 设置标题和标签
            plt.title(title)
            plt.xlabel('Training examples')
            plt.ylabel('Score')
            plt.legend(loc='best')
            plt.grid(True)

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制学习曲线失败: {str(e)}")
            raise

    def plot_roc_curve(self, y_true, y_scores, title='ROC Curve', figsize=(8, 6)):
        """
        绘制ROC曲线

        参数:
            y_true: array-like，真实标签
            y_scores: array-like，预测概率
            title: str，图表标题
            figsize: tuple，图形大小
        """
        try:
            # 计算ROC曲线
            fpr, tpr, _ = roc_curve(y_true, y_scores)
            roc_auc = auc(fpr, tpr)

            # 创建图形
            plt.figure(figsize=figsize)

            # 绘制ROC曲线
            plt.plot(fpr, tpr, color='darkorange', lw=2,
                     label=f'ROC curve (AUC = {roc_auc:.2f})')

            # 绘制对角线
            plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')

            # 设置标题和标签
            plt.title(title)
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.legend(loc='lower right')
            plt.grid(True)

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制ROC曲线失败: {str(e)}")
            raise

    def plot_precision_recall_curve(self, y_true, y_scores, title='Precision-Recall Curve',
                                    figsize=(8, 6)):
        """
        绘制精确率-召回率曲线

        参数:
            y_true: array-like，真实标签
            y_scores: array-like，预测概率
            title: str，图表标题
            figsize: tuple，图形大小
        """
        try:
            # 计算精确率-召回率曲线
            precision, recall, _ = precision_recall_curve(y_true, y_scores)

            # 创建图形
            plt.figure(figsize=figsize)

            # 绘制精确率-召回率曲线
            plt.plot(recall, precision, color='blue', lw=2,
                     label='Precision-Recall curve')

            # 设置标题和标签
            plt.title(title)
            plt.xlabel('Recall')
            plt.ylabel('Precision')
            plt.legend(loc='lower left')
            plt.grid(True)

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制精确率-召回率曲线失败: {str(e)}")
            raise

    def plot_prediction_distribution(self, y_true, y_pred, title='Prediction Distribution',
                                     figsize=(10, 6)):
        """
        绘制预测分布图

        参数:
            y_true: array-like，真实标签
            y_pred: array-like，预测标签
            title: str，图表标题
            figsize: tuple，图形大小
        """
        try:
            # 创建图形
            fig, axes = plt.subplots(1, 2, figsize=figsize)

            # 绘制真实标签分布
            sns.countplot(x=y_true, ax=axes[0])
            axes[0].set_title('True Label Distribution')

            # 绘制预测标签分布
            sns.countplot(x=y_pred, ax=axes[1])
            axes[1].set_title('Predicted Label Distribution')

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制预测分布图失败: {str(e)}")
            raise

    def plot_error_analysis(self, y_true, y_pred, features, top_n=10, figsize=(12, 8)):
        """
        绘制错误分析图

        参数:
            y_true: array-like，真实标签
            y_pred: array-like，预测标签
            features: DataFrame，特征数据
            top_n: int，显示前N个重要特征
            figsize: tuple，图形大小
        """
        try:
            # 计算错误样本
            errors = y_true != y_pred

            # 计算错误样本的特征均值
            error_features = features[errors].mean()

            # 计算所有样本的特征均值
            all_features = features.mean()

            # 计算特征差异
            feature_diff = (error_features - all_features).abs()

            # 获取前N个差异最大的特征
            top_features = feature_diff.nlargest(top_n)

            # 创建图形
            plt.figure(figsize=figsize)

            # 绘制条形图
            plt.barh(top_features.index, top_features.values)

            # 设置标题和标签
            plt.title('Top Features Contributing to Prediction Errors')
            plt.xlabel('Feature Value Difference')
            plt.ylabel('Feature')

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制错误分析图失败: {str(e)}")
            raise
