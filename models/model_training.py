from utils.imports import np, pd, sklearn_metrics, sklearn_model_selection

# 获取sklearn子模块中的具体类和函数
if sklearn_metrics:
    accuracy_score = getattr(sklearn_metrics, 'accuracy_score', None)
    precision_score = getattr(sklearn_metrics, 'precision_score', None)
    recall_score = getattr(sklearn_metrics, 'recall_score', None)
    f1_score = getattr(sklearn_metrics, 'f1_score', None)
    confusion_matrix = getattr(sklearn_metrics, 'confusion_matrix', None)

if sklearn_model_selection:
    GridSearchCV = getattr(sklearn_model_selection, 'GridSearchCV', None)
    cross_val_score = getattr(sklearn_model_selection, 'cross_val_score', None)
    StratifiedKFold = getattr(sklearn_model_selection, 'StratifiedKFold', None)

# 获取sklearn其他模块
from utils.imports import get_sklearn
_sklearn_modules = get_sklearn()

# 获取ensemble模块
sklearn_ensemble = _sklearn_modules.get(
    'ensemble') if _sklearn_modules else None
if sklearn_ensemble:
    RandomForestClassifier = getattr(
        sklearn_ensemble, 'RandomForestClassifier', None)
    GradientBoostingClassifier = getattr(
        sklearn_ensemble, 'GradientBoostingClassifier', None)
    StackingClassifier = getattr(sklearn_ensemble, 'StackingClassifier', None)
    VotingClassifier = getattr(sklearn_ensemble, 'VotingClassifier', None)

# 获取linear_model模块
sklearn_linear_model = _sklearn_modules.get(
    'linear_model') if _sklearn_modules else None
if sklearn_linear_model:
    LogisticRegression = getattr(
        sklearn_linear_model, 'LogisticRegression', None)

# 获取svm模块
sklearn_svm = _sklearn_modules.get('svm') if _sklearn_modules else None
if sklearn_svm:
    SVC = getattr(sklearn_svm, 'SVC', None)

def train_enhanced_model(X_train, y_train):
    """
    训练增强型机器学习模型

    参数:
        X_train: 训练特征数据
        y_train: 训练标签数据

    返回:
        model: 训练好的模型
        feature_importance: 特征重要性信息（如果可用）
    """
    # 设置随机种子以确保可重复性
    np.random.seed(42)

    # 检查数据
    print(f"训练数据形状: X={X_train.shape}, y={y_train.shape}")
    print(f"类别分布: {np.bincount(y_train)}")

    # 选择最佳模型架构
    # 1. 基础模型定义
    base_models = []

    # 随机森林
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=None,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        bootstrap=True,
        class_weight='balanced',
        random_state=42
    )
    base_models.append(('rf', rf_model))

    # 梯度提升树
    gb_model = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        random_state=42
    )
    base_models.append(('gb', gb_model))

    # 支持向量机（只用于小数据集）
    if X_train.shape[0] < 10000:  # 根据数据大小决定是否使用SVM
        svm_model = SVC(
            probability=True,
            kernel='rbf',
            C=1.0,
            gamma='scale',
            class_weight='balanced',
            random_state=42
        )
        base_models.append(('svm', svm_model))

    # 2. 创建集成模型
    # 尝试加载可选的高级模型
    try:
        from lightgbm import LGBMClassifier
        lgbm_model = LGBMClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            num_leaves=31,
            min_child_samples=20,
            random_state=42,
            class_weight='balanced'
        )
        base_models.append(('lgbm', lgbm_model))
    except ImportError:
        print("Warning: LightGBM 未安装，跳过该模型")

    try:
        from xgboost import XGBClassifier
        xgb_model = XGBClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            min_child_weight=1,
            gamma=0,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='multi:softproba',
            num_class=3,  # 适用于三类分类问题（-1, 0, 1）
            random_state=42
        )
        base_models.append(('xgb', xgb_model))
    except ImportError:
        print("Warning: XGBoost 未安装，跳过该模型")

    try:
        from catboost import CatBoostClassifier
        cat_model = CatBoostClassifier(
            iterations=100,
            learning_rate=0.1,
            depth=6,
            l2_leaf_reg=3,
            random_seed=42,
            verbose=0
        )
        base_models.append(('cat', cat_model))
    except ImportError:
        print("Warning: CatBoost 未安装，跳过该模型")

    # 构建堆叠和投票集成
    if len(base_models) >= 3:
        print("创建集成模型...")
        # 定义元模型
        meta_model = LogisticRegression(
            max_iter=1000, class_weight='balanced', random_state=42)

        # 创建堆叠集成
        stacking_model = StackingClassifier(
            estimators=base_models,
            final_estimator=meta_model,
            cv=5,
            stack_method='predict_proba'
        )

        # 创建投票集成
        voting_model = VotingClassifier(
            estimators=base_models,
            voting='soft',
            weights=[1] * len(base_models)
        )

        # 将集成模型添加到候选列表
        ensemble_models = [
            ('stacking', stacking_model),
            ('voting', voting_model)
        ]

        # 根据数据量大小选择最终模型
        if X_train.shape[0] > 5000:
            # 对于大数据集，使用简单投票模型以避免过长的训练时间
            print("使用投票集成模型进行训练...")
            final_model = voting_model
        else:
            # 对于小数据集，使用堆叠集成获得更好的性能
            print("使用堆叠集成模型进行训练...")
            final_model = stacking_model
    else:
        # 如果没有足够的基础模型，使用随机森林作为备选
        print("没有足够的基础模型可用，使用随机森林...")
        final_model = rf_model

    # 训练最终模型
    print("开始训练模型...")
    try:
        final_model.fit(X_train, y_train)
        print("模型训练完成！")
    except Exception as e:
        print(f"模型训练出错: {e}")
        print("回退到随机森林模型...")
        final_model = RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight='balanced')
        final_model.fit(X_train, y_train)

    # 计算模型评估指标
    try:
        cv_scores = cross_val_score(
            final_model, X_train, y_train, cv=5, scoring='accuracy')
        print(f"交叉验证平均准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    except Exception as e:
        print(f"交叉验证出错: {e}")

    # 提取特征重要性（如果可用）
    feature_importance = None
    if hasattr(final_model, 'feature_importances_'):
        feature_importance = final_model.feature_importances_
    elif hasattr(final_model, 'coef_'):
        feature_importance = final_model.coef_[0]
    elif hasattr(final_model, 'estimators_'):
        # 对于集成模型，尝试从第一个具有feature_importances_的基础模型获取
        for name, estimator in base_models:
            if hasattr(estimator, 'feature_importances_'):
                estimator.fit(X_train, y_train)  # 需要先拟合模型
                feature_importance = estimator.feature_importances_
                break

    return final_model, feature_importance

def prevent_overfitting(X_train, y_train, X_test, y_test):
    """
    防止模型过拟合的技术

    参数:
        X_train: 训练特征数据
        y_train: 训练标签数据
        X_test: 测试特征数据
        y_test: 测试标签数据

    返回:
        model: 防过拟合的模型
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import GridSearchCV, train_test_split

    # 划分验证集
    X_train_sub, X_val, y_train_sub, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )

    # 初始化基础模型
    base_model = RandomForestClassifier(
        random_state=42, class_weight='balanced')

    # 设置参数网格
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [None, 10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
    }

    # 使用GridSearchCV找到最佳参数
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=param_grid,
        cv=5,
        scoring='accuracy',
        n_jobs=-1,
        verbose=0
    )

    # 在训练子集上拟合网格搜索
    grid_search.fit(X_train_sub, y_train_sub)

    # 获取最佳参数
    best_params = grid_search.best_params_
    print("最佳参数:", best_params)

    # 使用最佳参数创建模型
    best_model = RandomForestClassifier(
        **best_params,
        random_state=42,
        class_weight='balanced'
    )

    # 在完整训练集上训练模型
    best_model.fit(X_train, y_train)

    # 评估在验证集和测试集上的性能
    val_accuracy = best_model.score(X_val, y_val)
    test_accuracy = best_model.score(X_test, y_test)

    print(f"验证集准确率: {val_accuracy:.4f}")
    print(f"测试集准确率: {test_accuracy:.4f}")

    # 检查过拟合（训练集准确率显著高于测试集）
    train_accuracy = best_model.score(X_train, y_train)
    print(f"训练集准确率: {train_accuracy:.4f}")

    if train_accuracy - test_accuracy > 0.1:
        print("检测到可能的过拟合，应用正则化...")

        # 通过降低复杂度来增加正则化
        regularized_params = best_params.copy()

        # 如果max_depth不是None，减少它
        if regularized_params.get('max_depth') is not None:
            regularized_params['max_depth'] = max(
                5, regularized_params['max_depth'] // 2)

        # 增加min_samples_split和min_samples_leaf以减少复杂度
        regularized_params['min_samples_split'] = min(
            20, regularized_params.get('min_samples_split', 2) * 2)
        regularized_params['min_samples_leaf'] = min(
            10, regularized_params.get('min_samples_leaf', 1) * 2)

        # 使用正则化参数创建新模型
        regularized_model = RandomForestClassifier(
            **regularized_params,
            random_state=42,
            class_weight='balanced'
        )

        # 训练正则化模型
        regularized_model.fit(X_train, y_train)

        # 评估正则化模型
        reg_train_accuracy = regularized_model.score(X_train, y_train)
        reg_test_accuracy = regularized_model.score(X_test, y_test)

        print(f"正则化后训练集准确率: {reg_train_accuracy:.4f}")
        print(f"正则化后测试集准确率: {reg_test_accuracy:.4f}")

        # 判断正则化是否有效（减少了过拟合同时保持了合理的测试性能）
        if (train_accuracy - reg_train_accuracy > 0.05) and (reg_test_accuracy >= test_accuracy - 0.02):
            print("正则化成功，使用正则化模型")
            return regularized_model

    # 如果没有过拟合或正则化不成功，返回原始最佳模型
    return best_model
