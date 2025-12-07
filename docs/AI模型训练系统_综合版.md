# AI模型训练系统_综合版

## 📋 执行摘要

本报告整合了AI模型训练工具和预测准确性跟踪系统的设计方案、审查报告和开发计划，为交易系统提供完整的AI模型训练、预测跟踪和质量评估解决方案。

**核心目标**：建立完整的AI模型训练生态系统，支持多种机器学习算法，实现模型版本管理和预测准确性跟踪。

**系统架构**：基于现有服务容器架构，采用事件驱动设计，确保与现有系统的无缝集成。

---

## 🏗️ 系统架构设计

### 1. 整体架构

#### 服务层架构
```python
class UnifiedAIServiceContainer:
    """统一AI服务容器"""
    
    def __init__(self):
        # 核心服务
        self.model_training_service = ModelTrainingService()
        self.prediction_tracking_service = PredictionTrackingService()
        self.quality_assessment_service = QualityAssessmentService()
        self.model_version_service = ModelVersionService()
        
        # 集成服务
        self.event_bus = EventBus()
        self.database_service = DatabaseService()
        self.cache_service = CacheService()
        self.monitoring_service = MonitoringService()
```

#### 核心服务设计

**1. ModelTrainingService - 模型训练服务**
```python
class ModelTrainingService(BaseService):
    """模型训练服务"""
    
    async def create_training_task(self, task_config: TrainingTaskConfig) -> str:
        """创建训练任务"""
        # 参数验证
        self._validate_task_config(task_config)
        
        # 生成任务ID
        task_id = f"train_{uuid.uuid4().hex[:8]}"
        
        # 保存任务配置
        await self._save_training_task(task_id, task_config)
        
        # 初始化任务状态
        await self._init_task_status(task_id)
        
        logger.info(f"创建训练任务成功: {task_id}")
        return task_id
    
    async def execute_training_task(self, task_id: str):
        """执行训练任务"""
        # 获取任务配置
        task_config = await self._get_training_task(task_id)
        if not task_config:
            raise ValueError(f"训练任务不存在: {task_id}")
        
        # 更新任务状态为运行中
        await self._update_task_status(task_id, TaskStatus.RUNNING)
        
        try:
            # 准备训练数据
            train_data, eval_data = await self._prepare_training_data(task_config)
            
            # 初始化模型
            model = self._initialize_model(task_config.model_type, task_config.model_params)
            
            # 创建训练线程
            training_thread = TrainingThread(
                model=model,
                train_data=train_data,
                eval_data=eval_data,
                params=task_config.training_params,
                callback=self._training_progress_callback(task_id)
            )
            
            # 启动训练
            training_thread.start()
            
            # 等待训练完成
            while training_thread.is_alive():
                await asyncio.sleep(1)
            
            # 获取训练结果
            training_result = training_thread.get_result()
            
            # 评估模型
            eval_metrics = await self._evaluate_model(model, eval_data)
            
            # 保存模型版本
            model_version = await self._save_model_version(
                task_id, model, training_result, eval_metrics
            )
            
            # 更新任务状态为完成
            await self._update_task_status(
                task_id, 
                TaskStatus.COMPLETED,
                result={
                    "model_version": model_version,
                    "metrics": eval_metrics
                }
            )
            
        except Exception as e:
            logger.error(f"训练任务执行失败: {str(e)}", exc_info=True)
            await self._update_task_status(
                task_id, 
                TaskStatus.FAILED,
                error=str(e)
            )
```

**2. PredictionTrackingService - 预测跟踪服务**
```python
class PredictionTrackingService(BaseService):
    """预测跟踪服务"""
    
    def __init__(self):
        self.prediction_buffer = {}
        self.tracking_metrics = {}
        self.performance_monitor = PerformanceMonitor()
    
    async def track_prediction(self, 
                             model_version: str,
                             prediction_input: Any,
                             prediction_output: Any,
                             actual_result: Any = None):
        """跟踪预测结果"""
        
        # 创建跟踪记录
        tracking_record = PredictionRecord(
            model_version=model_version,
            timestamp=datetime.now(),
            input_data=prediction_input,
            predicted_value=prediction_output,
            actual_value=actual_result,
            tracking_id=str(uuid.uuid4())
        )
        
        # 保存到缓冲区
        await self._save_to_buffer(tracking_record)
        
        # 如果有实际结果，更新准确性指标
        if actual_result is not None:
            await self._update_accuracy_metrics(tracking_record)
        
        # 发布预测跟踪事件
        self.event_bus.publish(
            PredictionTrackedEvent(
                model_version=model_version,
                tracking_id=tracking_record.tracking_id,
                has_actual=actual_result is not None
            )
        )
        
        return tracking_record.tracking_id
    
    async def generate_performance_report(self, 
                                        model_version: str,
                                        time_range: TimeRange) -> PerformanceReport:
        """生成性能报告"""
        
        # 获取指定时间范围的跟踪记录
        records = await self._get_tracking_records(model_version, time_range)
        
        # 计算性能指标
        accuracy_metrics = await self._calculate_accuracy_metrics(records)
        drift_metrics = await self._calculate_drift_metrics(records)
        performance_trends = await self._analyze_performance_trends(records)
        
        # 生成报告
        report = PerformanceReport(
            model_version=model_version,
            time_range=time_range,
            total_predictions=len(records),
            accuracy_metrics=accuracy_metrics,
            drift_metrics=drift_metrics,
            performance_trends=performance_trends,
            recommendations=self._generate_recommendations(
                accuracy_metrics, drift_metrics, performance_trends
            ),
            generated_at=datetime.now()
        )
        
        return report
```

**3. QualityAssessmentService - 质量评估服务**
```python
class QualityAssessmentService(BaseService):
    """质量评估服务"""
    
    async def assess_model_quality(self, 
                                 model_version: str,
                                 assessment_config: QualityAssessmentConfig) -> QualityAssessmentResult:
        """评估模型质量"""
        
        # 获取模型版本信息
        model_info = await self.model_version_service.get_model_info(model_version)
        if not model_info:
            raise ValueError(f"模型版本不存在: {model_version}")
        
        # 收集评估数据
        training_metrics = model_info.get('training_metrics', {})
        validation_metrics = model_info.get('validation_metrics', {})
        
        # 获取预测跟踪数据
        tracking_data = await self.prediction_tracking_service.get_recent_tracking_data(
            model_version, days=30
        )
        
        # 计算质量维度评分
        accuracy_score = await self._calculate_accuracy_score(
            validation_metrics, tracking_data
        )
        
        stability_score = await self._calculate_stability_score(
            training_metrics, validation_metrics
        )
        
        robustness_score = await self._calculate_robustness_score(
            model_info, tracking_data
        )
        
        efficiency_score = await self._calculate_efficiency_score(
            model_info, tracking_data
        )
        
        # 计算综合质量分数
        overall_score = self._calculate_overall_quality_score(
            accuracy_score, stability_score, robustness_score, efficiency_score,
            assessment_config.weights
        )
        
        # 生成评估结果
        assessment_result = QualityAssessmentResult(
            model_version=model_version,
            assessment_time=datetime.now(),
            overall_score=overall_score,
            dimension_scores={
                'accuracy': accuracy_score,
                'stability': stability_score,
                'robustness': robustness_score,
                'efficiency': efficiency_score
            },
            detailed_metrics={
                'training_metrics': training_metrics,
                'validation_metrics': validation_metrics,
                'prediction_metrics': await self._calculate_prediction_metrics(tracking_data)
            },
            recommendations=self._generate_quality_recommendations(
                accuracy_score, stability_score, robustness_score, efficiency_score
            )
        )
        
        # 保存评估结果
        await self._save_assessment_result(assessment_result)
        
        # 发布质量评估事件
        self.event_bus.publish(
            ModelQualityAssessedEvent(
                model_version=model_version,
                overall_score=overall_score,
                assessment_result=assessment_result
            )
        )
        
        return assessment_result
```

### 2. 数据流架构

#### 训练数据流
```python
# 数据准备流程
async def _prepare_training_data(self, task_config: TrainingTaskConfig):
    """准备训练数据"""
    
    # 1. 获取原始数据
    raw_data = await self.data_service.get_historical_data(
        symbols=task_config.symbols,
        start_date=task_config.start_date,
        end_date=task_config.end_date,
        data_types=task_config.data_types
    )
    
    # 2. 数据预处理
    processed_data = await self._preprocess_data(raw_data, task_config.preprocessing_params)
    
    # 3. 特征工程
    features = await self._engineer_features(processed_data, task_config.feature_params)
    
    # 4. 数据分割
    train_data, eval_data, test_data = await self._split_data(
        features, task_config.split_ratios
    )
    
    # 5. 数据标准化
    normalized_train, normalized_eval, normalized_test = await self._normalize_data(
        train_data, eval_data, test_data, task_config.normalization_params
    )
    
    return (normalized_train, normalized_eval, normalized_test)
```

#### 预测跟踪数据流
```python
# 预测跟踪流程
async def track_prediction_flow(self, prediction_request: PredictionRequest):
    """预测跟踪流程"""
    
    # 1. 获取模型版本
    model_version = prediction_request.model_version
    
    # 2. 执行预测
    prediction_result = await self._execute_prediction(
        model_version, prediction_request.input_data
    )
    
    # 3. 记录预测
    tracking_id = await self.prediction_tracking_service.track_prediction(
        model_version=model_version,
        prediction_input=prediction_request.input_data,
        prediction_output=prediction_result.output,
        actual_result=None  # 实际结果稍后更新
    )
    
    # 4. 更新预测状态
    await self._update_prediction_status(tracking_id, 'pending_actual')
    
    return tracking_id
```

---

## 🧠 模型训练实现

### 1. 支持的模型类型

#### 时间序列预测模型
```python
class TimeSeriesModelFactory:
    """时间序列模型工厂"""
    
    @staticmethod
    def create_model(model_type: str, **params):
        """创建时间序列模型"""
        
        if model_type == "lstm":
            return LSTMModel(**params)
        elif model_type == "gru":
            return GRUModel(**params)
        elif model_type == "transformer":
            return TransformerModel(**params)
        elif model_type == "prophet":
            return ProphetModel(**params)
        elif model_type == "xgboost":
            return XGBoostModel(**params)
        elif model_type == "lightgbm":
            return LightGBMModel(**params)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

class LSTMModel(nn.Module):
    """LSTM模型实现"""
    
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, 
                 output_size: int, dropout: float = 0.2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        
        out, _ = self.lstm(x, (h0, c0))
        out = self.dropout(out[:, -1, :])
        out = self.fc(out)
        return out

class XGBoostModel:
    """XGBoost模型实现"""
    
    def __init__(self, **params):
        self.params = {
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            **params
        }
        self.model = None
    
    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """训练模型"""
        dtrain = xgb.DMatrix(X_train, label=y_train)
        
        eval_list = []
        if X_val is not None and y_val is not None:
            dval = xgb.DMatrix(X_val, label=y_val)
            eval_list = [(dtrain, 'train'), (dval, 'eval')]
        
        self.model = xgb.train(
            params=self.params,
            dtrain=dtrain,
            num_boost_round=1000,
            evals=eval_list,
            early_stopping_rounds=50,
            verbose_eval=100
        )
        
        return self
    
    def predict(self, X):
        """预测"""
        if self.model is None:
            raise ValueError("模型未训练")
        
        dtest = xgb.DMatrix(X)
        return self.model.predict(dtest)
```

### 2. 训练任务管理

#### 训练任务配置
```python
@dataclass
class TrainingTaskConfig:
    """训练任务配置"""
    
    task_id: str
    task_name: str
    description: str
    
    # 模型配置
    model_type: str
    model_params: Dict[str, Any]
    
    # 数据配置
    symbols: List[str]
    start_date: str
    end_date: str
    data_types: List[str]
    
    # 训练配置
    training_params: Dict[str, Any]
    split_ratios: Dict[str, float] = field(default_factory=lambda: {
        'train': 0.7, 'val': 0.2, 'test': 0.1
    })
    
    # 特征工程配置
    feature_params: Dict[str, Any] = field(default_factory=dict)
    preprocessing_params: Dict[str, Any] = field(default_factory=dict)
    
    # 评估配置
    evaluation_metrics: List[str] = field(default_factory=lambda: [
        'mse', 'mae', 'rmse', 'r2', 'directional_accuracy'
    ])
    
    # 高级配置
    hyperparameter_tuning: bool = False
    cross_validation: bool = False
    ensemble_method: str = None
    
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
```

#### 训练执行引擎
```python
class TrainingEngine:
    """训练执行引擎"""
    
    def __init__(self, config: TrainingTaskConfig):
        self.config = config
        self.model = None
        self.training_history = []
        self.evaluation_results = {}
    
    async def execute(self) -> TrainingResult:
        """执行训练"""
        
        try:
            # 1. 数据准备
            train_data, val_data, test_data = await self._prepare_data()
            
            # 2. 模型初始化
            self.model = self._initialize_model()
            
            # 3. 训练循环
            if self.config.cross_validation:
                result = await self._cross_validation_training(train_data)
            else:
                result = await self._standard_training(train_data, val_data)
            
            # 4. 模型评估
            if test_data is not None:
                self.evaluation_results = await self._evaluate_model(test_data)
            
            # 5. 生成训练结果
            training_result = TrainingResult(
                task_id=self.config.task_id,
                model_version=result.model_version,
                training_metrics=result.training_metrics,
                evaluation_metrics=self.evaluation_results,
                model_artifacts=result.model_artifacts,
                training_time=result.training_time,
                success=True
            )
            
            return training_result
            
        except Exception as e:
            logger.error(f"训练执行失败: {str(e)}", exc_info=True)
            return TrainingResult(
                task_id=self.config.task_id,
                success=False,
                error=str(e)
            )
    
    async def _standard_training(self, train_data, val_data) -> TrainingResult:
        """标准训练流程"""
        
        start_time = time.time()
        
        # 训练循环
        for epoch in range(self.config.training_params['epochs']):
            epoch_start = time.time()
            
            # 前向传播
            train_loss = self._train_epoch(train_data)
            
            # 验证
            val_loss = self._validate_epoch(val_data)
            
            # 记录历史
            self.training_history.append({
                'epoch': epoch,
                'train_loss': train_loss,
                'val_loss': val_loss,
                'epoch_time': time.time() - epoch_start
            })
            
            # 早停检查
            if self._should_early_stop():
                logger.info(f"早停触发，训练在第{epoch}轮停止")
                break
            
            # 进度报告
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Train Loss={train_loss:.4f}, Val Loss={val_loss:.4f}")
        
        training_time = time.time() - start_time
        
        # 保存模型版本
        model_version = await self._save_model_version()
        
        return TrainingResult(
            task_id=self.config.task_id,
            model_version=model_version,
            training_metrics=self._calculate_final_metrics(),
            training_time=training_time,
            model_artifacts=self._get_model_artifacts()
        )
```

### 3. 模型版本管理

#### 版本管理策略
```python
class ModelVersionService(BaseService):
    """模型版本管理服务"""
    
    async def _save_model_version(self, task_id: str, model, training_result, eval_metrics):
        """保存模型版本"""
        
        # 生成版本号
        version = await self._generate_model_version()
        
        # 保存模型文件
        model_path = await self._save_model_file(model, version)
        
        # 记录版本信息
        version_info = {
            "version": version,
            "task_id": task_id,
            "model_type": model.__class__.__name__,
            "metrics": eval_metrics,
            "training_time": training_result["training_time"],
            "params": training_result["params"],
            "file_path": model_path,
            "created_at": datetime.now(),
            "status": "active"
        }
        
        # 保存到数据库
        version_id = await self._db_service.insert(
            "model_versions", 
            version_info
        )
        
        # 发布模型版本创建事件
        self.event_bus.publish(
            ModelVersionCreatedEvent(
                version_id=version_id,
                version=version,
                model_type=version_info["model_type"]
            )
        )
        
        return version
    
    async def _generate_model_version(self) -> str:
        """生成模型版本号"""
        
        # 获取当前最新版本
        latest_version = await self._get_latest_version()
        
        if latest_version:
            # 解析版本号并递增
            version_parts = latest_version.split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1])
            patch = int(version_parts[2]) + 1
            
            # 如果patch超过99，重置并递增minor
            if patch > 99:
                patch = 0
                minor += 1
                
            # 如果minor超过99，重置并递增major
            if minor > 99:
                minor = 0
                major += 1
                
            return f"{major}.{minor:02d}.{patch:02d}"
        else:
            # 首次版本
            return "1.00.00"
```

---

## 📊 预测跟踪系统

### 1. 跟踪数据模型

#### 预测记录结构
```python
@dataclass
class PredictionRecord:
    """预测记录"""
    
    tracking_id: str
    model_version: str
    timestamp: datetime
    
    # 输入输出数据
    input_data: Any
    predicted_value: Any
    actual_value: Optional[Any] = None
    
    # 上下文信息
    symbol: Optional[str] = None
    prediction_horizon: Optional[int] = None
    confidence_score: Optional[float] = None
    
    # 质量指标
    prediction_error: Optional[float] = None
    absolute_error: Optional[float] = None
    percentage_error: Optional[float] = None
    
    # 元数据
    execution_time: Optional[float] = None
    data_quality_score: Optional[float] = None
    feature_drift_score: Optional[float] = None
    
    def update_actual_value(self, actual_value: Any):
        """更新实际值并计算误差指标"""
        self.actual_value = actual_value
        
        if self.predicted_value is not None and actual_value is not None:
            # 计算预测误差
            self.prediction_error = self.predicted_value - actual_value
            self.absolute_error = abs(self.prediction_error)
            
            # 计算百分比误差（避免除零）
            if actual_value != 0:
                self.percentage_error = abs(self.prediction_error / actual_value) * 100
            else:
                self.percentage_error = 0.0
```

#### 性能指标计算
```python
class PerformanceMetricsCalculator:
    """性能指标计算器"""
    
    @staticmethod
    def calculate_accuracy_metrics(records: List[PredictionRecord]) -> AccuracyMetrics:
        """计算准确性指标"""
        
        valid_records = [r for r in records if r.actual_value is not None]
        
        if not valid_records:
            return AccuracyMetrics()
        
        # 计算各种误差指标
        errors = [r.prediction_error for r in valid_records if r.prediction_error is not None]
        abs_errors = [r.absolute_error for r in valid_records if r.absolute_error is not None]
        pct_errors = [r.percentage_error for r in valid_records if r.percentage_error is not None]
        
        # 方向准确性（对于价格预测）
        directional_accuracy = PerformanceMetricsCalculator._calculate_directional_accuracy(
            valid_records
        )
        
        return AccuracyMetrics(
            mse=np.mean([e**2 for e in errors]) if errors else 0.0,
            rmse=np.sqrt(np.mean([e**2 for e in errors])) if errors else 0.0,
            mae=np.mean(abs_errors) if abs_errors else 0.0,
            mape=np.mean(pct_errors) if pct_errors else 0.0,
            directional_accuracy=directional_accuracy,
            total_predictions=len(valid_records),
            valid_predictions=len([r for r in valid_records if r.prediction_error is not None])
        )
    
    @staticmethod
    def _calculate_directional_accuracy(records: List[PredictionRecord]) -> float:
        """计算方向准确性"""
        
        directional_correct = 0
        total_directional = 0
        
        for i in range(1, len(records)):
            curr_record = records[i]
            prev_record = records[i-1]
            
            if (curr_record.actual_value is not None and 
                prev_record.actual_value is not None and
                curr_record.predicted_value is not None and
                prev_record.predicted_value is not None):
                
                # 计算实际方向变化
                actual_direction = np.sign(curr_record.actual_value - prev_record.actual_value)
                predicted_direction = np.sign(curr_record.predicted_value - prev_record.predicted_value)
                
                if actual_direction != 0:  # 忽略无变化的情况
                    if actual_direction == predicted_direction:
                        directional_correct += 1
                    total_directional += 1
        
        return directional_correct / total_directional if total_directional > 0 else 0.0
```

### 2. 模型漂移检测

#### 数据漂移检测
```python
class DataDriftDetector:
    """数据漂移检测器"""
    
    def __init__(self, reference_data: pd.DataFrame):
        self.reference_data = reference_data
        self.reference_stats = self._calculate_reference_stats()
    
    def detect_drift(self, current_data: pd.DataFrame, threshold: float = 0.05) -> DriftAnalysis:
        """检测数据漂移"""
        
        current_stats = self._calculate_current_stats(current_data)
        drift_scores = {}
        drift_alerts = []
        
        for column in self.reference_data.columns:
            if column in current_data.columns:
                # 计算统计漂移
                stat_drift = self._calculate_statistical_drift(
                    self.reference_data[column], current_data[column]
                )
                
                # 计算分布漂移
                distribution_drift = self._calculate_distribution_drift(
                    self.reference_data[column], current_data[column]
                )
                
                # 计算综合漂移分数
                combined_drift = (stat_drift + distribution_drift) / 2
                drift_scores[column] = combined_drift
                
                # 检查是否超过阈值
                if combined_drift > threshold:
                    drift_alerts.append(DriftAlert(
                        feature=column,
                        drift_score=combined_drift,
                        threshold=threshold,
                        severity='high' if combined_drift > threshold * 2 else 'medium'
                    ))
        
        return DriftAnalysis(
            drift_scores=drift_scores,
            alerts=drift_alerts,
            overall_drift_score=np.mean(list(drift_scores.values())),
            analysis_timestamp=datetime.now()
        )
    
    def _calculate_statistical_drift(self, reference: pd.Series, current: pd.Series) -> float:
        """计算统计漂移"""
        
        # 使用Kolmogorov-Smirnov检验
        ks_statistic, p_value = ks_2samp(reference.dropna(), current.dropna())
        
        # 转换为漂移分数 (0-1)
        drift_score = ks_statistic
        
        return drift_score
    
    def _calculate_distribution_drift(self, reference: pd.Series, current: pd.Series) -> float:
        """计算分布漂移"""
        
        # 使用Jensen-Shannon散度
        ref_dist = reference.dropna().values
        curr_dist = current.dropna().values
        
        # 创建直方图
        bins = np.linspace(min(min(ref_dist), min(curr_dist)), 
                          max(max(ref_dist), max(curr_dist)), 50)
        
        ref_hist, _ = np.histogram(ref_dist, bins=bins, density=True)
        curr_hist, _ = np.histogram(curr_dist, bins=bins, density=True)
        
        # 归一化
        ref_hist = ref_hist / np.sum(ref_hist)
        curr_hist = curr_hist / np.sum(curr_hist)
        
        # 计算JS散度
        js_divergence = distance.jensenshannon(ref_hist, curr_hist)
        
        return js_divergence
```

### 3. 性能监控

#### 实时性能监控
```python
class RealTimePerformanceMonitor:
    """实时性能监控器"""
    
    def __init__(self):
        self.metrics_buffer = defaultdict(list)
        self.alert_thresholds = {
            'accuracy_drop': 0.1,  # 准确性下降超过10%
            'prediction_delay': 5.0,  # 预测延迟超过5秒
            'error_rate': 0.05,  # 错误率超过5%
            'drift_score': 0.3  # 漂移分数超过0.3
        }
        self.monitoring_active = True
    
    async def start_monitoring(self, model_versions: List[str]):
        """启动监控"""
        
        self.monitoring_active = True
        
        for model_version in model_versions:
            # 为每个模型版本启动监控任务
            asyncio.create_task(self._monitor_model_performance(model_version))
    
    async def _monitor_model_performance(self, model_version: str):
        """监控单个模型性能"""
        
        while self.monitoring_active:
            try:
                # 获取最近的预测记录
                recent_records = await self._get_recent_predictions(model_version, minutes=30)
                
                if recent_records:
                    # 计算当前性能指标
                    current_metrics = await self._calculate_current_metrics(recent_records)
                    
                    # 检查告警条件
                    await self._check_alert_conditions(model_version, current_metrics)
                    
                    # 存储指标
                    self.metrics_buffer[f"{model_version}_metrics"].append({
                        'timestamp': datetime.now(),
                        'metrics': current_metrics
                    })
                
                # 等待下一次检查（5分钟间隔）
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"监控模型 {model_version} 时出错: {str(e)}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试
    
    async def _check_alert_conditions(self, model_version: str, current_metrics: Dict):
        """检查告警条件"""
        
        alerts = []
        
        # 检查准确性下降
        if 'accuracy' in current_metrics:
            baseline_accuracy = await self._get_baseline_accuracy(model_version)
            accuracy_drop = (baseline_accuracy - current_metrics['accuracy']) / baseline_accuracy
            
            if accuracy_drop > self.alert_thresholds['accuracy_drop']:
                alerts.append(PerformanceAlert(
                    model_version=model_version,
                    alert_type='accuracy_drop',
                    message=f"模型准确性下降 {accuracy_drop:.2%}",
                    severity='high',
                    timestamp=datetime.now()
                ))
        
        # 检查预测延迟
        if 'avg_prediction_time' in current_metrics:
            if current_metrics['avg_prediction_time'] > self.alert_thresholds['prediction_delay']:
                alerts.append(PerformanceAlert(
                    model_version=model_version,
                    alert_type='prediction_delay',
                    message=f"预测延迟过高: {current_metrics['avg_prediction_time']:.2f}秒",
                    severity='medium',
                    timestamp=datetime.now()
                ))
        
        # 发送告警
        for alert in alerts:
            await self._send_alert(alert)
```

---

## 🔍 质量评估系统

### 1. 多维度质量评估

#### 质量评估框架
```python
class QualityAssessmentFramework:
    """质量评估框架"""
    
    def __init__(self):
        self.evaluation_dimensions = {
            'accuracy': AccuracyEvaluator(),
            'stability': StabilityEvaluator(),
            'robustness': RobustnessEvaluator(),
            'efficiency': EfficiencyEvaluator(),
            'interpretability': InterpretabilityEvaluator(),
            'fairness': FairnessEvaluator()
        }
    
    async def comprehensive_assessment(self, 
                                     model_version: str,
                                     assessment_scope: AssessmentScope) -> ComprehensiveAssessment:
        """综合质量评估"""
        
        # 获取评估所需数据
        model_data = await self._collect_model_data(model_version, assessment_scope)
        prediction_data = await self._collect_prediction_data(model_version, assessment_scope)
        training_data = await self._collect_training_data(model_version, assessment_scope)
        
        # 各维度评估
        dimension_results = {}
        for dimension_name, evaluator in self.evaluation_dimensions.items():
            if dimension_name in assessment_scope.dimensions:
                try:
                    result = await evaluator.evaluate(
                        model_data, prediction_data, training_data
                    )
                    dimension_results[dimension_name] = result
                except Exception as e:
                    logger.error(f"评估维度 {dimension_name} 时出错: {str(e)}")
                    dimension_results[dimension_name] = DimensionResult(
                        score=0.0, error=str(e), status='failed'
                    )
        
        # 计算综合分数
        overall_score = self._calculate_overall_score(dimension_results, assessment_scope.weights)
        
        # 生成建议
        recommendations = await self._generate_recommendations(dimension_results)
        
        return ComprehensiveAssessment(
            model_version=model_version,
            overall_score=overall_score,
            dimension_results=dimension_results,
            recommendations=recommendations,
            assessment_timestamp=datetime.now(),
            assessment_scope=assessment_scope
        )
```

#### 准确性评估器
```python
class AccuracyEvaluator:
    """准确性评估器"""
    
    async def evaluate(self, 
                      model_data: ModelData,
                      prediction_data: PredictionData,
                      training_data: TrainingData) -> DimensionResult:
        """评估准确性"""
        
        records = prediction_data.valid_records
        
        if not records:
            return DimensionResult(score=0.0, status='insufficient_data')
        
        # 计算基础准确性指标
        accuracy_metrics = PerformanceMetricsCalculator.calculate_accuracy_metrics(records)
        
        # 计算时间序列特定的准确性指标
        temporal_metrics = await self._calculate_temporal_metrics(records)
        
        # 计算业务相关的准确性指标
        business_metrics = await self._calculate_business_metrics(records)
        
        # 综合评分
        score = self._calculate_accuracy_score(
            accuracy_metrics, temporal_metrics, business_metrics
        )
        
        return DimensionResult(
            score=score,
            status='completed',
            detailed_metrics={
                'accuracy_metrics': accuracy_metrics.__dict__,
                'temporal_metrics': temporal_metrics,
                'business_metrics': business_metrics
            },
            confidence_interval=self._calculate_confidence_interval(records)
        )
    
    async def _calculate_temporal_metrics(self, records: List[PredictionRecord]) -> Dict:
        """计算时间序列特定指标"""
        
        if len(records) < 2:
            return {}
        
        # 按时间排序
        sorted_records = sorted(records, key=lambda x: x.timestamp)
        
        # 计算趋势预测准确性
        trend_accuracy = self._calculate_trend_accuracy(sorted_records)
        
        # 计算多步预测准确性
        multi_step_accuracy = await self._calculate_multi_step_accuracy(sorted_records)
        
        # 计算季节性预测准确性
        seasonal_accuracy = await self._calculate_seasonal_accuracy(sorted_records)
        
        return {
            'trend_accuracy': trend_accuracy,
            'multi_step_accuracy': multi_step_accuracy,
            'seasonal_accuracy': seasonal_accuracy
        }
    
    def _calculate_trend_accuracy(self, records: List[PredictionRecord]) -> float:
        """计算趋势预测准确性"""
        
        correct_trends = 0
        total_trends = 0
        
        for i in range(1, len(records)):
            curr = records[i]
            prev = records[i-1]
            
            if (curr.actual_value is not None and prev.actual_value is not None and
                curr.predicted_value is not None and prev.predicted_value is not None):
                
                # 实际趋势
                actual_trend = curr.actual_value - prev.actual_value
                # 预测趋势
                predicted_trend = curr.predicted_value - prev.predicted_value
                
                if actual_trend != 0:  # 忽略无变化的情况
                    if np.sign(actual_trend) == np.sign(predicted_trend):
                        correct_trends += 1
                    total_trends += 1
        
        return correct_trends / total_trends if total_trends > 0 else 0.0
```

### 2. 模型稳定性评估

#### 稳定性评估器
```python
class StabilityEvaluator:
    """稳定性评估器"""
    
    async def evaluate(self,
                      model_data: ModelData,
                      prediction_data: PredictionData,
                      training_data: TrainingData) -> DimensionResult:
        """评估模型稳定性"""
        
        # 计算预测方差稳定性
        variance_stability = await self._calculate_variance_stability(prediction_data)
        
        # 计算性能稳定性
        performance_stability = await self._calculate_performance_stability(prediction_data)
        
        # 计算数据漂移稳定性
        drift_stability = await self._calculate_drift_stability(prediction_data)
        
        # 计算跨时间段稳定性
        temporal_stability = await self._calculate_temporal_stability(prediction_data)
        
        # 综合稳定性分数
        overall_stability = np.mean([
            variance_stability,
            performance_stability,
            drift_stability,
            temporal_stability
        ])
        
        return DimensionResult(
            score=overall_stability,
            status='completed',
            detailed_metrics={
                'variance_stability': variance_stability,
                'performance_stability': performance_stability,
                'drift_stability': drift_stability,
                'temporal_stability': temporal_stability
            }
        )
    
    async def _calculate_variance_stability(self, prediction_data: PredictionData) -> float:
        """计算预测方差稳定性"""
        
        records = prediction_data.valid_records
        
        if len(records) < 10:
            return 0.0
        
        # 按时间窗口分组计算方差
        window_size = max(1, len(records) // 10)  # 10个窗口
        variances = []
        
        for i in range(0, len(records), window_size):
            window_records = records[i:i + window_size]
            if len(window_records) > 1:
                predictions = [r.predicted_value for r in window_records if r.predicted_value is not None]
                if len(predictions) > 1:
                    variances.append(np.var(predictions))
        
        if not variances:
            return 0.0
        
        # 计算方差的变异系数
        mean_variance = np.mean(variances)
        std_variance = np.std(variances)
        
        if mean_variance == 0:
            return 1.0 if std_variance == 0 else 0.0
        
        coefficient_of_variation = std_variance / mean_variance
        
        # 转换为稳定性分数 (变异系数越小，稳定性越高)
        stability_score = max(0.0, 1.0 - coefficient_of_variation)
        
        return stability_score
```

### 3. 鲁棒性评估

#### 鲁棒性评估器
```python
class RobustnessEvaluator:
    """鲁棒性评估器"""
    
    async def evaluate(self,
                      model_data: ModelData,
                      prediction_data: PredictionData,
                      training_data: TrainingData) -> DimensionResult:
        """评估模型鲁棒性"""
        
        # 计算噪声鲁棒性
        noise_robustness = await self._calculate_noise_robustness(model_data, training_data)
        
        # 计算异常值鲁棒性
        outlier_robustness = await self._calculate_outlier_robustness(prediction_data)
        
        # 计算分布偏移鲁棒性
        distribution_robustness = await self._calculate_distribution_robustness(prediction_data)
        
        # 计算对抗鲁棒性
        adversarial_robustness = await self._calculate_adversarial_robustness(model_data, training_data)
        
        # 综合鲁棒性分数
        overall_robustness = np.mean([
            noise_robustness,
            outlier_robustness,
            distribution_robustness,
            adversarial_robustness
        ])
        
        return DimensionResult(
            score=overall_robustness,
            status='completed',
            detailed_metrics={
                'noise_robustness': noise_robustness,
                'outlier_robustness': outlier_robustness,
                'distribution_robustness': distribution_robustness,
                'adversarial_robustness': adversarial_robustness
            }
        )
    
    async def _calculate_noise_robustness(self, model_data: ModelData, training_data: TrainingData) -> float:
        """计算噪声鲁棒性"""
        
        # 在测试数据上添加不同程度的噪声
        noise_levels = [0.01, 0.05, 0.1, 0.2]
        robustness_scores = []
        
        baseline_performance = await self._get_baseline_performance(model_data.model_version)
        
        for noise_level in noise_levels:
            # 生成带噪声的数据
            noisy_data = self._add_gaussian_noise(training_data.test_data, noise_level)
            
            # 在噪声数据上评估模型
            noisy_performance = await self._evaluate_on_noisy_data(model_data.model, noisy_data)
            
            # 计算性能下降程度
            performance_drop = (baseline_performance - noisy_performance) / baseline_performance
            
            # 计算鲁棒性分数
            robustness_score = max(0.0, 1.0 - performance_drop)
            robustness_scores.append(robustness_score)
        
        # 取平均鲁棒性分数
        return np.mean(robustness_scores)
```

---

## 🔄 系统集成

### 1. 与现有服务集成

#### 服务容器集成
```python
class AIServiceBootstrap:
    """AI服务启动器"""
    
    def __init__(self, service_container: UnifiedServiceContainer):
        self.container = service_container
        self.ai_services = {}
    
    async def initialize_ai_services(self):
        """初始化AI服务"""
        
        try:
            # 注册核心AI服务
            await self._register_core_services()
            
            # 初始化服务依赖
            await self._initialize_service_dependencies()
            
            # 启动事件监听
            await self._setup_event_listeners()
            
            # 启动监控服务
            await self._start_monitoring_services()
            
            logger.info("AI服务初始化完成")
            
        except Exception as e:
            logger.error(f"AI服务初始化失败: {str(e)}")
            raise
    
    async def _register_core_services(self):
        """注册核心AI服务"""
        
        # 模型训练服务
        self.container.register('model_training_service', ModelTrainingService)
        
        # 预测跟踪服务
        self.container.register('prediction_tracking_service', PredictionTrackingService)
        
        # 质量评估服务
        self.container.register('quality_assessment_service', QualityAssessmentService)
        
        # 模型版本管理服务
        self.container.register('model_version_service', ModelVersionService)
        
        # 性能监控服务
        self.container.register('ai_performance_monitor', AIPerformanceMonitor)
        
        logger.info("核心AI服务注册完成")
    
    async def _initialize_service_dependencies(self):
        """初始化服务依赖"""
        
        # 获取依赖服务
        event_bus = self.container.get('event_bus')
        database_service = self.container.get('database_service')
        cache_service = self.container.get('cache_service')
        
        # 为AI服务设置依赖
        model_training_service = self.container.get('model_training_service')
        model_training_service.set_dependencies(event_bus, database_service, cache_service)
        
        prediction_tracking_service = self.container.get('prediction_tracking_service')
        prediction_tracking_service.set_dependencies(event_bus, database_service, cache_service)
        
        logger.info("AI服务依赖初始化完成")
    
    async def _setup_event_listeners(self):
        """设置事件监听器"""
        
        event_bus = self.container.get('event_bus')
        
        # 监听模型相关事件
        event_bus.subscribe('model_training_completed', self._on_model_training_completed)
        event_bus.subscribe('prediction_made', self._on_prediction_made)
        event_bus.subscribe('model_deployed', self._on_model_deployed)
        
        logger.info("AI事件监听器设置完成")
```

### 2. 数据库集成

#### 数据库表结构
```sql
-- 模型版本表
CREATE TABLE model_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    task_id TEXT NOT NULL,
    model_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    training_metrics TEXT,  -- JSON
    validation_metrics TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    description TEXT
);

-- 训练任务表
CREATE TABLE training_tasks (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    description TEXT,
    model_type TEXT NOT NULL,
    model_params TEXT,  -- JSON
    training_params TEXT,  -- JSON
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- 预测跟踪表
CREATE TABLE prediction_tracking (
    tracking_id TEXT PRIMARY KEY,
    model_version TEXT NOT NULL,
    symbol TEXT,
    input_data TEXT,  -- JSON
    predicted_value REAL,
    actual_value REAL,
    prediction_error REAL,
    confidence_score REAL,
    execution_time REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actual_updated_at TIMESTAMP
);

-- 质量评估表
CREATE TABLE quality_assessments (
    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_version TEXT NOT NULL,
    overall_score REAL,
    accuracy_score REAL,
    stability_score REAL,
    robustness_score REAL,
    efficiency_score REAL,
    detailed_metrics TEXT,  -- JSON
    recommendations TEXT,  -- JSON
    assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 性能监控表
CREATE TABLE performance_monitoring (
    monitor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_version TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_level TEXT
);
```

### 3. API接口设计

#### RESTful API
```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

app = FastAPI(title="AI Model Training API", version="1.0.0")

class TrainingTaskRequest(BaseModel):
    task_name: str
    description: str
    model_type: str
    model_params: Dict[str, Any]
    symbols: List[str]
    start_date: str
    end_date: str
    training_params: Dict[str, Any]

class PredictionRequest(BaseModel):
    model_version: str
    input_data: Dict[str, Any]
    symbol: Optional[str] = None

class QualityAssessmentRequest(BaseModel):
    model_version: str
    assessment_scope: Optional[Dict[str, Any]] = None

@app.post("/training-tasks")
async def create_training_task(request: TrainingTaskRequest, background_tasks: BackgroundTasks):
    """创建训练任务"""
    
    try:
        model_training_service = app.state.container.get('model_training_service')
        
        # 创建训练任务配置
        config = TrainingTaskConfig(
            task_id=str(uuid.uuid4()),
            task_name=request.task_name,
            description=request.description,
            model_type=request.model_type,
            model_params=request.model_params,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            training_params=request.training_params
        )
        
        # 创建任务
        task_id = await model_training_service.create_training_task(config)
        
        # 异步执行训练
        background_tasks.add_task(
            model_training_service.execute_training_task, task_id
        )
        
        return {
            "task_id": task_id,
            "status": "created",
            "message": "训练任务已创建，正在后台执行"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predictions")
async def make_prediction(request: PredictionRequest):
    """执行预测"""
    
    try:
        prediction_service = app.state.container.get('prediction_tracking_service')
        
        # 执行预测
        prediction_result = await prediction_service.execute_prediction(
            model_version=request.model_version,
            input_data=request.input_data
        )
        
        # 跟踪预测结果
        tracking_id = await prediction_service.track_prediction(
            model_version=request.model_version,
            prediction_input=request.input_data,
            prediction_output=prediction_result.output,
            symbol=request.symbol
        )
        
        return {
            "tracking_id": tracking_id,
            "prediction": prediction_result.output,
            "confidence": prediction_result.confidence,
            "execution_time": prediction_result.execution_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model_version}/quality-assessment")
async def get_quality_assessment(model_version: str):
    """获取模型质量评估"""
    
    try:
        quality_service = app.state.container.get('quality_assessment_service')
        
        assessment_result = await quality_service.assess_model_quality(
            model_version=model_version,
            assessment_config=QualityAssessmentConfig()
        )
        
        return assessment_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model_version}/performance-report")
async def get_performance_report(model_version: str, days: int = 30):
    """获取性能报告"""
    
    try:
        tracking_service = app.state.container.get('prediction_tracking_service')
        
        time_range = TimeRange(
            start_date=datetime.now() - timedelta(days=days),
            end_date=datetime.now()
        )
        
        report = await tracking_service.generate_performance_report(
            model_version=model_version,
            time_range=time_range
        )
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 📈 部署和运维

### 1. 部署架构

#### 容器化部署
```dockerfile
# Dockerfile for AI Training Service
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose配置
```yaml
version: '3.8'

services:
  ai-training-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/ai_training
      - REDIS_URL=redis://redis:6379/0
      - EVENT_BUS_URL=rabbitmq://rabbitmq:5672
    depends_on:
      - postgres
      - redis
      - rabbitmq
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
    restart: unless-stopped

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=ai_training
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      - RABBITMQ_DEFAULT_USER=user
      - RABBITMQ_DEFAULT_PASS=password
    ports:
      - "15672:15672"
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 2. 监控和告警

#### 监控指标
```python
class AIMonitoringMetrics:
    """AI系统监控指标"""
    
    def __init__(self):
        self.metrics = {
            # 模型训练指标
            'training_tasks_total': Counter('ai_training_tasks_total'),
            'training_tasks_failed': Counter('ai_training_tasks_failed'),
            'training_duration': Histogram('ai_training_duration_seconds'),
            'model_accuracy': Gauge('ai_model_accuracy'),
            
            # 预测指标
            'predictions_total': Counter('ai_predictions_total'),
            'prediction_latency': Histogram('ai_prediction_latency_seconds'),
            'prediction_errors': Counter('ai_prediction_errors_total'),
            
            # 质量评估指标
            'quality_assessments_total': Counter('ai_quality_assessments_total'),
            'model_quality_score': Gauge('ai_model_quality_score'),
            'drift_detections': Counter('ai_drift_detections_total'),
            
            # 系统资源指标
            'gpu_utilization': Gauge('ai_gpu_utilization_percent'),
            'memory_usage': Gauge('ai_memory_usage_bytes'),
            'cpu_usage': Gauge('ai_cpu_usage_percent')
        }
    
    def record_training_start(self, model_type: str):
        """记录训练开始"""
        self.metrics['training_tasks_total'].labels(model_type=model_type).inc()
    
    def record_training_completed(self, model_type: str, duration: float, success: bool):
        """记录训练完成"""
        if success:
            self.metrics['training_duration'].labels(model_type=model_type).observe(duration)
        else:
            self.metrics['training_tasks_failed'].labels(model_type=model_type).inc()
    
    def record_prediction(self, model_version: str, latency: float, error: bool = False):
        """记录预测"""
        self.metrics['predictions_total'].labels(model_version=model_version).inc()
        self.metrics['prediction_latency'].labels(model_version=model_version).observe(latency)
        
        if error:
            self.metrics['prediction_errors'].labels(model_version=model_version).inc()
```

#### 告警规则
```yaml
# prometheus-alerts.yml
groups:
  - name: ai_training_alerts
    rules:
      - alert: AITrainingTaskFailureRate
        expr: rate(ai_training_tasks_failed[5m]) / rate(ai_training_tasks_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "AI训练任务失败率过高"
          description: "过去5分钟内AI训练任务失败率超过10%"

      - alert: AIPredictionLatencyHigh
        expr: histogram_quantile(0.95, rate(ai_prediction_latency_seconds_bucket[5m])) > 5
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "AI预测延迟过高"
          description: "95%的预测请求延迟超过5秒"

      - alert: AIModelQualityDegraded
        expr: ai_model_quality_score < 0.7
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "AI模型质量下降"
          description: "模型质量评分低于0.7"

      - alert: AIDataDriftDetected
        expr: increase(ai_drift_detections_total[1h]) > 5
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "检测到数据漂移"
          description: "过去1小时内检测到超过5次数据漂移"
```

### 3. 运维脚本

#### 自动化运维脚本
```python
#!/usr/bin/env python3
"""
AI模型训练系统运维脚本
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from typing import List, Dict

class AIOperationsManager:
    """AI运维管理器"""
    
    def __init__(self):
        self.container = None
    
    async def initialize(self):
        """初始化运维管理器"""
        from main import app
        self.container = app.state.container
    
    async def cleanup_old_models(self, days: int = 30):
        """清理旧模型文件"""
        
        model_version_service = self.container.get('model_version_service')
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 获取需要清理的模型版本
        old_versions = await model_version_service.get_old_versions(cutoff_date)
        
        cleaned_count = 0
        for version in old_versions:
            try:
                await model_version_service.archive_version(version)
                cleaned_count += 1
                print(f"已归档模型版本: {version}")
            except Exception as e:
                print(f"归档模型版本失败 {version}: {str(e)}")
        
        print(f"清理完成，共清理 {cleaned_count} 个模型版本")
    
    async def health_check(self) -> Dict:
        """系统健康检查"""
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'services': {},
            'metrics': {}
        }
        
        try:
            # 检查核心服务
            model_training_service = self.container.get('model_training_service')
            prediction_service = self.container.get('prediction_tracking_service')
            
            # 检查服务状态
            health_status['services']['model_training'] = await self._check_service_health(
                model_training_service
            )
            health_status['services']['prediction_tracking'] = await self._check_service_health(
                prediction_service
            )
            
            # 检查关键指标
            health_status['metrics'] = await self._collect_key_metrics()
            
            # 总体状态
            if any(service['status'] != 'healthy' for service in health_status['services'].values()):
                health_status['overall_status'] = 'degraded'
            
        except Exception as e:
            health_status['overall_status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status
    
    async def backup_system(self, backup_path: str):
        """系统备份"""
        
        import shutil
        import os
        
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        full_backup_path = f"{backup_path}/ai_system_backup_{backup_timestamp}"
        
        os.makedirs(full_backup_path, exist_ok=True)
        
        try:
            # 备份模型文件
            model_path = "./models"
            if os.path.exists(model_path):
                shutil.copytree(model_path, f"{full_backup_path}/models")
            
            # 备份配置文件
            config_files = ["./config/", "./logs/"]
            for config_file in config_files:
                if os.path.exists(config_file):
                    if os.path.isfile(config_file):
                        shutil.copy2(config_file, full_backup_path)
                    else:
                        shutil.copytree(config_file, f"{full_backup_path}/{os.path.basename(config_file)}")
            
            # 导出数据库
            database_service = self.container.get('database_service')
            await database_service.export_backup(f"{full_backup_path}/database.sql")
            
            print(f"系统备份完成: {full_backup_path}")
            
        except Exception as e:
            print(f"系统备份失败: {str(e)}")
            raise

async def main():
    parser = argparse.ArgumentParser(description="AI训练系统运维工具")
    parser.add_argument('action', choices=['cleanup', 'health', 'backup'],
                       help="执行的操作")
    parser.add_argument('--days', type=int, default=30,
                       help="清理操作的日期阈值")
    parser.add_argument('--path', type=str, default='./backups',
                       help="备份路径")
    
    args = parser.parse_args()
    
    ops_manager = AIOperationsManager()
    await ops_manager.initialize()
    
    if args.action == 'cleanup':
        await ops_manager.cleanup_old_models(args.days)
    elif args.action == 'health':
        health = await ops_manager.health_check()
        print(f"系统健康状态: {health}")
    elif args.action == 'backup':
        await ops_manager.backup_system(args.path)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🎯 总结

### 系统优势

1. **完整性**：涵盖模型训练、预测跟踪、质量评估的完整生命周期
2. **可扩展性**：模块化设计，支持新模型类型和评估维度
3. **可靠性**：基于现有服务容器架构，确保系统稳定性
4. **性能**：异步处理和并发优化，确保高性能
5. **监控**：全方位的监控和告警机制

### 核心价值

1. **提升模型质量**：通过全面的质量评估和持续监控
2. **降低维护成本**：自动化训练和部署流程
3. **增强用户体验**：稳定可靠的预测服务
4. **支持业务决策**：基于数据的模型选择和优化

### 实施建议

1. **分阶段部署**：从核心功能开始，逐步扩展
2. **渐进式迁移**：与现有系统并行运行，逐步切换
3. **持续优化**：基于监控数据不断优化系统
4. **团队培训**：确保团队掌握新系统的使用方法

---

**文档版本**：v1.0  
**生成时间**：2024-12-19  
**维护者**：AI训练系统开发团队

---

## 🔗 相关文档

- [AI模型训练开发计划](./ai_model_training_development_plan.md) - 详细开发计划
- [形态分析中AI预测功能深度分析报告](./形态分析中AI预测功能深度分析报告.md) - 应用场景分析
- [智能数据质量评估系统使用指南](./智能数据质量评估系统使用指南.md) - 质量评估指南