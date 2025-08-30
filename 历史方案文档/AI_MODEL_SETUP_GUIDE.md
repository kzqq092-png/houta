# FactorWeave-Quant  AI模型设置指南

## 问题描述

当启动FactorWeave-Quant 时，您可能会看到以下警告信息：

```
⚠️ 加载pattern模型不存在，路径: models\trained\pattern_model.h5
⚠️ 加载trend模型不存在，路径: models\trained\trend_model.h5  
⚠️ 加载sentiment模型不存在，路径: models\trained\sentiment_model.h5
⚠️ 加载price模型不存在，路径: models\trained\price_model.h5
```

这是因为AI预测功能需要预训练的机器学习模型，但初始安装时这些模型文件不存在。

## 快速解决方案（推荐）

### 方案一：使用简化模型（无需TensorFlow）

```bash
# 运行简化模型生成器
python scripts/generate_simple_models.py
```

这将在几秒钟内生成所有必需的模型文件。

### 方案二：生成完整AI模型（需要TensorFlow）

1. **安装TensorFlow**：
   ```bash
   pip install tensorflow
   ```

2. **生成AI模型**：
   ```bash
   # 快速模式（推荐，约2-5分钟）
   python scripts/generate_ai_models.py --quick
   
   # 标准模式（完整训练，约10-20分钟）
   python scripts/generate_ai_models.py
   
   # 只生成特定模型
   python scripts/generate_ai_models.py --model pattern --quick
   ```

## 模型说明

生成的4个AI预测模型：

| 模型文件 | 功能 | 输入特征 | 输出预测 |
|---------|------|----------|----------|
| `pattern_model.h5` | 形态识别 | 15个技术指标 | 价格形态类型 |
| `trend_model.h5` | 趋势预测 | 20个价格/指标特征 | 未来趋势方向 |
| `sentiment_model.h5` | 情绪分析 | 12个市场情绪指标 | 市场情绪状态 |
| `price_model.h5` | 价格预测 | 25个技术分析特征 | 价格变化方向 |

## 生成后的验证

1. **检查模型文件**：
   ```bash
   ls models/trained/
   ```
   应该看到：
   - `pattern_model.h5` + `pattern_model_info.json`
   - `trend_model.h5` + `trend_model_info.json`
   - `sentiment_model.h5` + `sentiment_model_info.json`
   - `price_model.h5` + `price_model_info.json`

2. **重新启动应用程序**：
   ```bash
   python main.py
   ```

3. **查看日志确认**：
   启动时应该看到：
   ```
   ✅ 加载pattern预训练模型
   ✅ 加载trend预训练模型
   ✅ 加载sentiment预训练模型
   ✅ 加载price预训练模型
   ```

## 高级选项

### 自定义模型训练

如果您有自己的股票数据和训练需求，可以修改 `scripts/generate_ai_models.py` 中的数据生成逻辑：

1. 替换 `generate_sample_data()` 方法中的随机数据生成
2. 使用真实的股票历史数据
3. 调整模型架构和参数

### 模型更新

定期重新训练模型以保持预测准确性：

```bash
# 每月重新训练（使用最新数据）
python scripts/generate_ai_models.py --quick
```

## 故障排除

### 1. TensorFlow安装问题

如果TensorFlow安装失败：

```bash
# 尝试指定版本
pip install tensorflow==2.13.0

# 或者使用CPU版本
pip install tensorflow-cpu
```

### 2. 内存不足

如果训练时内存不足：

```bash
# 使用快速模式
python scripts/generate_ai_models.py --quick
```

### 3. 权限问题

如果无法写入模型文件：

```bash
# 确保models/trained目录有写权限
mkdir -p models/trained
chmod 755 models/trained
```

### 4. 模型加载失败

如果生成的模型无法加载：

1. 删除现有模型文件
   ```bash
   rm models/trained/*.h5
   ```

2. 重新生成
   ```bash
   python scripts/generate_simple_models.py
   ```

## 性能对比

| 模型类型 | 生成时间 | 预测准确性 | 资源占用 | 推荐场景 |
|---------|----------|------------|----------|----------|
| 简化模型 | <1分钟 | 中等 | 低 | 快速体验、兼容性 |
| 快速AI模型 | 2-5分钟 | 良好 | 中等 | 日常使用 |
| 完整AI模型 | 10-20分钟 | 最佳 | 高 | 专业分析 |

## 备注

- 简化模型提供基本功能，但预测准确性有限
- 完整AI模型需要TensorFlow，但提供更好的预测性能
- 所有模型都支持实时预测和批量分析
- 模型文件会自动保存训练信息和元数据

## 联系支持

如果您在模型生成过程中遇到问题，请：

1. 检查Python环境和依赖包
2. 查看终端输出的错误信息
3. 尝试使用简化模型作为临时解决方案
4. 确保有足够的磁盘空间（至少500MB）

生成成功后，FactorWeave-Quant 的AI预测功能将完全可用！ 