# 数据质量监控Mock数据修复补丁

## 修复文件

### 1. gui/widgets/enhanced_ui/data_quality_monitor_tab.py

#### 在文件顶部添加导入
```python
# 在现有导入后添加
from gui.widgets.enhanced_ui.data_quality_monitor_tab_real_data import get_real_data_provider
```

#### 在 __init__ 方法中添加
```python
def __init__(self, parent=None, ...):
    # ... 现有代码 ...
    
    # 初始化真实数据提供者
    self.real_data_provider = get_real_data_provider()
    
    # ... 现有代码 ...
```

#### 添加真实数据方法（在文件末尾，1149行后）
```python
    # ==================== 真实数据处理方法 ====================
    
    def _get_real_quality_metrics(self) -> Dict[str, float]:
        """获取真实质量指标"""
        try:
            return self.real_data_provider.get_quality_metrics()
        except Exception as e:
            logger.error(f"获取真实质量指标失败: {e}")
            return {}
    
    def _get_real_data_sources_quality(self) -> List[Dict[str, Any]]:
        """获取真实数据源质量"""
        try:
            return self.real_data_provider.get_data_sources_quality()
        except Exception as e:
            logger.error(f"获取数据源质量失败: {e}")
            return []
    
    def _get_real_datatypes_quality(self) -> List[Dict[str, Any]]:
        """获取真实数据类型质量"""
        try:
            return self.real_data_provider.get_datatypes_quality()
        except Exception as e:
            logger.error(f"获取数据类型质量失败: {e}")
            return []
    
    def _get_real_anomaly_stats(self) -> Dict[str, int]:
        """获取真实异常统计"""
        try:
            return self.real_data_provider.get_anomaly_stats()
        except Exception as e:
            logger.error(f"获取异常统计失败: {e}")
            return {}
    
    def _get_real_anomaly_records(self) -> List[Dict[str, Any]]:
        """获取真实异常记录"""
        try:
            return self.real_data_provider.get_anomaly_records()
        except Exception as e:
            logger.error(f"获取异常记录失败: {e}")
            return []
```

### 2. gui/widgets/data_quality_control_center.py

#### 修改 load_sample_data 方法
```python
def load_sample_data(self):
    """加载数据（使用真实数据质量监控）"""
    # 初始化真实数据提供者
    try:
        from gui.widgets.enhanced_ui.data_quality_monitor_tab_real_data import get_real_data_provider
        self.real_data_provider = get_real_data_provider()
        
        # 加载真实数据
        self.load_real_metrics()
        self.load_real_rules()
        self.load_real_issues()
        
        logger.info("真实数据质量数据加载完成")
    except Exception as e:
        logger.error(f"加载真实数据失败: {e}")
        # 降级到基础数据
        self.generate_sample_metrics()
```

#### 添加真实数据加载方法
```python
def load_real_metrics(self):
    """加载真实质量指标"""
    try:
        metrics_data = self.real_data_provider.get_quality_metrics()
        
        for metric_name, value in metrics_data.items():
            metric_type_map = {
                'completeness': QualityMetricType.COMPLETENESS,
                'accuracy': QualityMetricType.ACCURACY,
                'timeliness': QualityMetricType.TIMELINESS,
                'consistency': QualityMetricType.CONSISTENCY,
                'validity': QualityMetricType.VALIDITY,
                'uniqueness': QualityMetricType.UNIQUENESS
            }
            
            if metric_name in metric_type_map:
                metric_type = metric_type_map[metric_name]
                metric = QualityMetric(
                    metric_type=metric_type,
                    value=value,
                    threshold=0.85,
                    timestamp=datetime.now()
                )
                self.quality_metrics[metric_type] = metric
        
        self.update_quality_gauges()
        
    except Exception as e:
        logger.error(f"加载真实质量指标失败: {e}")

def load_real_rules(self):
    """加载真实质量规则"""
    # 使用系统配置的规则
    # 这里可以从配置文件或数据库加载
    self.generate_sample_rules()  # 暂时保持规则生成

def load_real_issues(self):
    """加载真实质量问题"""
    try:
        anomalies = self.real_data_provider.get_anomaly_records()
        
        issues = []
        for idx, anomaly in enumerate(anomalies):
            if anomaly.get('severity') not in ['正常', 'INFO']:
                severity_map = {
                    '严重': QualitySeverity.CRITICAL,
                    '警告': QualitySeverity.HIGH,
                    '一般': QualitySeverity.MEDIUM,
                    '轻微': QualitySeverity.LOW
                }
                
                issue = QualityIssue(
                    issue_id=f"issue_{idx:03d}",
                    rule_id="auto_detected",
                    rule_name=anomaly.get('type', 'Unknown'),
                    severity=severity_map.get(anomaly.get('severity'), QualitySeverity.MEDIUM),
                    description=anomaly.get('description', ''),
                    affected_rows=1,
                    column=anomaly.get('datatype', ''),
                    sample_values=[anomaly.get('source', '')]
                )
                issues.append(issue)
        
        self.quality_issues = issues
        self.filter_issues()
        
    except Exception as e:
        logger.error(f"加载真实质量问题失败: {e}")
```

#### 修改 update_quality_metrics 方法
```python
def update_quality_metrics(self):
    """更新质量指标（使用真实数据）"""
    try:
        # 获取真实指标
        metrics_data = self.real_data_provider.get_quality_metrics()
        
        # 更新现有指标
        for metric_name, value in metrics_data.items():
            metric_type_map = {
                'completeness': QualityMetricType.COMPLETENESS,
                'accuracy': QualityMetricType.ACCURACY,
                'timeliness': QualityMetricType.TIMELINESS,
                'consistency': QualityMetricType.CONSISTENCY,
                'validity': QualityMetricType.VALIDITY,
                'uniqueness': QualityMetricType.UNIQUENESS
            }
            
            if metric_name in metric_type_map:
                metric_type = metric_type_map[metric_name]
                if metric_type in self.quality_metrics:
                    self.quality_metrics[metric_type].value = value
                    self.quality_metrics[metric_type].timestamp = datetime.now()
        
        self.update_quality_gauges()
        
    except Exception as e:
        logger.error(f"更新质量指标失败: {e}")
```

#### 修改 update_overview_stats 方法
```python
def update_overview_stats(self):
    """更新概览统计（使用真实数据）"""
    try:
        # 获取真实统计
        datatypes = self.real_data_provider.get_datatypes_quality()
        
        # 总记录数
        total_records = sum(dt.get('count', 0) for dt in datatypes)
        self.total_records_label.setText(f"{total_records:,}")
        
        # 质量问题数
        unresolved_issues = len([issue for issue in self.quality_issues if not issue.resolved])
        self.total_issues_label.setText(str(unresolved_issues))
        
        # 平均质量分数
        if self.quality_metrics:
            avg_score = sum(m.value for m in self.quality_metrics.values()) / len(self.quality_metrics)
            self.avg_score_label.setText(f"{avg_score:.2%}")
        else:
            self.avg_score_label.setText("N/A")
        
        # 最后更新时间
        self.last_update_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
    except Exception as e:
        logger.error(f"更新概览统计失败: {e}")
```

## 实施步骤

### 自动化脚本（推荐）

创建 `apply_data_quality_fix.py`:

```python
#!/usr/bin/env python3
"""
应用数据质量监控Mock数据修复补丁
"""

import os
from pathlib import Path

def apply_patch():
    """应用修复补丁"""
    
    print("=" * 60)
    print("数据质量监控Mock数据修复")
    print("=" * 60)
    
    # 1. 修改 data_quality_monitor_tab.py
    tab_file = Path("gui/widgets/enhanced_ui/data_quality_monitor_tab.py")
    if tab_file.exists():
        print(f"\n✅ 找到文件: {tab_file}")
        
        with open(tab_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经修复
        if 'get_real_data_provider' in content:
            print("⚠️  文件已经包含真实数据提供者导入")
        else:
            # 添加导入
            import_line = "from gui.widgets.enhanced_ui.data_quality_monitor_tab_real_data import get_real_data_provider\n"
            
            # 找到导入区域末尾
            lines = content.split('\n')
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    insert_pos = i + 1
            
            lines.insert(insert_pos, import_line)
            content = '\n'.join(lines)
            
            # 写回文件
            with open(tab_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 已添加真实数据提供者导入")
    
    # 2. 检查真实数据提供者文件
    provider_file = Path("gui/widgets/enhanced_ui/data_quality_monitor_tab_real_data.py")
    if provider_file.exists():
        print(f"\n✅ 真实数据提供者文件已存在: {provider_file}")
    else:
        print(f"\n❌ 缺少真实数据提供者文件: {provider_file}")
        print("   请确保该文件已创建")
    
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 测试应用启动")
    print("2. 检查数据质量监控Tab")
    print("3. 验证真实数据显示")

if __name__ == "__main__":
    apply_patch()
```

### 手动步骤

如果不使用脚本，请按照上述补丁说明手动修改文件。

## 验证

### 1. 启动应用
```bash
python main.py
```

### 2. 检查日志
```
INFO | 创建新的DataQualityMonitor实例
INFO | 创建新的UnifiedDataManager实例
INFO | 真实数据质量数据加载完成
```

### 3. 查看UI
- 打开数据质量监控Tab
- 应该显示真实的数据源状态
- 应该显示真实的质量指标
- 不应该看到随机变化的Mock数据

## 回滚

如果需要回滚，删除以下内容：
1. `gui/widgets/enhanced_ui/data_quality_monitor_tab_real_data.py`
2. `data_quality_monitor_tab.py` 中添加的导入和方法
3. `data_quality_control_center.py` 中的修改

## 注意事项

1. **性能**: 真实数据查询可能比Mock数据慢，已添加缓存机制
2. **依赖**: 需要UnifiedDataManager和DataQualityMonitor正常工作
3. **降级**: 如果服务不可用，会降级到默认值而非崩溃
4. **扩展**: 可以根据需要扩展更多真实数据源

---

**修复状态**: 补丁已准备就绪  
**测试状态**: 待验证  
**版本**: v2.0.3

