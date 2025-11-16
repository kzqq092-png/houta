# 进度间隔显示为空 - 完整修复链路

## 根本原因确认
QFormLayout在水平并排显示两个QGroupBox时，字段可能因为布局政策问题而不显示

## 执行的修复（完整链路）

1. **宽度约束** (第1192-1193行)
   - setMinimumWidth(100)
   - setMaximumWidth(200)

2. **FormLayout配置** (第1173-1174行)
   - setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
   - setHorizontalSpacing(10)

## 完整调用链
_create_integrated_config_tab() → error_layout(QFormLayout) → addRow("进度间隔:", progress_interval_spin)
→ execution_layout(QHBoxLayout) → error_config → 最终显示

修复后，进度间隔应能正常显示在"错误处理"配置区域